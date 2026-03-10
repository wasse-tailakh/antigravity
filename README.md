# Antigravity

Antigravity is a cost-optimized multi-agent orchestration system for practical AI workflows.

It combines:
- specialized agents
- secure tools
- smart retries and review loops
- working memory and task memory
- cost guardrails and caching
- real workflows for development, debugging, research, and safe automation

## Core Features

- Multi-agent architecture
- Gemini Flash as default low-cost provider
- Claude as escalation provider for complex reasoning/code tasks
- Tool registry with secure file/shell/git operations
- Smart retries, backoff, and review loop
- Working memory + task memory (SQLite-backed)
- Practical workflows for real tasks

## Project Structure

- `agents/` — model-specific agents and routing
- `orchestrator/` — planner, executor, retries, reviewer
- `tools/` / `skills/` — secure system capabilities
- `memory/` — short-term and task memory
- `policies/` — cost, safety, and retry policies
- `workflows/` — real task workflows
- `tests/` — smoke and workflow tests
- `docs/` — architecture and phase summaries
- `demos/` — runnable examples

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in the required API keys in `.env`.

## Run Tests

```bash
python tests/test_executor.py
pytest
```

## Run Demo

```bash
python demos/demo_working_memory.py
```

## Planned Entry Point

A unified CLI will allow running workflows like:

```bash
python main.py run debug --target file.py
python main.py run research --topic "Architecture"
python main.py run continuation --task-id last
```

## Status

Current status:

* Core architecture: complete
* Smart retries/review loop: complete
* Working memory/task memory: complete
* Real workflows: complete
* CLI layer: In Progress
