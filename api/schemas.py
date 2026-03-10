from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class APIError(BaseModel):
    code: str = Field(..., description="Error code (e.g., rate_limit, policy_violation, internal_error)")
    details: str = Field(..., description="Human readable error details")
    retryable: bool = Field(default=False, description="Whether the client should retry the request")

class APIResponse(BaseModel, Generic[T]):
    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(default="", description="Optional message about the response")
    data: Optional[T] = Field(default=None, description="The actual payload if successful")
    error: Optional[APIError] = Field(default=None, description="Error details if success is false")

class RunStatusResponse(BaseModel):
    task_id: str
    workflow_name: str
    status: str = Field(..., description="Status: 'pending', 'running', 'completed', 'failed'")
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    llm_calls_approx: int = 0
    tool_calls: int = 0
    retries: int = 0
    escalated_to_claude: bool = False
    final_output: Optional[Any] = None
    steps: List["StepResultSchema"] = []

class RunWorkflowRequest(BaseModel):
    workflow_name: str
    target: Optional[str] = None
    goal: Optional[str] = None
    error: Optional[str] = None
    task_id: Optional[str] = None

class StepResultSchema(BaseModel):
    step_id: str
    action: str
    status: str
    output: Any
    timestamp: datetime
    provider_used: Optional[str] = None
    attempts: int = 1

class RunWorkflowResponse(BaseModel):
    workflow_name: str
    status: str
    llm_calls_approx: int
    tool_calls: int
    retries: int
    escalated_to_claude: bool
    final_output: Any
    steps: List[StepResultSchema] = []

class TaskSummarySchema(BaseModel):
    task_id: str
    user_prompt: str
    summary: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class RunJournalSchema(BaseModel):
    id: int
    task_id: str
    step_id: str
    action: str
    provider: str
    status: str
    output: str
    timestamp: datetime
