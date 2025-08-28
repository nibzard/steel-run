# Steel Python SDK Developer Manual

## Overview

Steel is a browser automation platform that provides managed browser sessions for web scraping, testing, and automation. The Steel Python SDK offers both synchronous and asynchronous clients for interacting with Steel's REST API.

OpenAPI specifications is in: steel-openapi-spec-v303.json

**Key Features:**
- Managed browser sessions with stealth capabilities
- PDF generation, web scraping, and screenshots
- Captcha solving and proxy support
- File upload/download management
- Full TypeScript-style type annotations

## Installation

```bash
pip install steel-sdk
```

For async support with aiohttp:
```bash
pip install steel-sdk[aiohttp]
```

## Authentication

Set your API key as an environment variable:
```bash
export STEEL_API_KEY="your_steel_api_key_here"
```

Or pass it directly:
```python
from steel import Steel
client = Steel(steel_api_key="your_steel_api_key_here")
```

## Core Concepts

### 1. Sessions
Browser sessions are the foundation of Steel. Each session is a managed Chrome browser instance.

**Session Lifecycle:**
- **Create** → **Use** → **Release**
- Sessions consume credits while active
- Always release sessions when done

### 2. Regions
Steel supports multiple regions for session placement:
- `lax` - Los Angeles
- `ord` - Chicago
- `iad` - Washington DC
- `bom` - Mumbai
- `scl` - Santiago
- `fra` - Frankfurt
- `hkg` - Hong Kong

## Quick Start

### Basic Usage (Sync)

```python
from steel import Steel

# Initialize client
client = Steel()

# Create a browser session
session = client.sessions.create(
    api_timeout=20000,
    use_proxy=True,
    region="lax"
)

print(f"Session ID: {session.id}")
print(f"WebSocket URL: {session.websocket_url}")
print(f"Debug URL: {session.debug_url}")

# Always release when done
client.sessions.release(session.id)
```

### Async Usage

```python
import asyncio
from steel import AsyncSteel

async def main():
    client = AsyncSteel()

    session = await client.sessions.create(
        api_timeout=20000,
        use_proxy=True,
        solve_captcha=True
    )

    print(f"Session created: {session.id}")

    # Release session
    await client.sessions.release(session.id)

asyncio.run(main())
```

## Sessions API

### Creating Sessions

```python
# Basic session
session = client.sessions.create()

# Advanced session configuration
session = client.sessions.create(
    # Browser settings
    dimensions={"width": 1920, "height": 1080},
    user_agent="Mozilla/5.0 (Custom Agent)",
    block_ads=True,

    # Stealth configuration
    stealth_config={
        "humanize_interactions": True,
        "skip_fingerprint_injection": False
    },

    # Proxy settings
    use_proxy=True,
    region="lax",
    # Or custom proxy
    proxy_url="http://username:password@proxy.example.com:8080",

    # Automation features
    solve_captcha=True,
    is_selenium=True,  # For Selenium WebDriver

    # Session management
    api_timeout=300000,  # 5 minutes
    session_id="custom-uuid",  # Optional custom ID
    namespace="my-project",

    # Extensions
    extension_ids=["ext-1", "ext-2"],  # Or ["all_ext"] for all

    # Credentials for auto-login
    credentials={
        "username": "user@example.com",
        "password": "password123"
    }
)
```

### Session Management

```python
# List all sessions
sessions = client.sessions.list(
    status="live",  # "live", "released", "failed"
    limit=50
)

for session in sessions:
    print(f"Session {session.id}: {session.status}")

# Get session details
session = client.sessions.retrieve("session-id")
print(f"Credits used: {session.credits_used}")
print(f"Duration: {session.duration}ms")

# Get session context (cookies, storage, etc.)
context = client.sessions.context("session-id")

# Get live session state
live_details = client.sessions.live_details("session-id")

# Release specific session
response = client.sessions.release("session-id")

# Release all sessions (careful!)
response = client.sessions.release_all()
```

## Quick Actions API

### Web Scraping

```python
# Simple scraping
response = client.scrape(
    url="https://example.com",
    format=["html", "markdown", "readability"]
)

print(response.content.html)
print(response.content.markdown)

# Advanced scraping with options
response = client.scrape(
    url="https://example.com",
    delay=2000,  # Wait 2 seconds before scraping
    format=["cleaned_html", "markdown"],
    screenshot=True,  # Include screenshot
    pdf=True,        # Include PDF
    use_proxy=True,
    region="fra"
)

# Access different formats
html_content = response.content.html
markdown_content = response.content.markdown
screenshot_url = response.screenshot.url
pdf_url = response.pdf.url
```

### PDF Generation

```python
# Generate PDF from URL
pdf_response = client.pdf(
    url="https://example.com",
    delay=1000,
    use_proxy=True,
    region="ord"
)

print(f"PDF URL: {pdf_response.pdf.url}")
print(f"PDF size: {pdf_response.pdf.size_bytes} bytes")

# Download PDF content
with open("output.pdf", "wb") as f:
    response = client.files.download(pdf_response.pdf.path)
    f.write(response.content)
```

### Screenshots

```python
# Capture screenshot
screenshot = client.screenshot(
    url="https://example.com",
    full_page=True,  # Capture entire page
    delay=1500,
    use_proxy=True
)

print(f"Screenshot URL: {screenshot.screenshot.url}")
print(f"Dimensions: {screenshot.screenshot.width}x{screenshot.screenshot.height}")
```

## File Management

### Global Files

```python
# List all files
files = client.files.list()
for file in files.files:
    print(f"{file.path}: {file.size_bytes} bytes")

# Upload file
with open("local-file.txt", "rb") as f:
    uploaded = client.files.upload(
        file=f,
        path="remote/path/file.txt"
    )
print(f"Uploaded to: {uploaded.path}")

# Download file
response = client.files.download("remote/path/file.txt")
with open("downloaded-file.txt", "wb") as f:
    f.write(response.content)

# Delete file
client.files.delete("remote/path/file.txt")
```

### Session Files

```python
# List files in a session
session_files = client.sessions.files.list("session-id")

# Upload file to session
with open("test.txt", "rb") as f:
    uploaded = client.sessions.files.upload(
        session_id="session-id",
        file=f,
        path="uploads/test.txt"
    )

# Download from session
response = client.sessions.files.download(
    path="uploads/test.txt",
    session_id="session-id"
)

# Download all session files as ZIP
archive = client.sessions.files.download_archive("session-id")
with open("session-files.zip", "wb") as f:
    f.write(archive.content)

# Delete session file
client.sessions.files.delete(
    path="uploads/test.txt",
    session_id="session-id"
)

# Delete all session files
client.sessions.files.delete_all("session-id")
```

## Captcha Solving

```python
# Enable captcha solving in session
session = client.sessions.create(
    solve_captcha=True,
    use_proxy=True
)

# Check captcha status
status = client.sessions.captchas.status("session-id")
print(f"Captcha detected: {status.captcha_detected}")

# Solve image captcha manually
captcha_response = client.sessions.captchas.solve_image(
    session_id="session-id",
    image_base64="base64_encoded_image"
)
print(f"Solution: {captcha_response.solution}")
```

## Credentials Management

```python
# Create credentials
credential = client.credentials.create(
    domain="example.com",
    username="user@example.com",
    password="secure_password",
    description="Login for example.com"
)

# List credentials
credentials = client.credentials.list()
for cred in credentials.credentials:
    print(f"{cred.domain}: {cred.username}")

# Update credentials
updated = client.credentials.update(
    credential_id=credential.id,
    password="new_password"
)

# Delete credentials
client.credentials.delete(credential_id=credential.id)
```

## Error Handling

```python
import steel
from steel import Steel

client = Steel()

try:
    session = client.sessions.create()

except steel.RateLimitError as e:
    print(f"Rate limit hit: {e.status_code}")

except steel.AuthenticationError as e:
    print(f"Auth failed: {e.status_code}")

except steel.APIConnectionError as e:
    print(f"Connection error: {e}")

except steel.APIStatusError as e:
    print(f"API error {e.status_code}: {e.response}")

except steel.APIError as e:
    print(f"General API error: {e}")
```

## Advanced Configuration

### Custom HTTP Client

```python
import httpx
from steel import Steel, DefaultHttpxClient

client = Steel(
    http_client=DefaultHttpxClient(
        proxy="http://my-proxy.com:8080",
        transport=httpx.HTTPTransport(local_address="0.0.0.0"),
        timeout=httpx.Timeout(60.0, connect=10.0)
    )
)
```

### Context Managers

```python
# Auto-cleanup with context manager
with Steel() as client:
    session = client.sessions.create()
    # Use session...
    client.sessions.release(session.id)
# Client automatically closed
```

### Raw Response Access

```python
# Get raw HTTP response
response = client.sessions.with_raw_response.create(
    api_timeout=20000
)

print(response.headers.get("X-Request-ID"))
session = response.parse()  # Get parsed Session object
```

### Streaming Responses

```python
# Stream large responses
with client.sessions.with_streaming_response.create() as response:
    print(response.headers.get("Content-Type"))

    # Stream the response
    for chunk in response.iter_bytes():
        process_chunk(chunk)
```

## Pagination

Steel API responses are automatically paginated:

```python
# Auto-pagination
all_sessions = []
for session in client.sessions.list(status="live"):
    all_sessions.append(session)
    print(f"Session: {session.id}")

# Manual pagination
first_page = client.sessions.list(status="live", limit=10)
if first_page.has_next_page():
    next_page = first_page.get_next_page()
    print(f"Next page has {len(next_page.sessions)} sessions")
```

## Best Practices

### 1. Resource Management
```python
# Always release sessions
try:
    session = client.sessions.create()
    # Use session...
finally:
    client.sessions.release(session.id)

# Or use context management for complex workflows
class SessionManager:
    def __init__(self, client):
        self.client = client
        self.session = None

    def __enter__(self):
        self.session = self.client.sessions.create()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.client.sessions.release(self.session.id)

# Usage
with SessionManager(client) as session:
    # Use session safely
    pass
```

### 2. Optimal Configuration
```python
# For web scraping
session = client.sessions.create(
    use_proxy=True,          # Avoid IP blocks
    stealth_config={
        "humanize_interactions": True  # More human-like
    },
    block_ads=True,          # Faster loading
    api_timeout=30000        # Allow time for loading
)

# For testing
session = client.sessions.create(
    is_selenium=True,        # Selenium compatibility
    dimensions={
        "width": 1920,
        "height": 1080
    },
    solve_captcha=True,      # Handle captchas
    api_timeout=60000        # Longer timeout for tests
)
```

### 3. Error Handling Patterns
```python
import time
from steel import RateLimitError, APIConnectionError

def create_session_with_retry(client, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.sessions.create()
        except RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except APIConnectionError:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
```

### 4. Async Best Practices
```python
import asyncio
import aiohttp
from steel import AsyncSteel, DefaultAioHttpClient

async def bulk_scraping(urls):
    # Use aiohttp for better async performance
    async with AsyncSteel(
        http_client=DefaultAioHttpClient()
    ) as client:
        # Create session once, use many times
        session = await client.sessions.create(
            use_proxy=True,
            api_timeout=60000
        )

        try:
            # Process URLs concurrently
            tasks = []
            for url in urls:
                task = scrape_url(client, url)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        finally:
            await client.sessions.release(session.id)

async def scrape_url(client, url):
    return await client.scrape(
        url=url,
        format=["markdown"],
        use_proxy=True
    )
```

## Environment Variables

- `STEEL_API_KEY` - Your Steel API key
- `STEEL_BASE_URL` - Override base URL (default: `https://api.steel.dev`)
- `STEEL_LOG` - Set to `info` or `debug` for logging

## Limits & Quotas

- **Sessions**: Check your plan's concurrent session limit
- **Credits**: Sessions consume credits based on duration and features
- **File uploads**: Check size limits for your plan
- **API rate limits**: Handled automatically with retries

## Migration from v1

Key changes if migrating from older versions:

1. **Import changes**: `from steel import Steel` (not `from steel.client import Steel`)
2. **Async client**: Use `AsyncSteel` instead of `Steel` with async methods
3. **Type hints**: Full type support with Pydantic models
4. **Error handling**: More specific exception types

This manual covers the essential Steel SDK functionality. For complete API reference, see the [official documentation](https://docs.steel.dev) and the `api.md` file in the SDK repository.