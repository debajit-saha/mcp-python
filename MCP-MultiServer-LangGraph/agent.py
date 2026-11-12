
import sys
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

BASE_DIR = Path(__file__).parent


# --------------------------------------------------
# 1. Azure AI Foundry Model
# --------------------------------------------------

model = ChatOpenAI(
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    temperature=0
)


# --------------------------------------------------
# 2. Configure MCP Servers
# --------------------------------------------------

client = MultiServerMCPClient({
    "orders": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [
            str(BASE_DIR / "servers" / "orders_server.py")
        ]
    },
    "weather": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [
            str(BASE_DIR / "servers" / "weather_server.py")
        ]
    }
})


# --------------------------------------------------
# 3. Build LangGraph
# --------------------------------------------------

async def build_graph():

    # Load tools from all MCP servers
    tools = await client.get_tools()

    print("Available MCP tools:")
    for tool in tools:
        print("-", tool.name)

    # Bind tools to the model
    model_with_tools = model.bind_tools(tools)

    # Node 1: Call LLM
    async def call_model(state: MessagesState):

        system_message = {
            "role": "system",
            "content": (
                "You are a helpful assistant. "
                "Use MCP tools when needed to answer questions. "
                "Do not invent order or weather information."
            )
        }

        messages = [system_message] + state["messages"]

        response = await model_with_tools.ainvoke(messages)

        return {"messages": [response]}

    # Conditional routing
    def should_continue(state: MessagesState):

        last_message = state["messages"][-1]

        if last_message.tool_calls:
            return "tools"

        return END

    # Create graph
    graph_builder = StateGraph(MessagesState)

    # Add nodes
    graph_builder.add_node("call_model", call_model)
    graph_builder.add_node("tools", ToolNode(tools))

    # Add edges
    graph_builder.add_edge(START, "call_model")

    graph_builder.add_conditional_edges(
        "call_model",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    graph_builder.add_edge("tools", "call_model")

    # Compile
    graph = graph_builder.compile()

    return graph


# --------------------------------------------------
# 4. Run Agent
# --------------------------------------------------

async def main():

    graph = await build_graph()

    questions = [
        "What is the weather in Hyderabad?",
        "Show all orders for customer CUST-001.",
        "Show CUST-001 orders and weather in Hyderabad."
    ]

    for question in questions:

        print("\nQuestion:", question)

        result = await graph.ainvoke({
            "messages": [
                {"role": "user", "content": question}
            ]
        })

        print("Answer:", result["messages"][-1].content)
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
