#!/usr/bin/env python3

"""
Copyright Elasticsearch B.V. and contributors
SPDX-License-Identifier: Apache-2.0
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from elasticsearch import Elasticsearch
from mcp.server.fastmcp import FastMCP
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# State abbreviations map
STATE_ABBREVIATIONS = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

class ElasticsearchConfig:
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ca_cert: Optional[str] = None,
        google_maps_api_key: Optional[str] = None,
        properties_search_template: str = "properties-search-template",
        inference_id: str = ".elser-2-elasticsearch",
        e5_inference_id: str = ".multilingual-e5-small-elasticsearch"
    ):
        if not url:
            raise ValueError("Elasticsearch URL cannot be empty")
        
        # Validate authentication
        if username and not password:
            raise ValueError("Password must be provided when username is provided")
        if password and not username:
            raise ValueError("Username must be provided when password is provided")
        
        self.url = url
        self.api_key = api_key
        self.username = username
        self.password = password
        self.ca_cert = ca_cert
        self.google_maps_api_key = google_maps_api_key
        self.properties_search_template = properties_search_template
        self.inference_id = inference_id
        self.e5_inference_id = e5_inference_id

def create_elasticsearch_mcp_server(config: ElasticsearchConfig) -> FastMCP:
    """Create and configure the MCP server with Elasticsearch integration."""
    
    # Initialize Elasticsearch client with proper authentication
    if config.api_key:
        # Use API key authentication
        es_client = Elasticsearch(
            config.url,
            api_key=config.api_key,
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=300
        )
    elif config.username and config.password:
        # Use username/password authentication
        es_client = Elasticsearch(
            config.url,
            basic_auth=(config.username, config.password),
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=300
        )
    else:
        raise ValueError("Provide API Key or username/password")
    
    # Create MCP server with port configuration
    port = int(os.getenv("MCP_PORT", "8000"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    mcp = FastMCP(
        name="elasticsearch-mcp-server",
        port=port,
        host=host,
        on_duplicate_tools="error"
    )

    # Create a background task for checking inference endpoints
    async def check_inference_endpoints():
        """Periodically check if the inference endpoints are available."""
        while True:
            # Check ELSER inference endpoint
            if config.inference_id:
                logger.info(f"Checking ELSER inference endpoint: {config.inference_id}")
                try:
                    response = es_client.inference.inference(
                        inference_id=config.inference_id,
                        input=['wake up']
                    )
                    logger.info(f"ELSER inference endpoint is ready: {config.inference_id}")
                except Exception as e:
                    logger.error(f"Failed to connect to ELSER inference endpoint: {str(e)}")
                    logger.error(f"ELSER inference endpoint {config.inference_id} is not available")
            
            # Check E5 inference endpoint
            if config.e5_inference_id:
                logger.info(f"Checking E5 inference endpoint: {config.e5_inference_id}")
                try:
                    response = es_client.inference.inference(
                        inference_id=config.e5_inference_id,
                        input=['wake up']
                    )
                    logger.info(f"E5 inference endpoint is ready: {config.e5_inference_id}")
                except Exception as e:
                    logger.error(f"Failed to connect to E5 inference endpoint: {str(e)}")
                    logger.error(f"E5 inference endpoint {config.e5_inference_id} is not available")
            
            # Wait for 5 minutes before next check
            await asyncio.sleep(300)  # 300 seconds = 5 minutes

    # Start the background task
    loop = asyncio.get_event_loop()
    loop.create_task(check_inference_endpoints())
    
    @mcp.tool()
    async def wake_inference_endpoints() -> Dict[str, Any]:
        """Wake up ELSER and E5 inference endpoints. Returns 'Endpoints Awakened' when successful."""
        results = []
        
        # Wake up ELSER inference endpoint
        if config.inference_id:
            logger.info(f"Manually waking up ELSER inference endpoint: {config.inference_id}")
            try:
                response = es_client.inference.inference(
                    inference_id=config.inference_id,
                    input=['wake up']
                )
                logger.info(f"ELSER inference endpoint is ready: {config.inference_id}")
                results.append(f"✅ ELSER inference endpoint ({config.inference_id}) is ready")
            except Exception as e:
                logger.error(f"Failed to wake up ELSER inference endpoint: {str(e)}")
                results.append(f"❌ ELSER inference endpoint ({config.inference_id}) is not available: {str(e)}")
        else:
            results.append("⚠️ ELSER inference endpoint ID not configured")
        
        # Wake up E5 inference endpoint
        if config.e5_inference_id:
            logger.info(f"Manually waking up E5 inference endpoint: {config.e5_inference_id}")
            try:
                response = es_client.inference.inference(
                    inference_id=config.e5_inference_id,
                    input=['wake up']
                )
                logger.info(f"E5 inference endpoint is ready: {config.e5_inference_id}")
                results.append(f"✅ E5 inference endpoint ({config.e5_inference_id}) is ready")
            except Exception as e:
                logger.error(f"Failed to wake up E5 inference endpoint: {str(e)}")
                results.append(f"❌ E5 inference endpoint ({config.e5_inference_id}) is not available: {str(e)}")
        else:
            results.append("⚠️ E5 inference endpoint ID not configured")
        
        # Determine overall status
        all_ready = all("✅" in result for result in results if "✅" in result or "⚠️" not in result)
        
        # Create user-friendly message
        if all_ready:
            status_message = "Endpoints Awakened"
        else:
            status_message = "Some endpoints failed to awaken"
        
        return {
            "content": [
                {"type": "text", "text": status_message},
                {"type": "text", "text": "\n".join(results)}
            ],
            "data": {
                "status": "awakened" if all_ready else "partial_failure",
                "message": status_message,
                "elser_status": "ready" if config.inference_id and "✅" in results[0] else "not_available",
                "e5_status": "ready" if config.e5_inference_id and "✅" in results[1] else "not_available"
            }
        }
    
    @mcp.tool()
    async def get_properties_template_params() -> Dict[str, Any]:
        """Get the required parameters for the properties search template."""
        try:
            template_id = config.properties_search_template
            
            # Get template from Elasticsearch using the client's get_script API
            try:
                response = es_client.get_script(id=template_id)
                source = response['script']['source']
            except Exception as e:
                logger.error(f"Failed to get template: {str(e)}")
                return {
                    "content": [
                        {"type": "text", "text": f"Error getting template: {str(e)}"}
                    ]
                }
            
            # Find parameters in template
            import re
            param_matches = re.findall(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', source)
            parameters = list(set(param_matches))
            
            logger.info(f"Found parameters for template {template_id}: {', '.join(parameters)}")
            
            return {
                "content": [
                    {"type": "text", "text": "Required parameters for properties search template:"},
                    {"type": "text", "text": ", ".join(parameters)},
                    {"type": "text", "text": "Parameter descriptions:"},
                    {"type": "text", "text": """- query: Main search query (mandatory)
- latitude: Geographic latitude coordinate
- longitude: Geographic longitude coordinate
- distance: Distance from the latitude/longitude in miles. If not provided, default to 25
- bathrooms: Number of bathrooms
- tax: Real estate tax amount
- maintenance: Maintenance fee amount
- square_footage_min: Minimum property square footage. If only a max square footage is provided, set this to 0. otherwise, set this to the minimum square footage specified by the user.
- square_footage_max: Maximum property square footage
- home_price_min: Minimum home price.  If only a max home price is provided, set this to 0. otherwise, set this to the minimum home price specified by the user.
- home_price_max: Maximum home price
- features: Home features such as AC, pool, updated kitches, etc should be listed as a single string For example features such as pool and updated kitchen should be formated as pool updated kitchen"""}
                ],
                "data": {"parameters": parameters}
            }
        except Exception as e:
            logger.error(f"Failed to get template parameters: {str(e)}")
            return {
                "content": [
                    {"type": "text", "text": f"Error: {str(e)}"}
                ]
            }
    
    @mcp.tool()
    async def geocode_location(location: str) -> Dict[str, Any]:
        """Geocode a location string into a geo_point."""
        try:
            if not config.google_maps_api_key:
                logger.error("No Google Maps API key provided")
                return {
                    "content": [
                        {"type": "text", "text": "Error: Google Maps API key not configured"}
                    ]
                }
            
            base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': location,
                'region': 'us',
                'key': config.google_maps_api_key
            }
            
            logger.info(f"Attempting to geocode: '{location}'")
            response = requests.get(base_url, params=params)
            data = response.json()
            
            logger.info(f"Geocoding status: {data.get('status')}")
            
            if data.get('status') != "OK":
                logger.error(f"Google API error: {data.get('status')} - {data.get('error_message', 'No detailed error message')}")
                return {
                    "content": [
                        {"type": "text", "text": f"Geocoding failed: {data.get('status', 'Unknown error')} for location '{location}'"}
                    ]
                }
            
            result = data.get('results', [{}])[0]
            
            # Try fallback variations if needed
            if not result:
                logger.info("No results found, trying variations...")
                
                # Try replacing state abbreviations with full names
                import re
                state_match = re.search(r', ([A-Z]{2})(?:\s|$)', location)
                if state_match:
                    state_abbr = state_match.group(1)
                    full_state_name = STATE_ABBREVIATIONS.get(state_abbr)
                    if full_state_name:
                        fallback_location = location.replace(f", {state_abbr}", f", {full_state_name}")
                        logger.info(f"Trying fallback: '{fallback_location}'")
                        params['address'] = fallback_location
                        fallback_response = requests.get(base_url, params=params)
                        fallback_data = fallback_response.json()
                        result = fallback_data.get('results', [{}])[0]
            
            if not result or 'geometry' not in result or 'location' not in result['geometry']:
                logger.error("No geocoding results found after all attempts")
                return {
                    "content": [
                        {"type": "text", "text": f"Could not geocode location: '{location}'"}
                    ]
                }
            
            geo_point = {
                "latitude": result['geometry']['location']['lat'],
                "longitude": result['geometry']['location']['lng']
            }
            
            logger.info(f"Successfully geocoded to: {json.dumps(geo_point)}")
            return {
                "content": [
                    {"type": "text", "text": f"Geocoded '{location}' to: {json.dumps(geo_point)}"}
                ],
                "data": geo_point
            }
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return {
                "content": [
                    {"type": "text", "text": f"Error: {str(e)}"}
                ]
            }
    
    @mcp.tool()
    async def search_template(
        original_query: str,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        distance: Optional[int] = None,
        tax: Optional[float] = None,
        bedrooms: Optional[int] = None,
        home_price_min: Optional[float] = None,
        home_price_max: Optional[float] = None,
        bathrooms: Optional[float] = None,
        square_footage: Optional[int] = None,
        feature: Optional[str] = None,
        maintenance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a search template with the given parameters."""
        
        try:
            index = os.getenv("ES_INDEX", "properties")
            template_id = "properties-search-template"  # Use the correct template ID
            logger.info(f"Using template ID: {template_id} for index: {index}")
            logger.info(f"Original user query: {original_query}")
            
            # Set default distance if lat/long provided but distance not specified
            if latitude is not None and longitude is not None and distance is None:
                distance = '25'
                logger.info(f"Setting distance default distance to 25")

            params = {
                "query": original_query,
                "latitude": latitude,
                "longitude": longitude,
                "distance": f"{distance}mi" if distance is not None else None,  # Append 'mi' to distance
                "tax": tax,
                "bedrooms": bedrooms,
                "home_price_min": home_price_min,
                "home_price_max": home_price_max,
                "bathrooms": bathrooms,
                "square_footage": square_footage,
                "feature": feature,
                "maintenance": maintenance
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            logger.info(f"Normalized parameters: {json.dumps(params)}")
            
            # Execute search template
            response = es_client.search_template(
                index=index,
                id=template_id,
                params=params
            )
            
            # Extract hits
            hits = response.get('hits', {}).get('hits', [])
            total = response.get('hits', {}).get('total', {}).get('value', 0)
            
            if not hits:
                return {
                    "content": [
                        {"type": "text", "text": f"No results found for query: {original_query}"}
                    ]
                }
            
            # Format results
            results = []
            for hit in hits:
                fields = hit.get('fields', {})
                result = {
                    "title": fields.get('title', ['No title'])[0],
                    "tax": fields.get('annual-tax', ['N/A'])[0],
                    "maintenance": fields.get('maintenance-fee', ['N/A'])[0],
                    "bathrooms": fields.get('number-of-bathrooms', ['N/A'])[0],
                    "bedrooms": fields.get('number-of-bedrooms', ['N/A'])[0],
                    "square_footage": fields.get('square-footage', ['N/A'])[0],
                    "home_price": fields.get('home-price', ['N/A'])[0],
                    "features": fields.get('property-features', ['N/A'])[0]
                }
                results.append(result)
            
            return {
                "content": [
                    {"type": "text", "text": f"Found {total} properties matching your criteria. Here are the top {len(hits)} results:"},
                    {"type": "text", "text": json.dumps(results, indent=2)}
                ],
                "data": {
                    "total": total,
                    "results": results
                }
            }
        except Exception as e:
            logger.error(f"Search template failed: {str(e)}")
            return {
                "content": [
                    {"type": "text", "text": f"Error: {str(e)}"}
                ]
            }
    
    return mcp

def main():
    """Main entry point for the MCP server."""
    config = ElasticsearchConfig(
        url=os.getenv("ES_URL", ""),
        api_key=os.getenv("ES_API_KEY", ""),
        username=os.getenv("ES_USERNAME", ""),
        password=os.getenv("ES_PASSWORD", ""),
        ca_cert=os.getenv("ES_CA_CERT", ""),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        properties_search_template=os.getenv("PROPERTIES_SEARCH_TEMPLATE", ""),
        inference_id=os.getenv("ELSER_INFERENCE_ID", ""),
        e5_inference_id=os.getenv("E5_INFERENCE_ID", "")
    )
    
    server = create_elasticsearch_mcp_server(config)
    
    # Run the server using FastMCP's built-in SSE support
    server.run(transport="sse")

if __name__ == "__main__":
    main() 