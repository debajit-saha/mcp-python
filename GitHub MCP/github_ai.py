
import asyncio
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

# Microsoft Foundry configuration

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT"
)

AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY"
)

AZURE_OPENAI_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT"
)

if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT is missing")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("AZURE_OPENAI_API_KEY is missing")

if not AZURE_OPENAI_DEPLOYMENT:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT is missing")


# OpenAI-compatible client connecting to Microsoft Foundry

llm = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)

MODEL = AZURE_OPENAI_DEPLOYMENT
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is missing")

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


# --------------------------------------------------
# Convert MCP tools to OpenAI function tools
# --------------------------------------------------

def convert_mcp_tools(mcp_tools):

    openai_tools = []

    for tool in mcp_tools.tools:

        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
            }
        })

    return openai_tools


# --------------------------------------------------
# Convert MCP result to text
# --------------------------------------------------

def convert_mcp_result(result):

    output = []

    for item in result.content:

        if hasattr(item, "text"):
            output.append(item.text)

        else:
            output.append(str(item))

    if result.isError:
        return "MCP tool execution failed:\n" + "\n".join(output)

    return "\n".join(output)


# --------------------------------------------------
# Call Microsoft Foundry LLM
# Send MCP result back to Microsoft Foundry
# --------------------------------------------------

def call_llm(messages, tools):

    response = llm.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    return response.choices[0].message


# --------------------------------------------------
# MCP + LLM Agent
# --------------------------------------------------

async def github_agent(session, openai_tools, query):

    messages = [
        {
            "role": "system",
            "content": """
You are a GitHub AI assistant.

Rules:
1. Use GitHub MCP tools whenever repository information is needed.
2. Never invent repository names, issues, pull requests, or code.
3. Use actual GitHub tool results to answer questions.
4. If information is unavailable, clearly say so.
5. Explain results in simple language.
6. Do not perform write operations unless explicitly authorized.
"""
        },
        {
            "role": "user",
            "content": query
        }
    ]

    # Agent loop
    while True:

        assistant = call_llm(messages, openai_tools)

        # Add assistant response to conversation
        messages.append(
            assistant.model_dump(exclude_none=True)
        )

        # If no tool calls, LLM has finished
        if not assistant.tool_calls:

            return assistant.content or "No response from AI."

        # Execute MCP tools requested by LLM
        for tool_call in assistant.tool_calls:

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            print(f"\n[MCP Tool] {tool_name}")
            print(f"[Arguments] {arguments}")

            try:

                result = await session.call_tool(
                    tool_name,
                    arguments
                )

                tool_output = convert_mcp_result(result)

            except Exception as ex:

                tool_output = f"Tool execution error: {ex}"

            # Send MCP result back to OpenAI
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_output
            })


# --------------------------------------------------
# Main application
# --------------------------------------------------

async def main():

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-MCP-Readonly": "true"
    }

    print("Connecting to GitHub Remote MCP Server...")

    async with streamablehttp_client(
        GITHUB_MCP_URL,
        headers=headers
    ) as (read, write, get_session_id):

        async with ClientSession(read, write) as session:

            # Initialize MCP connection
            await session.initialize()

            # Discover GitHub MCP tools
            mcp_tools = await session.list_tools()

            openai_tools = convert_mcp_tools(mcp_tools)

            print("\nGitHub MCP Connected!")
            print(f"Available MCP tools: {len(openai_tools)}")

            # Display tool names
            for tool in mcp_tools.tools:
                print(f" - {tool.name}")

            print("\nGitHub AI Assistant Started")
            print("Type 'exit' to quit.")

            # Interactive conversation
            while True:

                query = input("\nYou: ").strip()

                if query.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break

                if not query:
                    continue

                try:

                    answer = await github_agent(
                        session,
                        openai_tools,
                        query
                    )

                    print("\nAI:", answer)

                except Exception as ex:

                    print("\nError:", ex)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
