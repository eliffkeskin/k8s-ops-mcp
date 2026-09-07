# host.py - mini MCP host: Ollama (model) + k8s-ops (MCP server)
# Run: source venv/bin/activate && python host.py
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

MODEL = os.environ.get("HOST_MODEL", "qwen2.5:7b")
llm = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

SYSTEM = (
    "You are a Kubernetes operations assistant. You have read-only diagnostic "
    "tools for the user's cluster. When the user asks about cluster state or "
    "problems, call the relevant tools first, then explain findings clearly "
    "and concisely. Answer in the user's language."
)

MAX_TOOL_ROUNDS = 5


def to_openai_tools(mcp_tools):
    out = []
    for t in mcp_tools:
        out.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema or {"type": "object", "properties": {}},
            },
        })
    return out


def tool_result_text(result):
    parts = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) or "(empty result)"


async def chat_loop(session: ClientSession):
    listed = await session.list_tools()
    tools = to_openai_tools(listed.tools)
    print(f"Connected tools: {', '.join(t['function']['name'] for t in tools)}")
    print(f"Model: {MODEL}  (to change: HOST_MODEL=... python host.py)")
    print("Type a question, Ctrl+C to exit.\n")

    messages = [{"role": "system", "content": SYSTEM}]

    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return
        if not user:
            continue
        messages.append({"role": "user", "content": user})

        for _ in range(MAX_TOOL_ROUNDS):
            resp = llm.chat.completions.create(
                model=MODEL, messages=messages, tools=tools)
            msg = resp.choices[0].message

            if not msg.tool_calls:
                print(f"\nassistant> {msg.content}\n")
                messages.append({"role": "assistant", "content": msg.content or ""})
                break

            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"  [tool call] {name}({args})")
                try:
                    result = await session.call_tool(name, arguments=args)
                    text = tool_result_text(result)
                except Exception as e:
                    text = f"tool error: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": text,
                })
        else:
            print("\nassistant> (tool call round limit reached - simplify the question)\n")


async def main():
    server = StdioServerParameters(
        command=sys.executable,          # same venv's Python - no uv needed
        args=["server.py"],
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await chat_loop(session)


if __name__ == "__main__":
    asyncio.run(main())