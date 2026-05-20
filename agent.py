import anthropic
import json
import sys
import os
from typing import AsyncGenerator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from models import BusinessProfile
from prompts import SYSTEM_PROMPT, build_analysis_prompt
from dotenv import load_dotenv

load_dotenv()

client = anthropic.AsyncAnthropic()


async def run_compliance_agent(profile: BusinessProfile) -> AsyncGenerator[str, None]:

    yield f"data: {json.dumps({'type': 'status', 'content': 'Agent started — connecting to MCP server...'})}\n\n"

    mcp_server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[mcp_server_path],
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                # MCP handshake — discover tools from the server
                await session.initialize()
                tools_result = await session.list_tools()

                # Convert MCP tool definitions to Anthropic format
                anthropic_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    }
                    for tool in tools_result.tools
                ]

                yield f"data: {json.dumps({'type': 'status', 'content': f'MCP connected — {len(anthropic_tools)} tools available'})}\n\n"

                messages = [
                    {
                        "role": "user",
                        "content": build_analysis_prompt(profile)
                    }
                ]

                iteration = 0
                max_iterations = 10

                while iteration < max_iterations:
                    iteration += 1

                    yield f"data: {json.dumps({'type': 'status', 'content': f'Thinking... (step {iteration})'})}\n\n"

                    try:
                        response = await client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=4096,
                            system=SYSTEM_PROMPT,
                            tools=anthropic_tools,
                            messages=messages
                        )
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'API error: {str(e)}'})}\n\n"
                        break

                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    if response.stop_reason == "end_turn":
                        for block in response.content:
                            if hasattr(block, "text"):
                                words = block.text.split(" ")
                                chunk = ""
                                for word in words:
                                    chunk += word + " "
                                    if len(chunk) > 50:
                                        yield f"data: {json.dumps({'type': 'report', 'content': chunk})}\n\n"
                                        chunk = ""
                                if chunk:
                                    yield f"data: {json.dumps({'type': 'report', 'content': chunk})}\n\n"
                        break

                    elif response.stop_reason == "tool_use":
                        tool_results = []

                        for block in response.content:
                            if block.type == "tool_use":
                                tool_name = block.name
                                tool_input = block.input

                                query_or_url = tool_input.get("query", tool_input.get("url", ""))
                                yield f"data: {json.dumps({'type': 'tool_call', 'content': f'Searching: {query_or_url}...'})}\n\n"

                                # Call tool via MCP session — goes to mcp_server.py's call_tool handler
                                result = await session.call_tool(tool_name, tool_input)
                                result_text = result.content[0].text if result.content else "No result"

                                yield f"data: {json.dumps({'type': 'tool_result', 'content': f'Got result for: {tool_name}'})}\n\n"

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_text
                                })

                        messages.append({
                            "role": "user",
                            "content": tool_results
                        })

                    else:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'Unexpected stop: {response.stop_reason}'})}\n\n"
                        break

                if iteration >= max_iterations:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Agent reached max iterations'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': f'MCP connection error: {str(e)}'})}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'content': 'Analysis complete'})}\n\n"