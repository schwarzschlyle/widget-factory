from app.core.celery_app import celery_app
from app.core.config import settings
from langchain_openai import OpenAI, ChatOpenAI
from langchain_core.messages import HumanMessage
import requests
import json
from app.api.extract_api_schemas import extract_schemas_from_api

# sample celery task
@celery_app.task(name="app.tasks.langchain_task.run_langchain")
def run_langchain(num1: float, num2: float) -> str:
    """
    Use a prompt template to ask the LLM to add two numbers.
    """
    prompt = f"What is {num1} + {num2}?"
    llm = OpenAI(openai_api_key=settings.OPENAI_API_KEY, temperature=0)
    result = llm.invoke(prompt)
    return result

# Celery task to generate OpenAPI 3.1.1 spec from discovered schemas
@celery_app.task(name="app.tasks.langchain_task.generate_openapi_spec_from_schemas")
def generate_openapi_spec_from_schemas() -> dict:
    """
    Always generate and overwrite openapi-schema.json with a new OpenAPI 3.1.1 specification.
    Returns a dict with type: "openapi" and schema: (the OpenAPI 3.1.1 spec as JSON).
    """
    import os

    schema_path = "openapi-schema.json"

    endpoints = settings.DATASOURCES_API_ENDPOINTS
    schemas = {}

    # Fetch schemas synchronously using the helper
    for url in endpoints:
        try:
            schemas.update(extract_schemas_from_api(url))
        except Exception as e:
            schemas[url] = {"error": str(e)}

    schemas_str = json.dumps(schemas, indent=2)
    # OpenAPI 3.1.1 documentation context (shortened for prompt size)
    # Determine which endpoints require Authorization from DATASOURCE_AUTH_HEADERS
    auth_endpoints = [
        url for url, headers in getattr(settings, "DATASOURCE_AUTH_HEADERS", {}).items()
        if "Authorization" in headers and headers["Authorization"].startswith("Bearer ")
    ]
    openapi_context = (
        "You are an expert API designer. Given the following discovered API endpoints and their JSON schemas, "
        "generate a complete, valid OpenAPI 3.1.1 specification (in JSON, not YAML) that describes these endpoints. "
        "Follow the OpenAPI 3.1.1 specification strictly. "
        "Include all required fields: openapi, info, servers, paths, components, etc. "
        "For the 'servers' field, use the following actual endpoint URLs (do NOT use example.com or placeholders):\n"
        f"{json.dumps([{'url': url} for url in endpoints], indent=2)}\n"
        "Use the schemas as the basis for the components/schemas section. "
        "For each endpoint, infer the HTTP method (GET if unknown), and create a path with a response schema. "
        "If you are unsure about details, make reasonable assumptions. "
        f"IMPORTANT: The following endpoints require an Authorization header with a Bearer token and must have security: [{{bearerAuth: []}}]:\n{json.dumps(auth_endpoints, indent=2)}\n"
        "You MUST include a securitySchemes section in components with a bearerAuth scheme (type: http, scheme: bearer, bearerFormat: JWT). "
        "You MUST add a security: [ { bearerAuth: [] } ] requirement ONLY to the paths/operations for the endpoints listed above. "
        "Do NOT add security to endpoints not listed above. "
        "Output ONLY the OpenAPI JSON object, no explanation or markdown.\n"
        f"Discovered schemas:\n{schemas_str}\n"
        "Respond ONLY with the OpenAPI 3.1.1 JSON object."
    )

    llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-4.1", temperature=0.2, max_tokens=20000)
    result = llm.invoke([HumanMessage(content=openapi_context)])
    if hasattr(result, "content"):
        result = result.content

    # Try to parse the LLM's response as JSON
    import time
    import re
    try:
        openapi_spec = json.loads(result)
        # Overwrite the "servers" field with the actual endpoints
        openapi_spec["servers"] = [{"url": url} for url in endpoints]
        # Save OpenAPI spec to file
        with open(schema_path, "w") as f:
            json.dump(openapi_spec, f, indent=2)
        print(f"✅ OpenAPI spec saved to {schema_path}")
        return {"type": "openapi", "schema": openapi_spec}
    except Exception as e:
        return {"error": f"Failed to parse LLM response as JSON: {str(e)}", "raw_response": result}

# Celery task to generate widget ideas from OpenAPI spec
@celery_app.task(name="app.tasks.langchain_task.suggest_widgets_from_openapi")
def suggest_widgets_from_openapi(openapi_spec: dict) -> list:
    """
    Feed an OpenAPI 3.1.1 specification to the LLM and suggest N widget ideas.
    Returns a list of dicts with widget_title, widget_description, endpoint, and data_combination.
    """
    openapi_str = json.dumps(openapi_spec, indent=2)
    count = settings.WIDGET_GENERATION_COUNT
    prompt = (
        "You are an expert dashboard widget designer and frontend engineer. "
        "You are given an OpenAPI 3.1.1 specification describing a set of API endpoints. "
        f"Your task is to suggest {count} highly complete, general-purpose widget ideas that could be built using these endpoints. "
        "Each widget should use as much of the available data as possible, maximizing completeness and usability. "
        "Each widget must be standalone: do not require any unimported datasources or endpoints, and use only what is fetched from the provided endpoints. "
        "The widget_description should be comprehensive, containing all relevant details about the widget's purpose and functionality. "
        "For each idea, output a JSON object with the following fields:\n"
        "- widget_title: (string) a short, descriptive title for the widget\n"
        "- widget_description: (string) a comprehensive, detailed description of what the widget does and how it is useful\n"
        "- endpoint: (string) the API endpoint(s) used\n"
        "- data_combination: (string) a highly detailed, step-by-step explanation of exactly what data fields (including all relevant nested JSON fields) to fetch and combine from which endpoint(s), with clear instructions for a frontend developer. The data_combination must fetch all relevant data from the specified endpoint(s) as appropriate, and sort or organize the data so that the widget is meaningful and useful for the end user. Be explicit about how to process, filter, and sort the data for the widget's purpose.\n"
        "- react_fetch_example: (string) a copy-paste ready React fetch code snippet (no imports, just the fetch logic and data extraction) that demonstrates exactly how to fetch and combine the data for this widget, with comments explaining each step and referencing all relevant nested fields. If the schema or sample is incomplete, make reasonable assumptions and still provide a complete, detailed example.\n"
        "Guardrails:\n"
        f"- Output exactly {count} ideas as a JSON array of objects.\n"
        "- All fields must be strings. If you are unsure, use an empty string.\n"
        "- Do NOT include any explanation, commentary, or markdown—output ONLY the JSON array.\n"
        f"- Validate your output: ensure the result is a valid JSON array of {count} objects, each with the required fields and correct types.\n"
        f"OpenAPI 3.1.1 specification:\n{openapi_str}\n"
        "Respond ONLY with the JSON array."
    )

    llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-4.1", temperature=0.3, max_tokens=20000)
    result = llm.invoke([HumanMessage(content=prompt)])
    if hasattr(result, "content"):
        result = result.content

    # Try to parse the LLM's response as JSON
    try:
        ideas = json.loads(result)
        # Validate structure: ensure each idea has required fields and there are exactly count
        if not isinstance(ideas, list) or len(ideas) != count:
            return [{"error": f"LLM did not return exactly {count} widget ideas", "raw_response": result}]
        validated = []
        for idea in ideas:
            validated.append({
                "widget_title": idea.get("widget_title", ""),
                "widget_description": idea.get("widget_description", ""),
                "endpoint": idea.get("endpoint", ""),
                "data_combination": idea.get("data_combination", "")
            })
        return validated
    except Exception as e:
        # Return error in result
        return [{"error": f"Failed to parse LLM response as JSON: {str(e)}", "raw_response": result}]

# Celery task to generate widget ideas from datasource schemas (end-to-end)
@celery_app.task(name="app.tasks.langchain_task.suggest_widgets_from_datasource_schemas")
def suggest_widgets_from_datasource_schemas() -> dict:
    """
    End-to-end Celery task: triggers OpenAPI spec generation, polls for result, then generates widget ideas.
    Returns a dict with schema_description and response (list of widget ideas or error).
    """
    import time
    import requests

    # Step 1: Trigger OpenAPI spec generation
    try:
        resp = requests.post("http://localhost:3001/api/datasource-schemas", timeout=10)
        if resp.status_code != 200:
            return {
                "schema_description": {"error": f"Failed to start OpenAPI spec generation: status {resp.status_code}"},
                "response": None
            }
        data = resp.json()
        task_id = data.get("task_id")
        if not task_id:
            return {
                "schema_description": {"error": "No task_id returned from /api/datasource-schemas"},
                "response": None
            }
    except Exception as e:
        return {
            "schema_description": {"error": f"Exception during OpenAPI spec generation: {str(e)}"},
            "response": None
        }

    # Step 2: Poll for result
    result_url = f"http://localhost:3001/api/datasource-schemas/result/{task_id}"
    max_attempts = 1200
    delay = 3  # seconds, for up to 1 hour total
    openapi_dict = None
    for _ in range(max_attempts):
        try:
            result_resp = requests.get(result_url, timeout=10)
            if result_resp.status_code == 200:
                result_data = result_resp.json()
                if result_data.get("status") == "SUCCESS" and result_data.get("schema"):
                    openapi_dict = result_data["schema"]
                    break
            time.sleep(delay)
        except Exception:
            time.sleep(delay)
    else:
        return {
            "schema_description": {"error": "Timeout waiting for OpenAPI spec generation (1 hour)"},
            "response": None
        }

    # Step 3: Generate widget ideas
    from app.tasks.langchain_task import suggest_widgets_from_openapi
    widget_ideas = suggest_widgets_from_openapi(openapi_dict)
    return {
        "schema_description": openapi_dict,
        "response": widget_ideas
    }

# main celery task for widget suggestions (legacy, to be removed)
@celery_app.task(name="app.tasks.langchain_task.suggest_widgets_from_schemas")
def suggest_widgets_from_schemas() -> list:
    """
    Fetch schemas from all datasources, feed to LLM, and suggest N widget ideas.
    Returns a list of dicts with widget_title, widget_description, endpoint, and data_combination.
    """
    endpoints = settings.DATASOURCES_API_ENDPOINTS
    schemas = {}
    count = settings.WIDGET_GENERATION_COUNT

    # Fetch schemas synchronously
    for url in endpoints:
        try:
            # Try OpenAPI/Swagger first
            for schema_path in ["/openapi.json", "/swagger.json"]:
                schema_url = url.rstrip("/") + schema_path
                resp = requests.get(schema_url, timeout=10)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                    schemas[url] = {"type": "openapi/swagger", "schema": resp.json()}
                    break
            else:
                # Fallback: try to infer schema from sample JSON
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                    try:
                        data = resp.json()
                        if isinstance(data, list) and data:
                            sample = data[0]
                        elif isinstance(data, dict):
                            sample = data
                        else:
                            sample = data
                        schemas[url] = {"type": "inferred", "sample": sample}
                    except Exception as e:
                        schemas[url] = {"error": f"Failed to parse JSON: {str(e)}"}
                else:
                    schemas[url] = {"error": f"No schema found and endpoint did not return JSON (status {resp.status_code})"}
        except Exception as e:
            schemas[url] = {"error": str(e)}

    # Build prompt for LLM
    schemas_str = json.dumps(schemas, indent=2)
    prompt = (
        "You are an expert dashboard widget designer and frontend engineer. "
        "You are given a list of datasource endpoints, each with a JSON schema and a sample data entry. "
        f"Your task is to suggest {count} highly complete, general-purpose widget ideas that could be built using these datasources. "
        "Each widget should use as much of the available data as possible, maximizing completeness and usability. "
        "Each widget must be standalone: do not require any unimported datasources or endpoints, and use only what is fetched from the provided endpoints. "
        "The widget_description should be comprehensive, containing all relevant details about the widget's purpose and functionality. "
        "Use the schema to understand the general structure and possible data, and use the sample entry ONLY as a reference for output formatting—not for restricting your ideas to the sample's values. "
        "For each idea, output a JSON object with the following fields:\n"
        "- widget_title: (string) a short, descriptive title for the widget\n"
        "- widget_description: (string) a comprehensive, detailed description of what the widget does and how it is useful\n"
        "- endpoint: (string) the datasource endpoint(s) used\n"
        "- data_combination: (string) a highly detailed, step-by-step explanation of exactly what data fields (including all relevant nested JSON fields) to fetch and combine from which endpoint(s), with clear instructions for a frontend developer. The data_combination must fetch all relevant data from the specified endpoint(s) as appropriate, and sort or organize the data so that the widget is meaningful and useful for the end user. Be explicit about how to process, filter, and sort the data for the widget's purpose.\n"
        "- react_fetch_example: (string) a copy-paste ready React fetch code snippet (no imports, just the fetch logic and data extraction) that demonstrates exactly how to fetch and combine the data for this widget, with comments explaining each step and referencing all relevant nested fields. If the schema or sample is incomplete, make reasonable assumptions and still provide a complete, detailed example.\n"
        "Guardrails:\n"
        f"- Output exactly {count} ideas as a JSON array of objects.\n"
        "- All fields must be strings. If you are unsure, use an empty string.\n"
        "- Do NOT use values from the sample entry as the only possible values; your suggestions should be general and applicable to any data conforming to the schema.\n"
        "- Do NOT include any explanation, commentary, or markdown—output ONLY the JSON array.\n"
        f"- Validate your output: ensure the result is a valid JSON array of {count} objects, each with the required fields and correct types.\n"
        f"Datasource schemas and sample entries:\n{schemas_str}\n"
        "Respond ONLY with the JSON array."
    )

    llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-4.1", temperature=0.3, max_tokens=20000)
    result = llm.invoke([HumanMessage(content=prompt)])
    if hasattr(result, "content"):
        result = result.content

    # Try to parse the LLM's response as JSON
    try:
        ideas = json.loads(result)
        # Validate structure: ensure each idea has required fields and there are exactly count
        if not isinstance(ideas, list) or len(ideas) != count:
            return [{"error": f"LLM did not return exactly {count} widget ideas", "raw_response": result}]
        validated = []
        for idea in ideas:
            validated.append({
                "widget_title": idea.get("widget_title", ""),
                "widget_description": idea.get("widget_description", ""),
                "endpoint": idea.get("endpoint", ""),
                "data_combination": idea.get("data_combination", "")
            })
        return validated
    except Exception as e:
        # Return error in result
        return [{"error": f"Failed to parse LLM response as JSON: {str(e)}", "raw_response": result}]

# Celery task to generate React widget code for each widget idea
@celery_app.task(name="app.tasks.langchain_task.generate_widgets_from_ideas")
def generate_widgets_from_ideas(openapi_spec: dict | None = None) -> list:
    """
    Generate React widget code for each widget idea using the widget-generation-prompt.tmpl.
    Returns a list of dicts: {widget_title, widget_description, code}
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    # 1. Get widget ideas and OpenAPI spec
    import os
    if openapi_spec:
        widget_ideas = suggest_widgets_from_openapi(openapi_spec)
    else:
        schema_path = "openapi-schema.json"
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                openapi_spec = json.load(f)
            widget_ideas = suggest_widgets_from_openapi(openapi_spec)
        else:
            result = suggest_widgets_from_datasource_schemas()
            openapi_spec = result.get("schema_description")
            widget_ideas = result.get("response")

    if not widget_ideas or not openapi_spec:
        return []

    # 2. Load prompt template
    tmpl_path = os.path.join(os.path.dirname(__file__), "../prompts/widget-generation-prompt.tmpl")
    with open(tmpl_path, "r") as f:
        prompt_template = f.read()

    # 3. For each widget idea, generate code
    llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-4.1", temperature=0.2, max_tokens=20000)
    import concurrent.futures
    import re
    import logging

    def generate_code(idea):
        description = idea.get("widget_description", "")
        endpoint = idea.get("endpoint", "")
        # Find the matching headers for the endpoint, if any
        matched_headers = None
        for url, headers in getattr(settings, "DATASOURCE_AUTH_HEADERS", {}).items():
            if endpoint.startswith(url):
                matched_headers = headers
                break
        openapi_schema_str = json.dumps(openapi_spec, indent=2)
        prompt = (
            prompt_template
            .replace('""" + description + """', description)
            .replace("OPENAPI_SCHEMA_PLACEHOLDER", openapi_schema_str)
        )
        result = llm.invoke([HumanMessage(content=prompt)])
        code = result.content if hasattr(result, "content") else str(result)
        # No header injection or replacement; rely on prompt to enforce correct header usage
        logging.warning(
            f"[WidgetGen] Widget Title: {idea.get('widget_title', '')}\n"
            f"Description: {description}\n"
            f"Code (full):\n{code}\n"
            f"Code length: {len(code)}"
        )
        print("\n===== FINAL WIDGET CODE WITH INJECTED HEADERS =====\n")
        print(code)
        print("\n===== END FINAL WIDGET CODE =====\n")
        return {
            "widget_title": idea.get("widget_title", ""),
            "widget_description": description,
            "code": code
        }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(generate_code, widget_ideas))

    return results
