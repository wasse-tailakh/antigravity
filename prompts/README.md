# Prompts Directory

This directory stores the text templates used to generate prompts for various agents in the Orchestrator layer. 

By separating prompts from the python code, we achieve:
1. **Cleaner Code:** The Python agents remain focused strictly on control flow and API mechanics.
2. **Easier Tuning:** Prompt engineers or LLMs can modify the system prompts without risking syntax errors or altering core engine logic.
3. **Caching / Consistency:** Reusable and trackable prompts make hash-based caching (like `ResponseCache`) reliable.

## Current Prompts

- **`planner.txt`**: Used by the `Planner` agent (default: Gemini) to ingest the user request and emit a structured JSON list of task descriptions and agent assignments.
- **`router.txt`**: Used by the `RouterAgent` (default: Gemini) specifically to decide if a task belongs to `claude` (for high-complexity/architecture work) or `gemini` (for rapid/general work).
- **`reviewer.txt`**: Used by the `Reviewer` (currently deprecated in favor of a fast deterministic reviewer, but kept for potential future heuristic validation loops).
