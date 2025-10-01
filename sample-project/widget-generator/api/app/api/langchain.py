from fastapi import APIRouter
from pydantic import BaseModel
from app.tasks.langchain_task import run_langchain
from celery.result import AsyncResult
from app.core.celery_app import celery_app

router = APIRouter()

class LangChainAddRequest(BaseModel):
    num1: float
    num2: float

class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None

@router.post("/langchain/add", response_model=TaskResultResponse)
def queue_langchain_add_task(request: LangChainAddRequest):
    task = run_langchain.apply_async(args=[request.num1, request.num2])
    return TaskResultResponse(task_id=task.id, status=task.status, result=None)

@router.get("/langchain/result/{task_id}", response_model=TaskResultResponse)
def get_langchain_result(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    result = task_result.result if task_result.successful() else None
    return TaskResultResponse(
        task_id=task_id,
        status=task_result.status,
        result=result
    )
