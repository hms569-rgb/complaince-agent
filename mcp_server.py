import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# This is a standalone MCP server process.
# It exposes tools over the MCP protocol via stdio.
# Any MCP-compatible LLM client can connect to this — not just Claude.

app = Server("compliance-tools")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    MCP requires servers to expose a list_tools endpoint.
    The client (agent.py) calls this on startup to discover
    what tools are available — this is the MCP handshake.
    """
    return [
        types.Tool(
            name="web_search",
            description="""Search the web for current Indian regulations, compliance requirements,
            government notifications, and legal updates. Use this for every regulation you reference
            — never rely on training data for compliance information as it changes frequently.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific — include regulation name, year, and state if applicable."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="fetch_regulation_page",
            description="""Fetch the full content of a government or legal webpage to get detailed
            regulation text. Use this after web_search when you need the full content of a specific URL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the government/legal page to fetch"
                    }
                },
                "required": ["url"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    MCP requires servers to expose a call_tool endpoint.
    When the LLM decides to use a tool, the client sends the
    tool name and arguments here — this executes and returns results.
    """
    if name == "web_search":
        result = await execute_web_search(arguments["query"])
    elif name == "fetch_regulation_page":
        result = await execute_fetch_page(arguments["url"])
    else:
        result = f"Unknown tool: {name}"

    # MCP always returns a list of content blocks
    return [types.TextContent(type="text", text=result)]


async def execute_web_search(query: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                },
                timeout=10.0
            )
            data = response.json()

            results = []

            if data.get("Abstract"):
                results.append(f"Summary: {data['Abstract']}")
                results.append(f"Source: {data.get('AbstractURL', '')}")

            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"- {topic['Text']}")

            if results:
                return "\n".join(results)
            else:
                return f"No results found for: {query}. Try a more specific query."

    except Exception as e:
        return f"Search failed: {str(e)}"


async def execute_fetch_page(url: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            return f"Content from {url}:\n{response.text[:3000]}"

    except Exception as e:
        return f"Could not fetch {url}: {str(e)}"


async def main():
    # Run the MCP server over stdio
    # stdio means the client (agent.py) launches this as a subprocess
    # and communicates via stdin/stdout — this is the MCP standard transport
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())