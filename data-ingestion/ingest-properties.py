#!/usr/bin/env python3

import os
import json
import argparse
from openai import AzureOpenAI
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from elasticsearch import Elasticsearch, helpers, NotFoundError
from elasticsearch.helpers import scan, bulk
import requests
import time

# Parse command line arguments
parser = argparse.ArgumentParser(description='Property data ingestion script with ELSER semantic processing')
parser.add_argument('--searchtemplate', action='store_true', 
                   help='Only run the search template creation part')
parser.add_argument('--full-ingestion', action='store_true', 
                   help='Only run the complete data ingestion pipeline (create indices, download data, process with ELSER)')
parser.add_argument('--reindex', action='store_true', 
                   help='Only run the reindex operation (recreates properties index, requires existing raw index)')
parser.add_argument('--recreate-index', action='store_true', 
                   help='Only delete and recreate the properties index (no data processing)')
parser.add_argument('--use-small-dataset', action='store_true',
                   help='Use the smaller 5000-line dataset instead of the full dataset')
args = parser.parse_args()

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Elasticsearch Configurations
ES_URL = os.getenv('ES_URL' ) ## expects full URL including scheme (http/https) and port (:443) 
ES_API_KEY = os.getenv('ES_API_KEY')

# Constants
RAW_INDEX_NAME = "properties_raw"
INDEX_NAME = "properties"
TEMPLATE_ID = "properties-search-template"
PROPERTIES_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties.json"
PROPERTIES_5000_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties-filtered-5000-lines.json"
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.json")
ELSER_INFERENCE_ID = ".elser-2-elasticsearch"
SEARCH_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "search-template.mustache")
RAW_INDEX_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "raw-index-mapping.json")
PROPERTIES_INDEX_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "properties-index-mapping.json")

def get_expected_document_count(use_small_dataset=False):
    """Return the expected number of documents based on the dataset being used"""
    if use_small_dataset:
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
if not ES_URL or not ES_API_KEY:
    raise ValueError("ES_URL and ES_API_KEY environment variables must be set")
es = Elasticsearch(
    hosts=[ES_URL], 
    api_key=ES_API_KEY, 
    request_timeout=600,
    retry_on_timeout=True,
    max_retries=10
)
es.info()
print("✅ Connected to Elasticsearch successfully")

def check_elser_deployment():
    """Check if ELSER is properly deployed by making a test inference call"""
    try:
        print("🔍 Checking ELSER deployment...")
        response = es.inference.inference(
            inference_id=ELSER_INFERENCE_ID,
            input=['wake up']
        )
        print("✅ ELSER is properly deployed and ready to use")
        return True
    except Exception as e:
        print(f"❌ Error checking ELSER deployment: {e}")
        print("Please ensure ELSER is properly deployed before proceeding")
        return False

def create_raw_index():
    print(f"🏗️ Creating raw index '{RAW_INDEX_NAME}'...")
    mapping = load_index_mapping(RAW_INDEX_MAPPING_FILE)

    if es.indices.exists(index=RAW_INDEX_NAME):
        es.indices.delete(index=RAW_INDEX_NAME)
        print(f"🗑️ Index '{RAW_INDEX_NAME}' deleted.")

    es.indices.create(index=RAW_INDEX_NAME, body=mapping)
    print(f"✅ Index '{RAW_INDEX_NAME}' created.")

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
        properties_url = PROPERTIES_URL
    
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
                    "_index": RAW_INDEX_NAME,
                    "_source": doc
                }
        print(f"📊 Total documents to index: {doc_count}")

    print("🚀 Starting parallel bulk indexing...")
    success_count = 0
    error_count = 0
    
    for ok, result in helpers.parallel_bulk(
        es,
        actions=generate_actions(),
        thread_count=4,
        chunk_size=500,
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

    print(f"✅ Successfully indexed {success_count} documents into '{RAW_INDEX_NAME}' using parallel_bulk")
    if error_count > 0:
        print(f"⚠️ Encountered {error_count} errors during indexing")

def async_reindex_with_tracking():
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        print(f"🔄 Starting reindex from '{RAW_INDEX_NAME}' to '{INDEX_NAME}' with ELSER semantic processing...")
        if retry_count > 0:
            print(f"🔄 Retry attempt {retry_count}/{max_retries}")
        
        # Step 1: Start reindexing asynchronously
        response = es.reindex(
            body={
                "source": {"index": RAW_INDEX_NAME, "size": 500 },
                "dest": {"index": INDEX_NAME}
            },
            wait_for_completion=False  # Run async
        )

        task_id = response["task"]
        print(f"🚀 Reindex started. Task ID: {task_id}")

        # Step 2: Poll for completion
        start_time = time.time()
        while True:
            task_status = es.tasks.get(task_id=task_id)
            completed = task_status.get("completed", False)

            if completed:
                stats = task_status["response"]
                elapsed_time = time.time() - start_time
                print(f"✅ Reindex complete!")
                print(f"   📊 {stats['created']} docs reindexed")
                print(f"   ⏱️ Took {stats['took']}ms (wall time: {elapsed_time:.1f}s)")
                print(f"   📈 Rate: {stats['created'] / (elapsed_time/60):.0f} docs/minute")
                
                # Check if we got the expected number of documents
                if stats['created'] == get_expected_document_count(args.use_small_dataset):
                    print(f"✅ Success! Expected {get_expected_document_count(args.use_small_dataset)} documents were created.")
                    return  # Success, exit the retry loop
                else:
                    print(f"❌ Expected {get_expected_document_count(args.use_small_dataset)} documents, but only {stats['created']} were created.")
                    if retry_count < max_retries:
                        print(f"🗑️ Deleting destination index '{INDEX_NAME}' and retrying...")
                        if es.indices.exists(index=INDEX_NAME):
                            es.indices.delete(index=INDEX_NAME)
                            print(f"🗑️ Index '{INDEX_NAME}' deleted.")
                        retry_count += 1
                        break  # Break out of the polling loop to retry
                    else:
                        print(f"❌ Max retries ({max_retries}) reached. Reindex failed to create expected number of documents.")
                        raise Exception(f"Reindex failed: expected {get_expected_document_count(args.use_small_dataset)} documents, got {stats['created']}")
                break
            else:
                # Get progress info if available
                if "status" in task_status:
                    status = task_status["status"]
                    if "total" in status and "updated" in status:
                        total = status["total"]
                        updated = status["updated"]
                        if total > 0:
                            progress = (updated / total) * 100
                            print(f"⏳ Reindex progress: {progress:.1f}% ({updated}/{total})")
                        else:
                            print("⏳ Reindex in progress...")
                    else:
                        print("⏳ Reindex in progress...")
                else:
                    print("⏳ Reindex in progress...")
                print("   Checking again in 10 seconds...")
                time.sleep(10)

def cleanup_raw_index():
    print("🧹 Cleaning up temporary index...")
    if es.indices.exists(index=RAW_INDEX_NAME):
        es.indices.delete(index=RAW_INDEX_NAME)
        print(f"🗑️ Index '{RAW_INDEX_NAME}' deleted.")

# Main execution logic based on command line arguments
if __name__ == "__main__":
    # Determine which dataset URL to use
    dataset_url = PROPERTIES_5000_URL if args.use_small_dataset else PROPERTIES_URL
    
    # Check ELSER deployment before proceeding (only if not just search template)
    if not args.searchtemplate:
        if not check_elser_deployment():
            raise SystemExit("ELSER deployment check failed. Please deploy ELSER before proceeding.")

    # Track if any specific operations were run
    operations_run = False

    if args.searchtemplate:
        print("🎯 Running search template creation...")
        create_search_template()
        print("✅ Search template creation complete!")
        operations_run = True
        
    if args.full_ingestion:
        print("🎯 Running complete data ingestion pipeline...")
        create_raw_index()
        create_properties_index()
        create_search_template()
        download_and_parallel_bulk_load(dataset_url)
        async_reindex_with_tracking()
        cleanup_raw_index()
        print("✅ Complete data ingestion pipeline complete!")
        print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search with ELSER")
        operations_run = True
        
    if args.reindex:
        print("🎯 Running reindex operation...")
        # Check if raw index exists
        if not es.indices.exists(index=RAW_INDEX_NAME):
            print(f"❌ Raw index '{RAW_INDEX_NAME}' does not exist. Please run with --full-ingestion first.")
            exit(1)
        
        # Delete and recreate the properties index to ensure clean state
        print(f"🗑️ Deleting and recreating properties index '{INDEX_NAME}'...")
        if es.indices.exists(index=INDEX_NAME):
            es.indices.delete(index=INDEX_NAME)
            print(f"🗑️ Index '{INDEX_NAME}' deleted.")
        
        create_properties_index()
        
        async_reindex_with_tracking()
        print("✅ Reindex operation complete!")
        operations_run = True
        
    if args.recreate_index:
        print("🎯 Running recreate index operation...")
        create_raw_index()
        create_properties_index()
        download_and_parallel_bulk_load(dataset_url)
        print("✅ Index recreation and data loading complete!")
        operations_run = True
        
    # If no specific flags were provided, run everything
    if not operations_run:
        print("🎯 Running complete property data ingestion...")
        # Run everything
        create_raw_index()
        create_properties_index()
        create_search_template()
        download_and_parallel_bulk_load(dataset_url)
        async_reindex_with_tracking()
        cleanup_raw_index()
        print("🎉 Property data ingestion and processing complete!")
        print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search with ELSER")