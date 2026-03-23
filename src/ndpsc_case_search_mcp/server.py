from fastmcp import FastMCP
from starlette.responses import JSONResponse

from ndpsc_case_search_mcp.tools import ALL_TOOLS

mcp = FastMCP(name="ndpsc-case-search")

for fn in ALL_TOOLS:
    mcp.tool(fn)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "healthy", "service": "ndpsc-case-search"})


def main():
    mcp.run(transport="http", host="0.0.0.0", port=8000, stateless_http=True)


if __name__ == "__main__":
    main()
