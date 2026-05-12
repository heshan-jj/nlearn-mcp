from mcp.server.fastmcp import FastMCP
from tools.get_deadlines import get_upcoming_deadlines
import logging

logging.basicConfig(level=logging.INFO)

# Initialize the FastMCP server
mcp = FastMCP("NLearn Sentinel")

# Register the get_deadlines tool
mcp.tool()(get_upcoming_deadlines)

if __name__ == "__main__":
    # Start the server using stdin/stdout
    mcp.run()
