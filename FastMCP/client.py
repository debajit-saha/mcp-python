
import asyncio
from pathlib import Path
import json
from fastmcp import Client

SERVER_FILE = Path(__file__).with_name("server.py")
SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    print("Starting MCP server...")

    # async with Client(SERVER_FILE) as client:
    async with Client(SERVER_URL) as client:

        print("MCP session initialized successfully!")

        tools = await client.list_tools()

        print("\nAvailable tools:")

        for tool in tools:
            print(tool.name)

        result = await client.call_tool(
            "get_order_status",
            {"order_id": "ORD-001"}
        )

        print("\nOrder status:")
        order = json.loads(result.content[0].text)
        print(json.dumps(order, indent=2))

        # Call another tool
        result = await client.call_tool(
            "list_customer_orders",
            {"customer_id": "CUST-001"}
        )

        print("\nCustomer orders:")
        order = json.loads(result.content[0].text)
        print(json.dumps(order, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
