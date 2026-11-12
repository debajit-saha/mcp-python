
from fastmcp import FastMCP

mcp = FastMCP("Orders MCP Server")

# In-memory sample orders
ORDERS = {
    "ORD-001": {
        "customer_id": "CUST-001",
        "status": "Shipped",
        "amount": 1500
    },
    "ORD-002": {
        "customer_id": "CUST-001",
        "status": "Processing",
        "amount": 2500
    },
    "ORD-003": {
        "customer_id": "CUST-002",
        "status": "Delivered",
        "amount": 500
    }
}


@mcp.tool
def get_order_status(order_id: str) -> dict:
    """Get the status and details of an order."""

    order = ORDERS.get(order_id)

    if not order:
        return {"error": "Order not found"}

    return {
        "order_id": order_id,
        **order
    }


@mcp.tool
def list_customer_orders(customer_id: str) -> list:
    """List all orders belonging to a customer."""

    return [
        {
            "order_id": order_id,
            **order
        }
        for order_id, order in ORDERS.items()
        if order["customer_id"] == customer_id
    ]


@mcp.resource("orders://catalog")
def order_catalog() -> str:
    """Provide order status definitions."""

    return """
    Shipped: Order has been dispatched.
    Processing: Order is being prepared.
    Delivered: Order reached customer.
    Cancelled: Order was cancelled.
    """


@mcp.prompt
def analyze_orders(customer_id: str) -> str:
    """Generate instructions for analyzing customer orders."""

    return f"""
    Analyze orders for customer {customer_id}.

    Identify:
    - Shipped orders
    - Processing orders
    - Delivery issues
    - Overall summary
    """


if __name__ == "__main__":

    # mcp.run(transport="stdio")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
