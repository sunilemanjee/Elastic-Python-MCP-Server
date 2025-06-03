#!/usr/bin/env python3

import os
import json
from openai import AzureOpenAI
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from elasticsearch import Elasticsearch, helpers, NotFoundError
from elasticsearch.helpers import scan, bulk
import requests
import time

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
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.json")
ELSER_INFERENCE_ID = ".elser-2-elasticsearch"

# Connect to Elasticsearch
if not ES_URL or not ES_API_KEY:
    raise ValueError("ES_URL and ES_API_KEY environment variables must be set")
es = Elasticsearch(hosts=[ES_URL], api_key=ES_API_KEY, request_timeout=300)
es.info()

def create_raw_index():
    mapping = {
      "mappings": {
        "dynamic": "false",
        "properties": {
          "additional_urls": {"type": "keyword"},
          "annual-tax": {"type": "integer"},
          "body_content": {
            "type": "text",
            "copy_to": ["body_content_phrase"]
          },
          "body_content_phrase": {"type": "text"},
          "domains": {"type": "keyword"},
          "full_html": {"type": "text", "index": False},
          "geo_point": {
            "properties": {
              "lat": {"type": "float"},
              "lon": {"type": "float"}
            }
          },
          "location": {"type": "geo_point"},
          "headings": {"type": "text"},
          "home-price": {"type": "integer"},
          "id": {"type": "keyword"},
          "last_crawled_at": {"type": "date"},
          "latitude": {"type": "float"},
          "links": {"type": "keyword"},
          "listing-agent-info": {"type": "text"},
          "longitude": {"type": "float"},
          "maintenance-fee": {"type": "integer"},
          "meta_description": {"type": "text"},
          "meta_keywords": {"type": "keyword"},
          "number-of-bathrooms": {"type": "float"},
          "number-of-bedrooms": {"type": "float"},
          "property-description": {"type": "text"},
          "property-features": {"type": "text"},
          "property-status": {"type": "keyword"},
          "square-footage": {"type": "float"},
          "title": {"type": "text"},
          "url": {"type": "keyword"},
          "url_host": {"type": "keyword"},
          "url_path": {"type": "keyword"},
          "url_path_dir1": {"type": "keyword"},
          "url_path_dir2": {"type": "keyword"},
          "url_path_dir3": {"type": "keyword"},
          "url_port": {"type": "keyword"},
          "url_scheme": {"type": "keyword"}
        }
      }
    }

    if es.indices.exists(index=RAW_INDEX_NAME):
        es.indices.delete(index=RAW_INDEX_NAME)
        print(f"🗑️ Index '{RAW_INDEX_NAME}' deleted.")

    es.indices.create(index=RAW_INDEX_NAME, body=mapping)
    print(f"✅ Index '{RAW_INDEX_NAME}' created.")

create_raw_index()

def create_properties_index():
    mapping = {
      "mappings": {
        "dynamic": "false",
        "properties": {
          "additional_urls": {"type": "keyword"},
          "annual-tax": {"type": "integer"},
          "body_content": {
            "type": "text",
            "copy_to": [ "body_content_semantic"]
          },
          "body_content_semantic": {
            "type": "semantic_text",
            "inference_id": ELSER_INFERENCE_ID,
            "model_settings": {
              "task_type": "sparse_embedding"
            }
          },
          "body_content_phrase": {"type": "text"},
          "domains": {"type": "keyword"},
          "full_html": {"type": "text", "index": False},
          "geo_point": {
            "properties": {
              "lat": {"type": "float"},
              "lon": {"type": "float"}
            }
          },
          "location": {"type": "geo_point"},
          "headings": {"type": "text"},
          "home-price": {"type": "integer"},
          "id": {"type": "keyword"},
          "last_crawled_at": {"type": "date"},
          "latitude": {"type": "float"},
          "links": {"type": "keyword"},
          "listing-agent-info": {"type": "text"},
          "longitude": {"type": "float"},
          "maintenance-fee": {"type": "integer"},
          "meta_description": {"type": "text"},
          "meta_keywords": {"type": "keyword"},
          "number-of-bathrooms": {"type": "float"},
          "number-of-bedrooms": {"type": "float"},
          "property-description": {"type": "text"},
          "property-features": {"type": "text"},
          "property-status": {"type": "keyword"},
          "square-footage": {"type": "float"},
          "title": {"type": "text"},
          "url": {"type": "keyword"},
          "url_host": {"type": "keyword"},
          "url_path": {"type": "keyword"},
          "url_path_dir1": {"type": "keyword"},
          "url_path_dir2": {"type": "keyword"},
          "url_path_dir3": {"type": "keyword"},
          "url_port": {"type": "keyword"},
          "url_scheme": {"type": "keyword"}
        }
      }
    }


    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"🗑️ Index '{INDEX_NAME}' deleted.")

    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"✅ Index '{INDEX_NAME}' created.")

create_properties_index()

"""##Search Template
Removes the existing properties-search-template if present and replaces it with an updated version. This ensures the template is always current and correctly structured for search operations.
"""

search_template_content = {
    "script": {
        "lang": "mustache",
        "source": """{
            "_source": false,
            "size": 5,
            "fields": ["title", "annual-tax", "maintenance-fee", "number-of-bathrooms", "number-of-bedrooms", "square-footage", "home-price", "property-features"],
            "retriever": {
                "standard": {
                    "query": {
                        "semantic": {
                            "field": "body_content_semantic",
                            "query": "{{query}}"
                        }
                    },
                    "filter": {
                        "bool": {
                            "must": [
                                {{#distance}}{
                                    "geo_distance": {
                                        "distance": "{{distance}}",
                                        "location": {
                                            "lat": {{latitude}},
                                            "lon": {{longitude}}
                                        }
                                    }
                                }{{/distance}}
                                {{#bedrooms}}{{#distance}},{{/distance}}{
                                    "range": {
                                        "number-of-bedrooms": {
                                            "gte": {{bedrooms}}
                                        }
                                    }
                                }{{/bedrooms}}
                                {{#bathrooms}}{{#distance}}{{^bedrooms}},{{/bedrooms}}{{/distance}}{{#bedrooms}},{{/bedrooms}}{
                                    "range": {
                                        "number-of-bathrooms": {
                                            "gte": {{bathrooms}}
                                        }
                                    }
                                }{{/bathrooms}}
                                {{#tax}}{{#distance}}{{^bedrooms}}{{^bathrooms}},{{/bathrooms}}{{/bedrooms}}{{/distance}}{{#bedrooms}}{{^bathrooms}},{{/bathrooms}}{{/bedrooms}}{{#bathrooms}},{{/bathrooms}}{
                                    "range": {
                                        "annual-tax": {
                                            "lte": {{tax}}
                                        }
                                    }
                                }{{/tax}}
                                {{#maintenance}}{{#distance}}{{^bedrooms}}{{^bathrooms}}{{^tax}},{{/tax}}{{/bathrooms}}{{/bedrooms}}{{/distance}}{{#bedrooms}}{{^bathrooms}}{{^tax}},{{/tax}}{{/bathrooms}}{{/bedrooms}}{{#bathrooms}}{{^tax}},{{/tax}}{{/bathrooms}}{{#tax}},{{/tax}}{
                                    "range": {
                                        "maintenance-fee": {
                                            "lte": {{maintenance}}
                                        }
                                    }
                                }{{/maintenance}}
                                {{#square_footage}}{{#distance}}{{^bedrooms}}{{^bathrooms}}{{^tax}}{{^maintenance}},{{/maintenance}}{{/tax}}{{/bathrooms}}{{/bedrooms}}{{/distance}}{{#bedrooms}}{{^bathrooms}}{{^tax}}{{^maintenance}},{{/maintenance}}{{/tax}}{{/bathrooms}}{{/bedrooms}}{{#bathrooms}}{{^tax}}{{^maintenance}},{{/maintenance}}{{/tax}}{{/bathrooms}}{{#tax}}{{^maintenance}},{{/maintenance}}{{/tax}}{{#maintenance}},{{/maintenance}}{
                                    "range": {
                                        "square-footage": {
                                            "gte": {{square_footage}}
                                        }
                                    }
                                }{{/square_footage}}
                                {{#home_price}}{{#distance}}{{^bedrooms}}{{^bathrooms}}{{^tax}}{{^maintenance}}{{^square_footage}},{{/square_footage}}{{/maintenance}}{{/tax}}{{/bathrooms}}{{/bedrooms}}{{/distance}}{{#bedrooms}}{{^bathrooms}}{{^tax}}{{^maintenance}}{{^square_footage}},{{/square_footage}}{{/maintenance}}{{/tax}}{{/bathrooms}}{{/bedrooms}}{{#bathrooms}}{{^tax}}{{^maintenance}}{{^square_footage}},{{/square_footage}}{{/maintenance}}{{/tax}}{{/bathrooms}}{{#tax}}{{^maintenance}}{{^square_footage}},{{/square_footage}}{{/maintenance}}{{/tax}}{{#maintenance}}{{^square_footage}},{{/square_footage}}{{/maintenance}}{{#square_footage}},{{/square_footage}}{
                                    "range": {
                                        "home-price": {
                                            "lte": {{home_price}}
                                        }
                                    }
                                }{{/home_price}}
                            ] {{#feature}} ,
                                "should": [
                                    {
                                        "match": {
                                            "property-features": {
                                                "query": "{{feature}}",
                                                "operator": "and"
                                            }
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            {{/feature}}
                        }
                    }
                }
            }
        }"""
    }
}



def delete_search_template(template_id):
    """Deletes the search template if it exists"""
    try:
        es.delete_script(id=template_id)
        print(f"Deleted existing search template: {template_id}")
    except Exception as e:
        if "not_found" in str(e):
            print(f"Search template '{template_id}' not found, skipping delete.")
        else:
            print(f"Error deleting template '{template_id}': {e}")


def create_search_template(
    template_id=TEMPLATE_ID, template_content=search_template_content
):
    """Creates a new search template"""
    try:
        es.put_script(id=template_id, body=template_content)
        print(f"Created search template: {template_id}")
    except Exception as e:
        print(f"Error creating template '{template_id}': {e}")

create_search_template()

"""## Ingest property data"""

def download_and_parallel_bulk_load():
    response = requests.get(PROPERTIES_URL, stream=True)
    response.raise_for_status()

    def generate_actions():
        for line in response.iter_lines():
            if line:
                doc = json.loads(line.decode("utf-8"))
                yield {
                    "_index": RAW_INDEX_NAME,
                    "_source": doc
                }

    success_count = 0
    for ok, result in helpers.parallel_bulk(
        es,
        actions=generate_actions(),
        thread_count=4,
        chunk_size=200,
        request_timeout=60
    ):
        if ok:
            success_count += 1

    print(f"✅ Successfully indexed {success_count} documents into '{RAW_INDEX_NAME}' using parallel_bulk")


download_and_parallel_bulk_load()

"""## Reindex property data into target index which will also host elserized field"""

def async_reindex_with_tracking():
    # Step 1: Start reindexing asynchronously
    response = es.reindex(
        body={
            "source": {"index": RAW_INDEX_NAME},
            "dest": {"index": INDEX_NAME}
        },
        wait_for_completion=False  # Run async
    )

    task_id = response["task"]
    print(f"🚀 Reindex started. Task ID: {task_id}")

    # Step 2: Poll for completion
    while True:
        task_status = es.tasks.get(task_id=task_id)
        completed = task_status.get("completed", False)

        if completed:
            stats = task_status["response"]
            print(f"✅ Reindex complete! {stats['created']} docs reindexed, took {stats['took']}ms")
            break
        else:
            print("⏳ Reindex in progress... checking again in 10 seconds.")
            time.sleep(10)

async_reindex_with_tracking()

"""## Clean up"""

if es.indices.exists(index=RAW_INDEX_NAME):
    es.indices.delete(index=RAW_INDEX_NAME)
    print(f"🗑️ Index '{RAW_INDEX_NAME}' deleted.")