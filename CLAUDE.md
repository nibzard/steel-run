# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a documentation and reference repository for Steel browser automation platform development. It contains comprehensive guides, API specifications, and strategic documentation for building web automation solutions using Steel.

## Core Development Principles

1. **Modularity**: Every component must be self-contained with clear interfaces. Services should be interchangeable, views should be composable, and business logic should be isolated from presentation concerns.

2. **Domain-Driven Design**: Code organization follows health document organization concepts. Use health terminology in naming, structure services around document organization workflows (document processing, text recognition, health timeline), and maintain strict boundaries between document organization and medical analysis concerns.

3. **Excessive Documentation**: All code must be thoroughly documented. Include comprehensive inline documentation for complex document processing logic, maintain detailed architectural decision records, and provide extensive code examples for health document organization concepts.

## Commit & Pull Request Guidelines
Commits: short, imperative subject; optional scope. Examples:
- fix: reset token clears colors
- ui: improve selected row highlight
- nix: wire Home Manager module

PRs: include a clear description, before/after terminal screenshot or asciinema for UI changes, linked issues, and notes on behavior or config (TRY_PATH). Update README.md when flags, defaults, or UX change.

## Key Files and Their Purpose

- **steel-llms.md** - Complete developer manual for Steel Python SDK covering browser automation, web scraping, sessions, and API integration with code examples
- **steel-openapi-spec-v303.json** - OpenAPI specification v3.0.3 for Steel REST API defining all endpoints, schemas, and types
- **python-web-dev-techstack.md** - Modern Python web development technology stack recommendations using uv, FastAPI, and production-ready tools
- **python-web-dev-deployment-services.md** - Deployment platforms and services guide for Python web applications
- **vision.md** - Strategic vision document outlining Steel's "Web Actions as a Service" positioning

## Development Context

When working on Steel-related projects based on this documentation:

1. **Package Management**: Use `uv` as the primary Python package manager (10-100x faster than pip, replaces pip-tools, poetry, pyenv, virtualenv)

2. **Steel SDK Usage**:
   - Install with `pip install steel-sdk` or `pip install steel-sdk[aiohttp]` for async support
   - Set API key: `export STEEL_API_KEY="your_key"`
   - Always follow session lifecycle: Create → Use → Release

3. **API Reference**: Use the OpenAPI spec (steel-openapi-spec-v303.json) as the authoritative source for Steel API endpoints and schemas

4. **Web Actions Philosophy**: Frame browser automation as atomic web functions rather than browser sessions - aligning with the "serverless web action platform" vision

## Architecture Principles

1. **Web Actions First**: Design interactions as atomic, serverless functions that can execute independently
2. **Session Management**: Proper lifecycle management for browser sessions to avoid resource leaks
3. **Reliability Focus**: Build with Steel's action reputation system in mind - prioritize successful execution rates
4. **API-First Design**: Use OpenAPI specifications to drive development and ensure API consistency

## Common Steel SDK Patterns

```python
from steel import Steel

# Sync client
client = Steel()
session = client.sessions.create()
# ... use session
client.sessions.release(session.id)

# Async client
async with Steel() as client:
    session = await client.sessions.create()
    # ... use session
    await client.sessions.release(session.id)
```
- We are running service through tailscale network here: http://100.126.153.59:8080/
- IMPORTANT: never do mock implementations, or placeholders