"""
AgentOS MCP Server
Exposes the RAG, Search, Code, and Orchestrator agents as MCP tools.
This lets Claude Code, Claude Desktop, or any MCP client call AgentOS agents directly.

Usage:
    python -m mcp_server.server

Then add to claude_desktop_config.json:
{
  "mcpServers": {
    "agentos": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/agentos"
    }
  }
}
"""

import asyncio
import json
from typing import Any

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from agents.rag_agent import get_rag_agent
from agents.search_agent import get_search_agent
from agents.code_agent import get_code_agent
from orchestrator.graph import run_orchestrator

logger = structlog.get_logger(__name__)

server = Server("agentos")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="rag_retrieve",
            description=(
                "Retrieve relevant documents from the AgentOS knowledge base using semantic search. "
                "Use this when you need to find specific information from ingested documents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "namespace": {"type": "string", "description": "Document namespace (default: 'default')", "default": "default"},
                    "top_k": {"type": "integer", "description": "Number of results to return (default: 5)", "default": 5},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="web_search",
            description=(
                "Search the web for current, real-time information. "
                "Use when you need up-to-date data not in the knowledge base."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "max_results": {"type": "integer", "description": "Max results to return (default: 5)", "default": 5},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="execute_python",
            description=(
                "Execute Python code in a secure sandbox and return the output. "
                "Great for calculations, data analysis, or testing code snippets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "timeout": {"type": "integer", "description": "Execution timeout in seconds (default: 30)", "default": 30},
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="agentos_query",
            description=(
                "Run a full multi-agent query through the AgentOS orchestrator. "
                "Automatically routes through RAG, Search, Code execution, and Critic evaluation. "
                "Use this for complex questions that may need multiple information sources."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The question or task to process"},
                    "session_id": {"type": "string", "description": "Session ID for conversation continuity (optional)", "default": "mcp-session"},
                    "enable_rag": {"type": "boolean", "description": "Enable knowledge base retrieval", "default": True},
                    "enable_search": {"type": "boolean", "description": "Enable web search", "default": False},
                    "enable_code": {"type": "boolean", "description": "Enable code execution", "default": False},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="ingest_document",
            description=(
                "Ingest a document into the AgentOS knowledge base for future retrieval. "
                "The document will be chunked, embedded, and stored in ChromaDB."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document text content"},
                    "namespace": {"type": "string", "description": "Namespace for organizing documents", "default": "default"},
                },
                "required": ["title", "content"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "rag_retrieve":
            rag = get_rag_agent()
            contexts, latency_ms = await rag.retrieve(
                query=arguments["query"],
                namespace=arguments.get("namespace", "default"),
                top_k=arguments.get("top_k", 5),
            )
            result = rag.format_context(contexts)
            return [types.TextContent(
                type="text",
                text=f"{result}\n\n_Retrieved in {latency_ms:.0f}ms_"
            )]

        elif name == "web_search":
            search = get_search_agent()
            results, latency_ms = await search.search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 5),
            )
            result = search.format_results(results)
            return [types.TextContent(
                type="text",
                text=f"{result}\n\n_Searched in {latency_ms:.0f}ms_"
            )]

        elif name == "execute_python":
            code_agent = get_code_agent()
            result = await code_agent.execute(
                code=arguments["code"],
                timeout=arguments.get("timeout", 30),
            )
            formatted = code_agent.format_result(result)
            return [types.TextContent(type="text", text=formatted)]

        elif name == "agentos_query":
            state = await run_orchestrator(
                query=arguments["query"],
                session_id=arguments.get("session_id", "mcp-session"),
                enable_rag=arguments.get("enable_rag", True),
                enable_search=arguments.get("enable_search", False),
                enable_code=arguments.get("enable_code", False),
                enable_eval=True,
            )

            response = state["final_response"]
            provider = state.get("provider_used", "unknown")
            latency = state.get("total_latency_ms", 0)
            eval_m = state.get("eval_metrics", {})
            score = eval_m.get("overall_score", 0) if eval_m else 0

            metadata = (
                f"\n\n---\n"
                f"_Provider: {provider} · Latency: {latency:.0f}ms"
                f" · Eval score: {score:.2f} · Retries: {state.get('retry_count', 0)}_"
            )
            return [types.TextContent(type="text", text=response + metadata)]

        elif name == "ingest_document":
            rag = get_rag_agent()
            result = await rag.ingest(
                title=arguments["title"],
                content=arguments["content"],
                namespace=arguments.get("namespace", "default"),
            )
            return [types.TextContent(
                type="text",
                text=f"✅ Ingested '{result['title']}' into namespace '{result['namespace']}' "
                     f"as {result['chunk_count']} chunks."
            )]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error("mcp_tool_error", tool=name, error=str(e))
        return [types.TextContent(type="text", text=f"Error running {name}: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
