# Compliance Agent 🇮🇳

An AI-native compliance analysis service for Indian businesses — built for AI-native service companies.

Instead of giving businesses a tool to check compliance themselves, this agent does the work — it analyzes your business profile, searches live government regulations, and produces a detailed compliance report.

## What it does

- Takes a business profile (type, state, sector, turnover, employees)
- Spawns an MCP tool server with web search and document fetching capabilities
- Runs an agentic loop — Claude searches live Indian regulations, cross-references the business profile, identifies compliance gaps
- Streams the analysis back to the user in real time
- Produces a structured report with specific action items, deadlines, and portal links

## Tech stack

- FastAPI— async REST API with SSE streaming
- Claude (Anthropic)— agentic reasoning and tool orchestration  
- MCP — decoupled tool server architecture
- Pydantic — request validation
- Docker— containerized deployment
- GitHub Actions — CI/CD pipeline

