import time
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from api.routes import health, workflows, runs, memory
from api.schemas import APIResponse, APIError

# Setup simple logger for API
logger = logging.getLogger("api_access")
logger.setLevel(logging.INFO)
# Prevent duplicate logs if run from uvicorn
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] [%(name)s] request_id=%(request_id)s %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

app = FastAPI(
    title="Antigravity API",
    description="Lightweight API layer for the Antigravity multi-agent orchestrator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    # Quick hack to inject request_id into logs contextually for this thread
    # Real apps use contextvars, but simple adapter is fine for now
    logger = logging.LoggerAdapter(logging.getLogger("api_access"), {"request_id": request_id})
    
    start_time = time.time()
    logger.info(f"Started {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(f"Completed {response.status_code} in {process_time:.3f}s")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.LoggerAdapter(logging.getLogger("api_access"), {"request_id": request.headers.get("X-Request-ID", "unknown")})
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Internal Server Error",
            error=APIError(code="internal_error", details=str(exc), retryable=False)
        ).model_dump()
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(runs.router, prefix="/runs", tags=["Runs"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Antigravity API. See /docs for documentation."}
