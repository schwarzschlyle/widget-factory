from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import settings
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.tasks.langchain_task import generate_openapi_spec_from_schemas

router = APIRouter()

@router.post("/datasource-schemas")
def queue_openapi_spec_task():
    """
    Queue a Celery task to generate an OpenAPI 3.1.1 specification from discovered schemas.
    """
    task = generate_openapi_spec_from_schemas.apply_async()
    return {"task_id": task.id, "status": task.status, "type": None, "schema": None}

@router.get("/datasource-schemas/result/{task_id}")
def get_openapi_spec_result(task_id: str):
    """
    Get the result of the OpenAPI 3.1.1 spec generation Celery task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    result = task_result.result if task_result.successful() else None

    if isinstance(result, dict) and "type" in result and "schema" in result:
        return {
            "task_id": task_id,
            "status": task_result.status,
            "type": result["type"],
            "schema": result["schema"]
        }
    else:
        return {
            "task_id": task_id,
            "status": task_result.status,
            "type": None,
            "schema": None
        }
