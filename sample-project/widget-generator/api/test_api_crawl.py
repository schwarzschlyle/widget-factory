import requests
from genson import SchemaBuilder

BASE_URL = "https://pokeapi.co/api/v2/"

def fetch_root_endpoints():
    return requests.get(BASE_URL).json()

def infer_schema_from_sample(url):
    # try fetching "1" if it's a paginated endpoint
    if url.endswith("/"):
        sample_url = url + "1/"
    else:
        sample_url = url + "/1/"
    
    try:
        response = requests.get(sample_url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"⚠️ Could not fetch {sample_url}: {e}")
        return None
    
    # infer schema
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()

def main():
    root_endpoints = fetch_root_endpoints()
    combined_schema = {}

    for name, url in root_endpoints.items():
        print(f"Processing {name} → {url}")
        schema = infer_schema_from_sample(url)
        if schema:
            combined_schema[name] = schema
    
    # save to file
    import json
    with open("pokeapi_combined_schema.json", "w") as f:
        json.dump(combined_schema, f, indent=2)

    print("✅ Combined schema saved to pokeapi_combined_schema.json")

if __name__ == "__main__":
    main()
