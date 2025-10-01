from fastapi import FastAPI
from app.api.langchain import router as langchain_router
from app.api.datasource import router as datasource_router
from app.api.generate_widget_ideas import router as widget_ideas_router

app = FastAPI(
    title="AI FastAPI Boilerplate with Celery & Redis",
    description="Async AI backend with Celery task queue and Redis broker.",
    version="0.1.0"
)

app.include_router(langchain_router, prefix="/api")
app.include_router(datasource_router, prefix="/api")
app.include_router(widget_ideas_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
