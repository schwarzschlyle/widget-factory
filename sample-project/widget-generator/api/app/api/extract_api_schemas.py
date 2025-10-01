import requests
from genson import SchemaBuilder
from app.core.config import settings

def fetch_root_endpoints(base_url):
    """Fetch the root endpoints from the given base API URL."""
    headers = settings.DATASOURCE_AUTH_HEADERS.get(base_url, {})
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    return response.json()

def infer_schema_from_sample(url, base_url=None):
    """Try to fetch a sample resource and infer its JSON schema."""
    # Try fetching "1" if it's a paginated endpoint
    if url.endswith("/"):
        sample_url = url + "1/"
    else:
        sample_url = url + "/1/"
    headers = {}
    if base_url:
        headers = settings.DATASOURCE_AUTH_HEADERS.get(base_url, {})
    try:
        response = requests.get(sample_url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"⚠️ Could not fetch {sample_url}: {e}")
        return None
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()

import json
import re

def extract_schemas_from_api(base_url):
    """
    Given a base API URL, fetch all root endpoints and infer their JSON schemas.
    Returns a dict mapping endpoint names to inferred schemas.
    Also saves the combined schema to a file named "{endpoint}_schema.json".
    """
    root_endpoints = fetch_root_endpoints(base_url)
    combined_schema = {}
    for name, url in root_endpoints.items():
        print(f"Processing {name} → {url}")
        schema = infer_schema_from_sample(url, base_url=base_url)
        if schema:
            combined_schema[name] = schema

    # Sanitize base_url for filename
    endpoint_name = re.sub(r'[^a-zA-Z0-9]+', '_', base_url).strip('_')
    filename = f"{endpoint_name}_schema.json"
    with open(filename, "w") as f:
        json.dump(combined_schema, f, indent=2)
    print(f"✅ Combined schema saved to {filename}")

    return combined_schema
