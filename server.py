from mcp.server.fastmcp import FastMCP
from tools.get_deadlines import get_upcoming_deadlines, get_past_deadlines
from tools.get_assignment import get_assignment
import logging

logging.basicConfig(level=logging.INFO)

# Initialize the FastMCP server
mcp = FastMCP("NLearn Sentinel")

# Register the tools
mcp.tool()(get_upcoming_deadlines)
mcp.tool()(get_past_deadlines)
mcp.tool()(get_assignment)

if __name__ == "__main__":
    # Start the server using stdin/stdout
    mcp.run()
