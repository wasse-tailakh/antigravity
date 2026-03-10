from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, workflows, runs, memory

app = FastAPI(
    title="Antigravity API",
    description="Lightweight API layer for the Antigravity multi-agent orchestrator",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(runs.router, prefix="/runs", tags=["Runs"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Antigravity API. See /docs for documentation."}
