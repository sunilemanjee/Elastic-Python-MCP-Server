#!/usr/bin/env python3

import os
import json
import argparse
from elasticsearch import Elasticsearch, helpers
from elasticsearch.helpers import BulkIndexError
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
parser.add_argument('--ingest-raw-500-dataset', action='store_true',
                   help='Use raw index mapping (no ELSER) with 500-line dataset')
parser.add_argument('--instruqt', action='store_true',
                   help='Use Instruqt workshop settings for Elasticsearch connection')
parser.add_argument('--instruqt-reindex-with-endpoints', action='store_true',
                   help='Reindex properties to original-properties, delete properties, recreate with Instruqt mapping, and reindex 10 documents')
args = parser.parse_args()

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Elasticsearch Configurations
INSTRUQT_WORKSHOP_SETTINGS = args.instruqt

# Use ES_URL for both regular and Instruqt modes
ES_URL = os.getenv('ES_URL')  # expects full URL including scheme (http/https) and port (:443)

if INSTRUQT_WORKSHOP_SETTINGS:
    # Use Instruqt workshop settings
    ES_USERNAME = os.getenv('INSTRUQT_ES_USERNAME')
    ES_PASSWORD = os.getenv('INSTRUQT_ES_PASSWORD')
    
    # For Instruqt, read API key from JSON file using jq pattern
    import subprocess
    try:
        # Execute the jq command to extract API key
        result = subprocess.run([
            'jq', '-r', '.[].credentials.api_key', '/tmp/project_results.json'
        ], capture_output=True, text=True, check=True)
        
        ES_API_KEY = result.stdout.strip()
        if not ES_API_KEY:
            raise ValueError("API key not found in JSON file")
        
        USE_PASSWORD_AUTH = False  # Use API key auth for Instruqt
        print("🎓 Using Instruqt workshop settings for Elasticsearch connection")
        print("🔑 API key extracted from JSON file")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to extract API key from JSON file: {e}")
    except FileNotFoundError:
        raise ValueError("jq command not found. Please install jq for Instruqt workshop settings")
else:
    # Use regular settings
    ES_API_KEY = os.getenv('ES_API_KEY')
    ES_USERNAME = os.getenv('ES_USERNAME')
    ES_PASSWORD = os.getenv('ES_PASSWORD')
    USE_PASSWORD_AUTH = os.getenv('USE_PASSWORD_AUTH', 'false').lower() == 'true'

INDEX_NAME = os.getenv('ES_INDEX', "properties")
TEMPLATE_ID = os.getenv('PROPERTIES_SEARCH_TEMPLATE', "properties-search-template")
ELSER_INFERENCE_ID = os.getenv('ELSER_INFERENCE_ID', ".elser-2-elasticsearch")
E5_INFERENCE_ID = os.getenv('E5_INFERENCE_ID', ".multilingual-e5-small-elasticsearch")
RERANK_INFERENCE_ID = os.getenv('RERANK_INFERENCE_ID', ".rerank-v1-elasticsearch")

# Constants
PROPERTIES_FULL_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties.json"
PROPERTIES_5000_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties-filtered-5000-lines.json"
PROPERTIES_500_URL = "https://sunmanapp.blob.core.windows.net/publicstuff/properties/properties-filtered-500-lines_cleaned_redacted.json"
SEARCH_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "search-template.mustache")
PROPERTIES_INDEX_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "properties-index-mapping.json")
PROPERTIES_INDEX_MAPPING_INSTRUQT_FILE = os.path.join(os.path.dirname(__file__), "properties-index-mapping-instruqt.json")
RAW_INDEX_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "raw-index-mapping.json")

# Determine index name and mapping file based on arguments
if args.ingest_raw_500_dataset:
    INDEX_MAPPING_FILE = RAW_INDEX_MAPPING_FILE
elif args.instruqt_reindex_with_endpoints:
    INDEX_NAME = "properties"
    INDEX_MAPPING_FILE = PROPERTIES_INDEX_MAPPING_INSTRUQT_FILE
else:
    INDEX_MAPPING_FILE = PROPERTIES_INDEX_MAPPING_FILE

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
            mapping_content = f.read()
        
        # Replace placeholder values with environment variables
        mapping_content = mapping_content.replace('"{{ELSER_INFERENCE_ID}}"', f'"{ELSER_INFERENCE_ID}"')
        mapping_content = mapping_content.replace('"{{E5_INFERENCE_ID}}"', f'"{E5_INFERENCE_ID}"')
        mapping_content = mapping_content.replace('"{{RERANK_INFERENCE_ID}}"', f'"{RERANK_INFERENCE_ID}"')
        
        return json.loads(mapping_content)
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
    if args.ingest_raw_500_dataset:
        print(f"🏗️ Creating raw properties index '{INDEX_NAME}' (no ELSER semantic fields)...")
    else:
        print(f"🏗️ Creating properties index '{INDEX_NAME}' with ELSER semantic fields...")
    mapping = load_index_mapping(INDEX_MAPPING_FILE)

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
        for line_num, line in enumerate(response.iter_lines(), 1):
            if line:
                try:
                    doc = json.loads(line.decode("utf-8"))
                    doc_count += 1
                    if doc_count % 1000 == 0:
                        print(f"📊 Processed {doc_count} documents...")
                    yield {
                        "_index": INDEX_NAME,
                        "_source": doc,
                        "_line_number": line_num  # Track line number for error reporting
                    }
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error on line {line_num}: {e}")
        print(f"📊 Total documents to index: {doc_count}")

    print("🚀 Starting parallel bulk indexing...")
    success_count = 0
    error_count = 0
    failed_docs = []  # Track failed documents
    
    # Use smaller chunk size for Instruqt or raw dataset to avoid 413 errors
    chunk_size = 10 if (args.instruqt or args.ingest_raw_500_dataset) else 500
    
    for ok, result in helpers.parallel_bulk(
        es,
        actions=generate_actions(),
        thread_count=4,
        chunk_size=chunk_size,
        request_timeout=600
    ):
        if ok:
            success_count += 1
            if success_count % 1000 == 0:
                print(f"✅ Successfully indexed {success_count} documents...")
        else:
            error_count += 1
            # Capture detailed error information
            error_info = {
                "error_type": result.get("index", {}).get("error", {}).get("type", "unknown"),
                "error_reason": result.get("index", {}).get("error", {}).get("reason", "unknown"),
                "doc_id": result.get("index", {}).get("_id", "unknown"),
                "line_number": result.get("index", {}).get("_line_number", "unknown")
            }
            failed_docs.append(error_info)
            
            if error_count % 100 == 0:
                print(f"❌ Encountered {error_count} errors...")
            elif error_count <= 10:  # Show first 10 errors immediately
                print(f"❌ Error {error_count}: {error_info['error_type']} - {error_info['error_reason']}")

    print(f"✅ Successfully indexed {success_count} documents into '{INDEX_NAME}' using parallel_bulk")
    if error_count > 0:
        print(f"⚠️ Encountered {error_count} errors during indexing")
        
        # Report failed documents in detail
        print(f"\n🔍 DETAILED ERROR REPORT:")
        print(f"Total errors: {error_count}")
        print(f"Failed documents:")
        for i, failed_doc in enumerate(failed_docs, 1):
            print(f"  {i}. Line {failed_doc.get('line_number', 'unknown')}: {failed_doc.get('error_type', 'unknown')} - {failed_doc.get('error_reason', 'unknown')}")
    
    # Add delay for Instruqt or raw dataset to allow documents to be available for counting
    if args.instruqt or args.ingest_raw_500_dataset:
        print("⏳ Waiting 20 seconds for documents to be available for counting...")
        time.sleep(20)
    
    # Verify the final document count
    final_count = es.count(index=INDEX_NAME)['count']
    # For Instruqt mode or raw dataset mode, always expect 500 documents since they use the 500-line dataset
    if args.instruqt or args.ingest_raw_500_dataset:
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

def bulk_load_from_memory(data_lines):
    """Bulk load data from memory (for retry attempts)"""
    print("🚀 Starting parallel bulk indexing from memory...")
    success_count = 0
    error_count = 0
    failed_docs = []  # Track failed documents
    
    # Use smaller chunk size for Instruqt or raw dataset to avoid 413 errors
    chunk_size = 10 if (args.instruqt or args.ingest_raw_500_dataset or args.instruqt_reindex_with_endpoints) else 500
    
    def generate_actions_from_memory():
        doc_count = 0
        for line_num, line in enumerate(data_lines, 1):
            try:
                doc = json.loads(line)
                doc_count += 1
                if doc_count % 1000 == 0:
                    print(f"📊 Processed {doc_count} documents...")
                yield {
                    "_index": INDEX_NAME,
                    "_source": doc,
                    "_line_number": line_num  # Track line number for error reporting
                }
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error on line {line_num}: {e}")
                failed_docs.append({
                    "line_number": line_num,
                    "error": f"JSON decode error: {e}",
                    "raw_line": line[:200] + "..." if len(line) > 200 else line
                })
        print(f"📊 Total documents to index: {doc_count}")
    
    try:
        for ok, result in helpers.parallel_bulk(
            es,
            actions=generate_actions_from_memory(),
            thread_count=4,
            chunk_size=chunk_size,
            request_timeout=600
        ):
            if ok:
                success_count += 1
                if success_count % 1000 == 0:
                    print(f"✅ Successfully indexed {success_count} documents...")
            else:
                error_count += 1
                # Capture detailed error information
                error_info = {
                    "error_type": result.get("index", {}).get("error", {}).get("type", "unknown"),
                    "error_reason": result.get("index", {}).get("error", {}).get("reason", "unknown"),
                    "doc_id": result.get("index", {}).get("_id", "unknown"),
                    "line_number": result.get("index", {}).get("_line_number", "unknown")
                }
                failed_docs.append(error_info)
                
                if error_count % 100 == 0:
                    print(f"❌ Encountered {error_count} errors...")
                elif error_count <= 10:  # Show first 10 errors immediately
                    print(f"❌ Error {error_count}: {error_info['error_type']} - {error_info['error_reason']}")

        print(f"✅ Successfully indexed {success_count} documents into '{INDEX_NAME}' using parallel_bulk")
        if error_count > 0:
            print(f"⚠️ Encountered {error_count} errors during indexing")
            
            # Report failed documents in detail
            print(f"\n🔍 DETAILED ERROR REPORT:")
            print(f"Total errors: {error_count}")
            print(f"Failed documents:")
            for i, failed_doc in enumerate(failed_docs, 1):
                print(f"  {i}. Line {failed_doc.get('line_number', 'unknown')}: {failed_doc.get('error_type', 'unknown')} - {failed_doc.get('error_reason', 'unknown')}")
                if 'raw_line' in failed_doc:
                    print(f"     Raw data: {failed_doc['raw_line']}")
            
            # If using instruqt-reindex-with-endpoints, save failed docs to file
            if args.instruqt_reindex_with_endpoints:
                error_file = "failed_documents.json"
                with open(error_file, 'w') as f:
                    json.dump(failed_docs, f, indent=2)
                print(f"\n💾 Failed document details saved to: {error_file}")
        
        # Add delay for Instruqt or raw dataset to allow documents to be available for counting
        if args.instruqt or args.ingest_raw_500_dataset or args.instruqt_reindex_with_endpoints:
            print("⏳ Waiting 30 seconds for documents to be available for counting...")
            time.sleep(30)
        
        # Verify the final document count
        final_count = es.count(index=INDEX_NAME)['count']
        # For Instruqt mode or raw dataset mode, always expect 500 documents since they use the 500-line dataset
        if args.instruqt or args.ingest_raw_500_dataset or args.instruqt_reindex_with_endpoints:
            expected_count = 500
        else:
            expected_count = get_expected_document_count(args.use_small_5k_dataset, args.use_500_dataset)
        print(f"📊 Final document count in '{INDEX_NAME}': {final_count}")
        
        # If count is close to expected but not quite there, wait a bit more for refresh
        if args.instruqt or args.ingest_raw_500_dataset or args.instruqt_reindex_with_endpoints:
            if final_count >= 400 and final_count < expected_count:
                print(f"📊 Count is close ({final_count}/500), waiting 20 more seconds for refresh...")
                time.sleep(20)
                final_count = es.count(index=INDEX_NAME)['count']
                print(f"📊 Updated document count in '{INDEX_NAME}': {final_count}")
        
        if final_count == expected_count:
            print(f"✅ Success! Expected {expected_count} documents were indexed.")
            return True, failed_docs
        else:
            print(f"⚠️ Expected {expected_count} documents, but {final_count} were indexed.")
            return False, failed_docs
            
    except BulkIndexError as e:
        print(f"❌ BulkIndexError: {e}")
        print(f"📊 Total errors in bulk operation: {len(e.errors)}")
        
        # Extract detailed error information from the BulkIndexError
        for i, error in enumerate(e.errors, 1):
            if 'index' in error:
                index_error = error['index']
                error_info = {
                    "error_type": index_error.get("error", {}).get("type", "unknown"),
                    "error_reason": index_error.get("error", {}).get("reason", "unknown"),
                    "doc_id": index_error.get("_id", "unknown"),
                    "line_number": "unknown"  # We can't get line number from BulkIndexError
                }
                failed_docs.append(error_info)
                print(f"  {i}. Document {error_info['doc_id']}: {error_info['error_type']} - {error_info['error_reason']}")
        
        # Save failed documents to file
        if args.instruqt_reindex_with_endpoints:
            error_file = "failed_documents.json"
            with open(error_file, 'w') as f:
                json.dump(failed_docs, f, indent=2)
            print(f"\n💾 Failed document details saved to: {error_file}")
        
        return False, failed_docs

def retry_ingestion_with_instruqt_logic(dataset_url, max_retries=0):
    """Retry ingestion logic specifically for Instruqt workshop settings or raw dataset ingestion"""
    print(f"📥 Downloading property data from {dataset_url}...")
    response = requests.get(dataset_url, stream=True)
    response.raise_for_status()
    print("✅ Data download completed successfully")
    
    # Store the data in memory for reuse
    data_lines = []
    for line in response.iter_lines():
        if line:
            data_lines.append(line.decode("utf-8"))
    
    print(f"📊 Downloaded {len(data_lines)} documents for retry attempts")
    
    # Track all errors across all attempts
    all_failed_docs = []
    
    # Calculate number of attempts (1 for max_retries=0, max_retries+1 for max_retries>0)
    num_attempts = 1 if max_retries == 0 else max_retries + 1
    
    for attempt in range(1, num_attempts + 1):
        if args.instruqt:
            print(f"🔄 Attempt {attempt}/{num_attempts} for Instruqt ingestion...")
        else:
            print(f"🔄 Attempt {attempt}/{num_attempts} for raw dataset ingestion...")
        
        try:
            print("🏗️ Creating properties index...")
            # Create index and ingest data from memory
            create_properties_index()
            print("🚀 Starting bulk ingestion...")
            success, failed_docs = bulk_load_from_memory(data_lines)
            
            # Collect failed documents from this attempt
            if failed_docs:
                all_failed_docs.extend(failed_docs)
                print(f"📊 Attempt {attempt} had {len(failed_docs)} failed documents")
            
            if success:
                print(f"✅ Success on attempt {attempt}!")
                
                # Even if successful, save any errors that occurred during retries
                if all_failed_docs and args.instruqt_reindex_with_endpoints:
                    error_file = "failed_documents.json"
                    with open(error_file, 'w') as f:
                        json.dump(all_failed_docs, f, indent=2)
                    print(f"💾 All failed document details from retry attempts saved to: {error_file}")
                    print(f"📊 Total errors across all attempts: {len(all_failed_docs)}")
                
                return True
            else:
                print(f"❌ Attempt {attempt} failed - incorrect document count")
                if attempt < num_attempts:
                    print("⏳ Waiting 30 seconds before retry...")
                    time.sleep(30)
                else:
                    print(f"❌ All {num_attempts} attempts failed")
                    
                    # Save all failed documents from all attempts
                    if all_failed_docs and args.instruqt_reindex_with_endpoints:
                        error_file = "failed_documents.json"
                        with open(error_file, 'w') as f:
                            json.dump(all_failed_docs, f, indent=2)
                        print(f"💾 All failed document details from all attempts saved to: {error_file}")
                        print(f"📊 Total errors across all attempts: {len(all_failed_docs)}")
                    
                    return False
                    
        except Exception as e:
            print(f"❌ Attempt {attempt} failed with error: {e}")
            import traceback
            print(f"🔍 Full error details:")
            traceback.print_exc()
            
            if attempt < num_attempts:
                print("⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
            else:
                print(f"❌ All {num_attempts} attempts failed")
                
                # Save any failed documents we collected
                if all_failed_docs and args.instruqt_reindex_with_endpoints:
                    error_file = "failed_documents.json"
                    with open(error_file, 'w') as f:
                        json.dump(all_failed_docs, f, indent=2)
                    print(f"💾 Failed document details saved to: {error_file}")
                
                return False

def create_raw_properties_index():
    """Create and ingest data into raw properties index"""
    print(f"🏗️ Creating raw properties index '{INDEX_NAME}' (no ELSER semantic fields)...")
    mapping = load_index_mapping(RAW_INDEX_MAPPING_FILE)

    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"🗑️ Index '{INDEX_NAME}' deleted.")

    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"✅ Index '{INDEX_NAME}' created.")

def ingest_raw_properties_data(dataset_url):
    """Ingest data into raw properties index"""
    print(f"📥 Downloading property data for raw index from {dataset_url}...")
    response = requests.get(dataset_url, stream=True)
    response.raise_for_status()
    print("✅ Data download started successfully")

    def generate_actions():
        doc_count = 0
        for line_num, line in enumerate(response.iter_lines(), 1):
            if line:
                try:
                    doc = json.loads(line.decode("utf-8"))
                    doc_count += 1
                    if doc_count % 1000 == 0:
                        print(f"📊 Processed {doc_count} documents...")
                    yield {
                        "_index": INDEX_NAME,
                        "_source": doc,
                        "_line_number": line_num  # Track line number for error reporting
                    }
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error on line {line_num}: {e}")
        print(f"📊 Total documents to index: {doc_count}")

    print("🚀 Starting parallel bulk indexing for raw properties...")
    success_count = 0
    error_count = 0
    failed_docs = []  # Track failed documents
    
    # Use smaller chunk size for Instruqt to avoid 413 errors
    chunk_size = 10
    
    for ok, result in helpers.parallel_bulk(
        es,
        actions=generate_actions(),
        thread_count=4,
        chunk_size=chunk_size,
        request_timeout=600
    ):
        if ok:
            success_count += 1
            if success_count % 1000 == 0:
                print(f"✅ Successfully indexed {success_count} documents...")
        else:
            error_count += 1
            # Capture detailed error information
            error_info = {
                "error_type": result.get("index", {}).get("error", {}).get("type", "unknown"),
                "error_reason": result.get("index", {}).get("error", {}).get("reason", "unknown"),
                "doc_id": result.get("index", {}).get("_id", "unknown"),
                "line_number": result.get("index", {}).get("_line_number", "unknown")
            }
            failed_docs.append(error_info)
            
            if error_count % 100 == 0:
                print(f"❌ Encountered {error_count} errors...")
            elif error_count <= 10:  # Show first 10 errors immediately
                print(f"❌ Error {error_count}: {error_info['error_type']} - {error_info['error_reason']}")

    print(f"✅ Successfully indexed {success_count} documents into '{INDEX_NAME}' using parallel_bulk")
    if error_count > 0:
        print(f"⚠️ Encountered {error_count} errors during indexing")
        
        # Report failed documents in detail
        print(f"\n🔍 DETAILED ERROR REPORT:")
        print(f"Total errors: {error_count}")
        print(f"Failed documents:")
        for i, failed_doc in enumerate(failed_docs, 1):
            print(f"  {i}. Line {failed_doc.get('line_number', 'unknown')}: {failed_doc.get('error_type', 'unknown')} - {failed_doc.get('error_reason', 'unknown')}")
    
    # Add delay for Instruqt to allow documents to be available for counting
    print("⏳ Waiting 20 seconds for documents to be available for counting...")
    time.sleep(20)
    
    # Verify the final document count
    final_count = es.count(index=INDEX_NAME)['count']
    expected_count = 500  # Always expect 500 documents for Instruqt
    print(f"📊 Final document count in '{INDEX_NAME}': {final_count}")
    if final_count == expected_count:
        print(f"✅ Success! Expected {expected_count} documents were indexed in raw properties.")
        return True
    else:
        print(f"⚠️ Expected {expected_count} documents, but {final_count} were indexed in raw properties.")
        return False

def instruqt_reindex_with_endpoints():
    """Perform reindexing operation for Instruqt with endpoints"""
    print("🎯 Running Instruqt reindex with endpoints operation...")
    
    # Step 1: Reindex properties to original-properties
    print("📋 Step 1: Reindexing properties to original-properties...")
    try:
        reindex_response = es.reindex(
            body={
                "source": {
                    "index": "properties"
                },
                "dest": {
                    "index": "original-properties"
                }
            },
            wait_for_completion=False
        )
        task_id = reindex_response['task']
        print(f"✅ Reindex task started with ID: {task_id}")
        
        # Wait for the reindex task to complete
        print("⏳ Waiting for reindex task to complete...")
        start_time = time.time()
        poll_count = 0
        while True:
            task_status = es.tasks.get(task_id=task_id)
            if task_status['completed']:
                elapsed_time = time.time() - start_time
                print(f"✅ Reindex to original-properties completed (took {elapsed_time:.1f} seconds)")
                break
            poll_count += 1
            elapsed_time = time.time() - start_time
            print(f"⏳ Still waiting... (poll #{poll_count}, {elapsed_time:.1f}s elapsed)")
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Failed to reindex properties to properties-original: {e}")
        return False
    
    # Step 2: Delete properties index
    print("🗑️ Step 2: Deleting properties index...")
    try:
        if es.indices.exists(index="properties"):
            es.indices.delete(index="properties")
            print("✅ Properties index deleted")
        else:
            print("⚠️ Properties index does not exist, skipping deletion")
    except Exception as e:
        print(f"❌ Failed to delete properties index: {e}")
        return False
    
    # Step 3: Create properties index with Instruqt mapping
    print("📋 Step 3: Creating properties index with Instruqt mapping...")
    try:
        mapping = load_index_mapping(PROPERTIES_INDEX_MAPPING_INSTRUQT_FILE)
        es.indices.create(index="properties", body=mapping)
        print("✅ Properties index created with Instruqt mapping")
    except Exception as e:
        print(f"❌ Failed to create properties index: {e}")
        return False
    
    # Step 4: Delete properties index again
    print("🗑️ Step 4: Deleting properties index again...")
    try:
        if es.indices.exists(index="properties"):
            es.indices.delete(index="properties")
            print("✅ Properties index deleted again")
        else:
            print("⚠️ Properties index does not exist, skipping deletion")
    except Exception as e:
        print(f"❌ Failed to delete properties index: {e}")
        return False
    
    # Step 5: Reindex 10 documents from original-properties to properties
    print("📋 Step 5: Reindexing 10 documents from original-properties to properties...")
    try:
        # First recreate the properties index
        mapping = load_index_mapping(PROPERTIES_INDEX_MAPPING_INSTRUQT_FILE)
        es.indices.create(index="properties", body=mapping)
        print("✅ Properties index recreated with Instruqt mapping")
        
        # Now reindex 10 documents
        reindex_response = es.reindex(
            body={
                "source": {
                    "index": "original-properties",
                    "size": 10
                },
                "dest": {
                    "index": "properties"
                }
            },
            wait_for_completion=False
        )
        task_id = reindex_response['task']
        print(f"✅ Reindex task started with ID: {task_id}")
        
        # Wait for the reindex task to complete
        print("⏳ Waiting for reindex task to complete...")
        start_time = time.time()
        poll_count = 0
        while True:
            task_status = es.tasks.get(task_id=task_id)
            if task_status['completed']:
                elapsed_time = time.time() - start_time
                print(f"✅ Reindex of 10 documents completed (took {elapsed_time:.1f} seconds)")
                break
            poll_count += 1
            elapsed_time = time.time() - start_time
            print(f"⏳ Still waiting... (poll #{poll_count}, {elapsed_time:.1f}s elapsed)")
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Failed to reindex documents: {e}")
        return False
    
    print("🎉 Instruqt reindex with endpoints operation completed successfully!")
    return True

# Main execution logic based on command line arguments
if __name__ == "__main__":
    # Determine which dataset URL to use
    if args.ingest_raw_500_dataset:
        # When using raw index mapping, always use the 500-line dataset
        dataset_url = PROPERTIES_500_URL
        print("📊 Raw index mode: Using 500-line dataset")
    elif args.instruqt:
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
            # Use retry logic for Instruqt and also create raw properties index
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                # Also create and ingest raw properties index
                print("🎯 Creating and ingesting raw properties index...")
                create_raw_properties_index()
                raw_success = ingest_raw_properties_data(dataset_url)
                if raw_success:
                    create_search_template()
                    print("✅ Complete data ingestion pipeline complete!")
                    print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search")
                    print(f"📋 Final index '{INDEX_NAME}' is ready for basic search (no ELSER)")
                else:
                    print("❌ Raw properties index creation failed")
                    exit(1)
            else:
                print("❌ Data ingestion pipeline failed after all retry attempts")
                exit(1)
        elif args.ingest_raw_500_dataset:
            # Use retry logic for raw dataset
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                create_search_template()
                print("✅ Complete data ingestion pipeline complete!")
                print(f"📋 Final index '{INDEX_NAME}' is ready for basic search (no ELSER)")
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
            # Use retry logic for Instruqt and also create raw properties index
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                # Also create and ingest raw properties index
                print("🎯 Creating and ingesting raw properties index...")
                create_raw_properties_index()
                raw_success = ingest_raw_properties_data(dataset_url)
                if raw_success:
                    print("✅ Index recreation and data loading complete!")
                else:
                    print("❌ Raw properties index creation failed")
                    exit(1)
            else:
                print("❌ Index recreation failed after all retry attempts")
                exit(1)
        elif args.ingest_raw_500_dataset:
            # Use retry logic for raw dataset
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
        
    if args.instruqt_reindex_with_endpoints:
        print("🎯 Running Instruqt reindex with endpoints operation...")
        
        # Call the new reindexing function
        success = instruqt_reindex_with_endpoints()
        if success:
            print("✅ Instruqt reindex with endpoints complete!")
            print(f"📋 Index 'properties' is ready with Instruqt mapping and 10 reindexed documents")
        else:
            print("❌ Instruqt reindex with endpoints failed")
            exit(1)
        operations_run = True
        
    # If no specific flags were provided, run everything
    if not operations_run:
        print("🎯 Running complete property data ingestion...")
        if args.instruqt:
            # Use retry logic for Instruqt and also create raw properties index
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                # Also create and ingest raw properties index
                print("🎯 Creating and ingesting raw properties index...")
                create_raw_properties_index()
                raw_success = ingest_raw_properties_data(dataset_url)
                if raw_success:
                    create_search_template()
                    print("🎉 Property data ingestion and processing complete!")
                    print(f"📋 Final index '{INDEX_NAME}' is ready for semantic search")
                    print(f"📋 Final index 'raw_properties' is ready for basic search (no ELSER)")
                else:
                    print("❌ Raw properties index creation failed")
                    exit(1)
            else:
                print("❌ Property data ingestion failed after all retry attempts")
                exit(1)
        elif args.ingest_raw_500_dataset:
            # Use retry logic for raw dataset
            success = retry_ingestion_with_instruqt_logic(dataset_url)
            if success:
                create_search_template()
                print("🎉 Property data ingestion and processing complete!")
                print(f"📋 Final index '{INDEX_NAME}' is ready for basic search (no ELSER)")
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