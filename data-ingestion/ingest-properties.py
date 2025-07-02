#!/usr/bin/env python3

import os
import json
import argparse
from elasticsearch import Elasticsearch, helpers
import requests
import time

# Parse command line arguments
parser = argparse.ArgumentParser(description='Property data ingestion script with ELSER semantic processing')
parser.add_argument('--searchtemplate', action='store_true', 
                   help='Only run the search template creation part')
parser.add_argument('--full-ingestion', action='store_true', 
                   help='Only run the complete data ingestion pipeline (create indices, download data, process with ELSER)')
parser.add_argument('--recreate-index', action='store_true', 
                   help='Only delete and recreate the properties index (no data processing)')
parser.add_argument('--use-small-5k-dataset', action='store_true',
                   help='Use the smaller 5000-line dataset instead of the full dataset')
parser.add_argument('--use-500-dataset', action='store_true',
                   help='Use the tiny 500-line dataset instead of the full dataset')
parser.add_argument('--instruqt', action='store_true',
                   help='Use Instruqt workshop settings for Elasticsearch connection')
args = parser.parse_args()

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Elasticsearch Configurations
INSTRUQT_WORKSHOP_SETTINGS = args.instruqt

if INSTRUQT_WORKSHOP_SETTINGS:
    # Use Instruqt workshop settings
    ES_URL = os.getenv('INSTRUQT_ES_URL')
    ES_USERNAME = os.getenv('INSTRUQT_ES_USERNAME')
    ES_PASSWORD = os.getenv('INSTRUQT_ES_PASSWORD')
    
    # For Instruqt, read API key from JSON file using jq pattern
    import subprocess
    try:
        REGIONS = os.getenv('REGIONS')
        if not REGIONS:
            raise ValueError("REGIONS environment variable must be set for Instruqt workshop settings")
        
        # Execute the jq command to extract API key
        result = subprocess.run([
            'jq', '-r', '--arg', 'region', REGIONS, 
            '.[$region].credentials.api_key', '/tmp/project_results.json'
        ], capture_output=True, text=True, check=True)
        
        ES_API_KEY = result.stdout.strip()
        if not ES_API_KEY:
            raise ValueError("API key not found in JSON file")
        
        USE_PASSWORD_AUTH = False  # Use API key auth for Instruqt
        print("🎓 Using Instruqt workshop settings for Elasticsearch connection")
        print(f"🔑 API key extracted from JSON file for region: {REGIONS}")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to extract API key from JSON file: {e}")
    except FileNotFoundError:
        raise ValueError("jq command not found. Please install jq for Instruqt workshop settings")
else:
    # Use regular settings
    ES_URL = os.getenv('ES_URL')  # expects full URL including scheme (http/https) and port (:443) 
    ES_API_KEY = os.getenv('ES_API_KEY')
    ES_USERNAME = os.getenv('ES_USERNAME')
    ES_PASSWORD = os.getenv('ES_PASSWORD')
    USE_PASSWORD_AUTH = os.getenv('USE_PASSWORD_AUTH', 'false').lower() == 'true'

INDEX_NAME = os.getenv('ES_INDEX', "properties")
TEMPLATE_ID = os.getenv('PROPERTIES_SEARCH_TEMPLATE', "properties-search-template")
ELSER_INFERENCE_ID = os.getenv('ELSER_INFERENCE_ID', ".elser-2-elasticsearch")

# Constants
PROPERTIES_FULL_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties.json"
PROPERTIES_5000_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties-filtered-5000-lines.json"
PROPERTIES_500_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties-filtered-500-lines.json"
SEARCH_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "search-template.mustache")
PROPERTIES_INDEX_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "properties-index-mapping.json")

def get_expected_document_count(use_small_dataset=False, use_tiny_dataset=False):
    """Return the expected number of documents based on the dataset being used"""
    if use_tiny_dataset:
        return 500  # Tiny dataset has 500 documents
    elif use_small_dataset:
        return 5000  # Smaller dataset has 5000 documents
    else:
        return 48966  # Full dataset has 48966 documents

# Load search template from external file
def load_search_template():
    """Load search template content from external file"""
    try:
        with open(SEARCH_TEMPLATE_FILE, 'r') as f:
            template_source = f.read()
        return {
            "script": {
                "lang": "mustache",
                "source": template_source
            }
        }
    except FileNotFoundError:
        print(f"❌ Search template file not found: {SEARCH_TEMPLATE_FILE}")
        raise

# Load index mapping from external file
def load_index_mapping(mapping_file):
    """Load index mapping from external JSON file"""
    try:
        with open(mapping_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Index mapping file not found: {mapping_file}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in mapping file {mapping_file}: {e}")
        raise

# Load the search template content
search_template_content = load_search_template()

print("🔧 Initializing Elasticsearch connection...")

# Connect to Elasticsearch
if not ES_URL:
    if INSTRUQT_WORKSHOP_SETTINGS:
        raise ValueError("INSTRUQT_ES_URL environment variable must be set when INSTRUQT_WORKSHOP_SETTINGS=true")
    else:
        raise ValueError("ES_URL environment variable must be set")

if USE_PASSWORD_AUTH:
    # Use username/password authentication
    if not ES_USERNAME:
        if INSTRUQT_WORKSHOP_SETTINGS:
            raise ValueError("INSTRUQT_ES_USERNAME environment variable must be set when INSTRUQT_WORKSHOP_SETTINGS=true")
        else:
            raise ValueError("ES_USERNAME environment variable must be set when USE_PASSWORD_AUTH=true")
    
    # For Instruqt workshop settings, password can be empty
    if not INSTRUQT_WORKSHOP_SETTINGS and not ES_PASSWORD:
        raise ValueError("ES_PASSWORD environment variable must be set when USE_PASSWORD_AUTH=true")
    
    print("🔐 Using username/password authentication...")
    es = Elasticsearch(
        hosts=[ES_URL], 
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        request_timeout=600,
        retry_on_timeout=True,
        max_retries=0
    )
else:
    # Use API key authentication
    if not ES_API_KEY:
        if INSTRUQT_WORKSHOP_SETTINGS:
            raise ValueError("Failed to extract API key from JSON file for Instruqt workshop settings")
        else:
            raise ValueError("ES_API_KEY environment variable must be set when USE_PASSWORD_AUTH=false")
    
    print("🔑 Using API key authentication...")
    es = Elasticsearch(
        hosts=[ES_URL], 
        api_key=ES_API_KEY, 
        request_timeout=600,
        retry_on_timeout=True,
        max_retries=0
    )

es.info()
print("✅ Connected to Elasticsearch successfully")



def create_properties_index():
    print(f"🏗️ Creating properties index '{INDEX_NAME}' with ELSER semantic fields...")
    mapping = load_index_mapping(PROPERTIES_INDEX_MAPPING_FILE)

    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"🗑️ Index '{INDEX_NAME}' deleted.")

    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"✅ Index '{INDEX_NAME}' created.")

def create_search_template(
    template_id=TEMPLATE_ID, template_content=search_template_content
):
    """Creates a new search template"""
    print(f"📝 Creating search template '{template_id}'...")
    try:
        es.put_script(id=template_id, body=template_content)
        print(f"✅ Created search template: {template_id}")
    except Exception as e:
        print(f"❌ Error creating template '{template_id}': {e}")

def download_and_parallel_bulk_load(properties_url=None):
    if properties_url is None:
        properties_url = PROPERTIES_FULL_URL
    
    print(f"📥 Downloading property data from {properties_url}...")
    response = requests.get(properties_url, stream=True)
    response.raise_for_status()
    print("✅ Data download started successfully")

    def generate_actions():
        doc_count = 0
        for line in response.iter_lines():
            if line:
                doc = json.loads(line.decode("utf-8"))
                doc_count += 1
                if doc_count % 1000 == 0:
                    print(f"📊 Processed {doc_count} documents...")
                yield {
                    "_index": INDEX_NAME,
                    "_source": doc
                }
        print(f"📊 Total documents to index: {doc_count}")

    print("🚀 Starting parallel bulk indexing...")
    success_count = 0
    error_count = 0
    
    # Use smaller chunk size for Instruqt to avoid 413 errors
    chunk_size = 50 if args.instruqt else 500
    
    for ok, result in helpers.parallel_bulk(
        es,
        actions=generate_actions(),
        thread_count=4,
        chunk_size=chunk_size,
        request_timeout=60
    ):
        if ok:
            success_count += 1
            if success_count % 1000 == 0:
                print(f"✅ Successfully indexed {success_count} documents...")
        else:
            error_count += 1
            if error_count % 100 == 0:
                print(f"❌ Encountered {error_count} errors...")

    print(f"✅ Successfully indexed {success_count} documents into '{INDEX_NAME}' using parallel_bulk")
    if error_count > 0:
        print(f"⚠️ Encountered {error_count} errors during indexing")
    
    # Add delay for Instruqt to allow documents to be available for counting
    if args.instruqt:
        print("⏳ Waiting 20 seconds for documents to be available for counting...")
        time.sleep(20)
    
    # Verify the final document count
    final_count = es.count(index=INDEX_NAME)['count']
    # For Instruqt mode, always expect 500 documents since it uses the 500-line dataset
    if args.instruqt:
        expected_count = 500
    else:
        expected_count = get_expected_document_count(args.use_small_5k_dataset, args.use_500_dataset)
    print(f"📊 Final document count in '{INDEX_NAME}': {final_count}")
    if final_count == expected_count:
        print(f"✅ Success! Expected {expected_count} documents were indexed.")
        return True
    else:
        print(f"⚠️ Expected {expected_count} documents, but {final_count} were indexed.")
        return False

def retry_ingestion_with_instruqt_logic(dataset_url, max_retries=5):
    """Retry ingestion logic specifically for Instruqt workshop settings"""
    for attempt in range(1, max_retries + 1):
        print(f"🔄 Attempt {attempt}/{max_retries} for Instruqt ingestion...")
        
        try:
            # Create index and ingest data
            create_properties_index()
            success = download_and_parallel_bulk_load(dataset_url)
            
            if success:
                print(f"✅ Success on attempt {attempt}!")
                return True
            else:
                print(f"❌ Attempt {attempt} failed - incorrect document count")
                if attempt < max_retries:
                    print("⏳ Waiting 30 seconds before retry...")
                    time.sleep(30)
                else:
                    print(f"❌ All {max_retries} attempts failed")
                    return False
                    
        except Exception as e:
            print(f"❌ Attempt {attempt} failed with error: {e}")
            if attempt < max_retries:
                print("⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
            else:
                print(f"❌ All {max_retries} attempts failed")
                return False

# Main execution logic based on command line arguments
if __name__ == "__main__":
    # Determine which dataset URL to use
    if args.instruqt:
        # When using Instruqt workshop settings, always use the 500-line dataset
        dataset_url = PROPERTIES_500_URL
        print("🎓 Instruqt mode: Using 500-line dataset")
    elif args.use_500_dataset:
        dataset_url = PROPERTIES_500_URL
    elif args.use_small_5k_dataset:
        dataset_url = PROPERTIES_5000_URL
    else:
        dataset_url = PROPERTIES_FULL_URL
    


    # Track if any specific operations were run
    operations_run = False

    if args.searchtemplate:
        print("🎯 Running search template creation...")
        create_search_template()
        print("✅ Search template creation complete!")
        operations_run = True
        
    if args.full_ingestion:
        print("🎯 Running complete data ingestion pipeline...")
        if args.instruqt:
            # Use retry logic for Instruqt
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                create_search_template()
                print("✅ Complete data ingestion pipeline complete!")
                print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search")
            else:
                print("❌ Data ingestion pipeline failed after all retry attempts")
                exit(1)
        else:
            # Regular ingestion for non-Instruqt
            create_properties_index()
            create_search_template()
            download_and_parallel_bulk_load(dataset_url)
            print("✅ Complete data ingestion pipeline complete!")
            print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search with ELSER")
        operations_run = True
        
    if args.recreate_index:
        print("🎯 Running recreate index operation...")
        if args.instruqt:
            # Use retry logic for Instruqt
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                print("✅ Index recreation and data loading complete!")
            else:
                print("❌ Index recreation failed after all retry attempts")
                exit(1)
        else:
            # Regular recreation for non-Instruqt
            create_properties_index()
            download_and_parallel_bulk_load(dataset_url)
            print("✅ Index recreation and data loading complete!")
        operations_run = True
        
    # If no specific flags were provided, run everything
    if not operations_run:
        print("🎯 Running complete property data ingestion...")
        if args.instruqt:
            # Use retry logic for Instruqt
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                create_search_template()
                print("🎉 Property data ingestion and processing complete!")
                print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search")
            else:
                print("❌ Property data ingestion failed after all retry attempts")
                exit(1)
        else:
            # Regular ingestion for non-Instruqt
            create_properties_index()
            create_search_template()
            download_and_parallel_bulk_load(dataset_url)
            print("🎉 Property data ingestion and processing complete!")
            print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search")