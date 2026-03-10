from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

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
