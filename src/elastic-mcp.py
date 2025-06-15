import requests
from typing import Any, Dict, List, Optional
from elasticsearch import Elasticsearch

class Elastic():
    def __init__(
            self, 
            es_url: str = "localhost",
            api_key: Optional[str] = None,
            verify_ssl: bool = False,
        ):
        self.es_url = es_url
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.request_timeout = 300
        
        # Initialize Elasticsearch client
        self.es = Elasticsearch(
                self.es_url,
                api_key=self.api_key,
                verify_certs=self.verify_ssl,
                ssl_show_warn=False,
                request_timeout=self.request_timeout
            )


    def get_base_url(self) -> str:
        return f'{self.protocol}://{self.host}:{self.port}'

    def _safe_call(self, f) -> Any:
        try:
            return f()
        except Exception as e:
            raise Exception(f"Elasticsearch operation failed: {str(e)}")

    def create_index(self, index_name: str, mappings: Dict = None) -> Any:
        """Create a new index with optional mappings."""
        def call_fn():
            return self.es.indices.create(index=index_name, mappings=mappings)
        return self._safe_call(call_fn)

    def delete_index(self, index_name: str) -> Any:
        """Delete an index."""
        def call_fn():
            return self.es.indices.delete(index=index_name)
        return self._safe_call(call_fn)

    def index_document(self, index_name: str, document: Dict, doc_id: Optional[str] = None) -> Any:
        """Index a document into Elasticsearch."""
        def call_fn():
            return self.es.index(index=index_name, document=document, id=doc_id)
        return self._safe_call(call_fn)

    def get_document(self, index_name: str, doc_id: str) -> Any:
        """Retrieve a document by ID."""
        def call_fn():
            return self.es.get(index=index_name, id=doc_id)
        return self._safe_call(call_fn)

    def search(self, index_name: str, query: Dict) -> Any:
        """Search documents using Elasticsearch query DSL."""
        def call_fn():
            return self.es.search(index=index_name, query=query)
        return self._safe_call(call_fn)

    def update_document(self, index_name: str, doc_id: str, doc: Dict) -> Any:
        """Update a document by ID."""
        def call_fn():
            return self.es.update(index=index_name, id=doc_id, doc=doc)
        return self._safe_call(call_fn)

    def delete_document(self, index_name: str, doc_id: str) -> Any:
        """Delete a document by ID."""
        def call_fn():
            return self.es.delete(index=index_name, id=doc_id)
        return self._safe_call(call_fn)

    def bulk_index(self, index_name: str, documents: List[Dict]) -> Any:
        """Bulk index multiple documents."""
        def call_fn():
            actions = [
                {"_index": index_name, "_source": doc}
                for doc in documents
            ]
            return self.es.bulk(operations=actions)
        return self._safe_call(call_fn)

    def get_indices(self) -> Any:
        """Get list of all indices."""
        def call_fn():
            return self.es.indices.get_alias().keys()
        return self._safe_call(call_fn)

    def get_index_stats(self, index_name: str) -> Any:
        """Get statistics for an index."""
        def call_fn():
            return self.es.indices.stats(index=index_name)
        return self._safe_call(call_fn)

    def get_cluster_health(self) -> Any:
        """Get cluster health information."""
        def call_fn():
            return self.es.cluster.health()
        return self._safe_call(call_fn)

    def get_cluster_stats(self) -> Any:
        """Get cluster statistics."""
        def call_fn():
            return self.es.cluster.stats()
        return self._safe_call(call_fn)