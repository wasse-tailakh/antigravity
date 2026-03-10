# Cleanup Sprint Summary

## Sprint 1: Security & Repository Hygiene
- **Deleted** `ettings.local.json` (leaked secrets), `dummy_refactor_test.py`, `math_test.txt`, `test_demo.txt`, `test_output.txt`, `system.log`
- **Hardened** `.gitignore`: added `*.db`, `.vscode/`, `.claude/`, `stabilization_notes.md`, and test artifacts
- **Moved** phase summaries (`PHASE6_5`, `PHASE7A`, `PHASE7A_5`) → `docs/phases/`
- **Moved** `RUNTIME_VALIDATION.md` → `docs/`
- **Moved** legacy `agent.py` (standalone Claude REPL) → `legacy/`

## Sprint 2: Architecture Fixes
- **Singleton Executor**: Created `api/dependencies.py` with `@lru_cache` singleton pattern
- **Lazy-loaded Agents**: `RouterAgent` now instantiates Claude/OpenAI only when first needed via `get_agent()`
- **Pydantic V2**: Updated `config/settings.py` from deprecated `class Config` to `ConfigDict`
- **datetime fix**: Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` in `api/services.py`

## Sprint 3: Code Quality & Security Hardening
- **Planner**: Fixed misleading comment ("Claude" → "Gemini Flash"), removed duplicate `json`/`re` imports
- **Reviewer**: Replaced naive `"error" in output` substring matching with structured prefix-pattern detection
- **FileSkill**: Hardened path traversal protection with `os.path.realpath()` to resolve symlinks before validation
- **ShellSkill**: Expanded blocklist from 5 → 30+ patterns, added metacharacter injection detection (`&&`, `||`, `;`, backticks, `$(`, `|`), enforced MAX_TIMEOUT=120s cap
- **requirements.txt**: Fixed `google-generativeai` → `google-genai`, added `httpx`/`pytest`, removed unused `selenium`/`playwright`

## Test Results
```
10 passed in 14.12s (0 warnings)
```
