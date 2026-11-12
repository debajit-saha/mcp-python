from fastmcp import FastMCP

mcp = FastMCP("Weather MCP Server")


@mcp.tool
def get_weather(city: str) -> dict:
    """Get weather information for a city."""

    weather_data = {
        "Hyderabad": {"temperature": 30, "condition": "Sunny"},
        "Bengaluru": {"temperature": 24, "condition": "Cloudy"},
        "Kolkata": {"temperature": 28, "condition": "Rainy"}
    }

    weather = weather_data.get(city)

    if not weather:
        return {"error": "City not found"}

    return {
        "city": city,
        **weather
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
