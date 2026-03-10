"""
Dependency injection module for the FastAPI application.
Provides a singleton Executor instance to avoid re-initializing
agents, tools, and database connections on every API call.
"""
from functools import lru_cache
from orchestrator.executor import Executor

@lru_cache(maxsize=1)
def get_executor() -> Executor:
    """Returns a singleton Executor instance."""
    return Executor()
