from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.tasks.langchain_task import suggest_widgets_from_schemas
from celery.result import AsyncResult
from app.core.celery_app import celery_app
import requests

router = APIRouter()

class WidgetSuggestionResponse(BaseModel):
    widget_title: str = Field(..., description="Short title for the widget")
    widget_description: str = Field(..., description="Brief description of the widget")
    endpoint: str = Field(..., description="Datasource endpoint(s) used")
    data_combination: str = Field(..., description="Specific data fields to combine from which endpoint(s)")

class WidgetIdeasRequest(BaseModel):
    openapi_spec: str | None = Field(
        None,
        description="Optional OpenAPI 3.1.1 specification as a JSON string. If provided, this will be used directly."
    )

class TaskWidgetSuggestionResultResponse(BaseModel):
    task_id: str
    status: str
    schema_description: dict | None = None
    response: list[WidgetSuggestionResponse] | None = None
    datasources: list[str] | None = None

def fetch_schema_description():
    try:
        resp = requests.get("http://localhost:3001/api/datasource-schemas", timeout=10000)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Failed to fetch schema: status {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/widget-ideas", response_model=TaskWidgetSuggestionResultResponse)
def queue_widget_suggestion_task(request: WidgetIdeasRequest):
    """
    Queue a Celery task to suggest 3 widget ideas.
    If openapi_spec is provided, use it directly and skip the datasource-schemas Celery task.
    Otherwise, fetch the OpenAPI spec from /api/datasource-schemas as before.
    This endpoint is non-blocking and returns a task_id immediately.
    """
    from app.tasks.langchain_task import suggest_widgets_from_datasource_schemas, suggest_widgets_from_openapi
    from app.core.config import settings
    import json

    if request.openapi_spec:
        # Use provided OpenAPI spec directly
        try:
            openapi_dict = json.loads(request.openapi_spec)
        except Exception as e:
            return TaskWidgetSuggestionResultResponse(
                task_id="",
                status="FAILED",
                schema_description={"error": f"Invalid OpenAPI JSON: {str(e)}"},
                response=None,
                datasources=getattr(settings, "DATASOURCES_API_ENDPOINTS", None)
            )
        celery_task = suggest_widgets_from_openapi.apply_async(args=[openapi_dict])
        return TaskWidgetSuggestionResultResponse(
            task_id=celery_task.id,
            status=celery_task.status,
            schema_description=openapi_dict,
            response=None,
            datasources=getattr(settings, "DATASOURCES_API_ENDPOINTS", None)
        )
    else:
        # Fallback to end-to-end Celery task
        task = suggest_widgets_from_datasource_schemas.apply_async()
        return TaskWidgetSuggestionResultResponse(
            task_id=task.id,
            status=task.status,
            schema_description=None,
            response=None,
            datasources=getattr(settings, "DATASOURCES_API_ENDPOINTS", None)
        )

@router.get("/widget-ideas/result/{task_id}", response_model=TaskWidgetSuggestionResultResponse)
def get_widget_suggestion_result(task_id: str):
    """
    Get the result of the widget suggestion Celery task.
    """
    from app.core.config import settings
    task_result = AsyncResult(task_id, app=celery_app)
    result = task_result.result if task_result.successful() else None

    schema_description = None
    widget_results = None

    if isinstance(result, dict):
        schema_description = result.get("schema_description")
        widget_results = result.get("response")
        # Convert widget_results to WidgetSuggestionResponse if possible
        if isinstance(widget_results, list):
            try:
                widget_results = [WidgetSuggestionResponse(**item) if isinstance(item, dict) and "widget_title" in item else item for item in widget_results]
            except Exception:
                pass

    return TaskWidgetSuggestionResultResponse(
        task_id=task_id,
        status=task_result.status,
        schema_description=schema_description,
        response=widget_results,
        datasources=getattr(settings, "DATASOURCES_API_ENDPOINTS", None)
    )

# NEW ENDPOINT: /api/generate-widgets
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
import os

class GenerateWidgetsRequest(BaseModel):
    openapi_spec: str | None = Field(
        None,
        description="Optional OpenAPI 3.1.1 specification as a JSON string. If provided, this will be used directly."
    )

class GeneratedWidgetCode(BaseModel):
    widget_title: str
    widget_description: str
    code: str

@router.post("/generate-widgets")
def generate_widgets(request: GenerateWidgetsRequest):
    """
    Queue a Celery task to generate React widget code for each widget idea.
    Returns a task_id immediately.
    """
    import json
    from app.tasks.langchain_task import generate_widgets_from_ideas

    if request.openapi_spec:
        try:
            openapi_dict = json.loads(request.openapi_spec)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid OpenAPI JSON: {str(e)}"}
            )
        celery_task = generate_widgets_from_ideas.apply_async(args=[openapi_dict])
    else:
        celery_task = generate_widgets_from_ideas.apply_async(args=[None])

    return {"task_id": celery_task.id, "status": celery_task.status}

@router.get("/generate-widgets/result/{task_id}")
def get_generate_widgets_result(task_id: str):
    """
    Get the result of the widget code generation Celery task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    result = task_result.result if task_result.successful() else None
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": result
    }
