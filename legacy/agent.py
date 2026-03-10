"""
Claude Agent — A conversational AI agent powered by the Anthropic Claude API.

Features:
  • Multi-turn conversation with memory
  • Tool use (function calling) with automatic tool-result loop
  • Streaming responses for real-time terminal output
  • Built-in tools: calculator, current time, web search stub
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding — must run before any Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import anthropic
from dotenv import load_dotenv

# ── Configuration ────────────────────────────────────────────────────────────

# Load .env from the same directory as this script
load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use the available tools when they would help answer the user's question. "
    "Be concise, accurate, and friendly."
)

# ── Tool definitions (JSON-schema for Claude) ───────────────────────────────

TOOLS = [
    {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression. Supports standard Python math "
            "operators and functions from the math module (sin, cos, sqrt, pi, e, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '2 ** 10' or 'math.sqrt(144)'.",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_current_time",
        "description": "Return the current date and time in UTC and the user's local timezone.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for information. Returns a summary of the top results. "
            "(Stub implementation — replace with a real search API for production use.)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
            },
            "required": ["query"],
        },
    },
]

# ── Tool implementations ────────────────────────────────────────────────────


def tool_calculator(expression: str) -> str:
    """Safely evaluate a math expression."""
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "int": int, "float": float})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return json.dumps({"result": result})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def tool_get_current_time() -> str:
    """Return current UTC and local time."""
    utc_now = datetime.now(timezone.utc)
    local_now = datetime.now()
    return json.dumps(
        {
            "utc": utc_now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "local": local_now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


def tool_web_search(query: str) -> str:
    """Stub web search — replace with a real API (e.g. Brave, Tavily, SerpAPI)."""
    return json.dumps(
        {
            "note": "This is a stub. Integrate a real search API for production.",
            "query": query,
            "results": [],
        }
    )


TOOL_DISPATCH = {
    "calculator": lambda inp: tool_calculator(inp["expression"]),
    "get_current_time": lambda inp: tool_get_current_time(),
    "web_search": lambda inp: tool_web_search(inp["query"]),
}

# ── Agent ────────────────────────────────────────────────────────────────────


class ClaudeAgent:
    """A multi-turn conversational agent backed by Claude with tool-use support."""

    def __init__(self, model: str = MODEL, system: str = SYSTEM_PROMPT):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\n✖  ANTHROPIC_API_KEY not set.")
            print("   Create a .env file with:  ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system = system
        self.messages: list[dict] = []

    # ── Core turn ────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Send a user message and return the final assistant text.

        Automatically handles the tool-use loop: if Claude requests tool calls,
        the agent executes them and feeds the results back until Claude produces
        a final text response.
        """
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self.system,
                tools=TOOLS,
                messages=self.messages,
            )

            # Collect assistant content blocks
            assistant_content = response.content
            self.messages.append({"role": "assistant", "content": assistant_content})

            # If the model didn't request any tool use, we're done
            if response.stop_reason != "tool_use":
                return self._extract_text(assistant_content)

            # Process every tool-use block and build tool results
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    print(f"  ⚙  Tool call: {tool_name}({json.dumps(tool_input)})")

                    handler = TOOL_DISPATCH.get(tool_name)
                    if handler:
                        result = handler(tool_input)
                    else:
                        result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            # Feed tool results back to the model
            self.messages.append({"role": "user", "content": tool_results})

    # ── Streaming turn ───────────────────────────────────────────────────

    def chat_stream(self, user_message: str) -> str:
        """Like chat(), but streams the text response token-by-token.

        Still handles the full tool-use loop internally.
        """
        self.messages.append({"role": "user", "content": user_message})

        while True:
            collected_content: list = []
            current_text = ""
            tool_uses: list[dict] = []

            with self.client.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self.system,
                tools=TOOLS,
                messages=self.messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            current_text = ""
                        elif event.content_block.type == "tool_use":
                            tool_uses.append(
                                {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input_json": "",
                                }
                            )
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            print(event.delta.text, end="", flush=True)
                            current_text += event.delta.text
                        elif event.delta.type == "input_json_delta":
                            if tool_uses:
                                tool_uses[-1]["input_json"] += event.delta.partial_json

                # Gather the final message from the stream
                final_message = stream.get_final_message()
                collected_content = final_message.content

            self.messages.append({"role": "assistant", "content": collected_content})

            if final_message.stop_reason != "tool_use":
                print()  # newline after streamed text
                return current_text

            # Process tool calls
            tool_results = []
            for tu in tool_uses:
                tool_input = json.loads(tu["input_json"]) if tu["input_json"] else {}
                print(f"\n  ⚙  Tool call: {tu['name']}({json.dumps(tool_input)})")

                handler = TOOL_DISPATCH.get(tu["name"])
                if handler:
                    result = handler(tool_input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tu['name']}"})

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": result,
                    }
                )

            self.messages.append({"role": "user", "content": tool_results})

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_text(content_blocks) -> str:
        """Pull plain text from a list of content blocks."""
        parts = [b.text for b in content_blocks if hasattr(b, "text")]
        return "\n".join(parts)

    def reset(self):
        """Clear conversation history."""
        self.messages.clear()


# ── Interactive REPL ─────────────────────────────────────────────────────────


def main():
    agent = ClaudeAgent()

    print("╔══════════════════════════════════════════════════╗")
    print("║           🤖  Claude Agent  (ctrl+c to exit)    ║")
    print("║  Built-in tools: calculator, time, web_search   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    while True:
        try:
            user_input = input("\033[1;36mYou › \033[0m").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "exit", "quit"):
            print("\nGoodbye! 👋")
            break

        if user_input.lower() in ("/reset", "/clear"):
            agent.reset()
            print("  ↻  Conversation cleared.\n")
            continue

        print(f"\033[1;33mClaude › \033[0m", end="", flush=True)
        agent.chat_stream(user_input)
        print()


if __name__ == "__main__":
    main()
