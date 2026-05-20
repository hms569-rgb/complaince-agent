import httpx
import json
from anthropic import Anthropic

client = Anthropic()

# This is the MCP-style tool definition — we describe the tool in JSON schema
# so Claude knows when and how to call it
TOOLS = [
    {
        "name": "web_search",
        "description": """Search the web for current Indian regulations, compliance requirements,
        government notifications, and legal updates. Use this for every regulation you reference
        — never rely on training data for compliance information as it changes frequently.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific — include regulation name, year, and state if applicable."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_regulation_page",
        "description": """Fetch the full content of a government or legal webpage to get detailed
        regulation text. Use this after web_search when you need the full content of a specific URL.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the government/legal page to fetch"
                }
            },
            "required": ["url"]
        }
    }
]


async def execute_web_search(query: str) -> str:
    """
    Calls the Brave Search API (free tier: 2000 searches/month)
    Falls back to a DuckDuckGo scrape if no API key is set
    """
    try:
        # Using DuckDuckGo instant answer API — completely free, no key needed
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

            # Abstract (main answer)
            if data.get("Abstract"):
                results.append(f"Summary: {data['Abstract']}")
                results.append(f"Source: {data.get('AbstractURL', '')}")

            # Related topics
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"- {topic['Text']}")

            if results:
                return "\n".join(results)
            else:
                # If DDG returns nothing useful, return a message so agent knows to try differently
                return f"No instant results found for: {query}. Try a more specific query or different terms."

    except Exception as e:
        return f"Search failed: {str(e)}. Try fetching a specific government URL directly."


async def execute_fetch_page(url: str) -> str:
    """
    Fetches a webpage and returns its text content
    Works well for government sites like gst.gov.in, mca.gov.in, labour.gov.in
    """
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
            # Return first 3000 chars — enough for Claude to get the regulation details
            text = response.text[:3000]
            return f"Content from {url}:\n{text}"

    except Exception as e:
        return f"Could not fetch {url}: {str(e)}"


async def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    Router — Claude calls a tool by name, this function dispatches to the right handler
    This is the core of the MCP pattern: tool call → execute → return result to agent
    """
    if tool_name == "web_search":
        return await execute_web_search(tool_input["query"])
    elif tool_name == "fetch_regulation_page":
        return await execute_fetch_page(tool_input["url"])
    else:
        return f"Unknown tool: {tool_name}"