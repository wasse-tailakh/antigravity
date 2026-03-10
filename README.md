# Claude Agent

A conversational AI agent powered by the **Anthropic Claude API** with tool-use support, multi-turn memory, and streaming output.

## Features

- 🔄 **Multi-turn conversations** — remembers context across messages
- 🛠️ **Tool use (function calling)** — calculator, current time, web search stub
- ⚡ **Streaming responses** — real-time token-by-token output
- 🎨 **Colored terminal UI** — friendly interactive REPL

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# Edit .env and paste your Anthropic API key

# 3. Run the agent
python agent.py
```

## Usage

Once running, just type your messages:

```
You › What is 2^32?
Claude › ⚙  Tool call: calculator({"expression": "2 ** 32"})
         2^32 = 4,294,967,296

You › What time is it?
Claude › ⚙  Tool call: get_current_time({})
         It's currently 2025-03-10 03:25:00 UTC.

You › /reset       ← clears conversation history
You › /quit        ← exits the agent
```

## Adding Custom Tools

1. Define the tool schema in `TOOLS` (JSON Schema format)
2. Implement the handler function
3. Register it in `TOOL_DISPATCH`

## License

MIT
