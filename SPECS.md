# Steel.run Development Specification

## Vision: Atomic Web Functions

Steel.run transforms browser automation from complex session management into simple function calls. Each web interaction is an atomic, self-contained function that executes and returns results immediately.

**Core Concept**: "Twitter post" is just a function call, not a browser session.

```python
# This is all developers need to know
result = await steel.run("post_tweet", message="Hello World!")
```

## MVP Product: Three Core Views

### 1. Landing Page - Natural Language Input

Clean interface with single text input for natural language web actions:

```
┌─────────────────────────────────────────────────────┐
│                    steel.run                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Type your web action...]                          │
│  "Post 'Hello World' to Twitter"                    │
│                                                     │
│                  [Execute]                          │
│                                                     │
│  Status: Ready                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Results will appear here...                     │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2. Dashboard - Action Gallery

Browse and execute pre-built atomic actions:

```
┌─────────────────────────────────────────────────────┐
│ Popular Actions                                     │
├─────────────────────────────────────────────────────┤
│ 📱 Post to Twitter          | Post tweet to timeline│
│ 📊 Check Stock Price        | Get current price     │
│ 🛒 Amazon Price Alert       | Monitor product cost  │
│ 💼 LinkedIn Profile Scrape  | Extract profile data  │
│ 📧 Gmail Unread Count       | Count new emails      │
│ 📸 Website Screenshot       | Capture page image    │
│ 📊 Extract Table Data       | Scrape HTML tables    │
│ 🔍 Google Search Results    | Get search results    │
└─────────────────────────────────────────────────────┘
```

### 3. Editor - Action Code Preview/Customize

View and customize atomic function implementations:

```python
# Atomic Web Function: Post to Twitter
async def post_tweet(message: str, credentials: dict):
    """
    Posts a tweet to Twitter timeline.
    
    Args:
        message: Tweet content (max 280 characters)
        credentials: {"username": "user", "password": "pass"}
    
    Returns:
        {"status": "posted", "tweet_id": "123", "screenshot": "base64..."}
    """
    with SteelBrowser(start_url="https://x.com") as browser:
        agent = ClaudeAgent(browser)
        
        task = f"""
        1. Login to X.com with username: {credentials['username']}
        2. Navigate to compose tweet
        3. Enter message: "{message}"
        4. Click post button
        5. Confirm tweet was posted successfully
        """
        
        return agent.execute_task(task)
```

## First Example: Twitter Posting Action

### User Flow

1. **Input**: User types "Post 'Building something cool with Steel!' to Twitter"
2. **Parse**: System extracts action=post_tweet, message="Building something cool with Steel!"
3. **Auth**: Prompts for Twitter credentials (first time only)
4. **Execute**: Runs atomic function via Steel + Claude
5. **Result**: Returns confirmation + screenshot

### Implementation

```python
class TwitterAction(BaseAction):
    name = "Post to Twitter"
    description = "Post a tweet to your timeline"
    requires_auth = True
    parameters = {
        "message": {"type": "string", "max_length": 280, "required": True}
    }
    
    async def execute(self, message: str, credentials: dict) -> dict:
        """Atomic execution - create session, run, release"""
        
        # Create Steel session
        session = self.steel.sessions.create(
            use_proxy=True,
            solve_captcha=True,
            api_timeout=30000
        )
        
        try:
            # Connect browser using Steel cookbook pattern
            with SteelBrowser(session) as browser:
                agent = ClaudeAgent(browser)
                
                task = f"""
                Navigate to X.com and login with the provided credentials.
                Then post this tweet: "{message}"
                Confirm the tweet was posted successfully.
                TASK_COMPLETED when tweet is visible on timeline.
                """
                
                result = agent.execute_task(task, credentials)
                
                return {
                    "status": "success",
                    "message": "Tweet posted successfully",
                    "tweet_content": message,
                    "screenshot": browser.screenshot(),
                    "timestamp": datetime.now().isoformat()
                }
                
        finally:
            # Always release session
            self.steel.sessions.release(session.id)
```

## Technical Architecture

### Stored Actions System

Steel.run allows users to save custom actions with specific parameters, creating a personal library of atomic web functions. These stored actions can be called via API by external services without requiring separate integrations.

**Key Benefits:**
- Users build their own action libraries
- No separate Zapier/n8n integrations needed
- API-first approach for all external services
- Actions are stored with configuration, not just code

### Project Structure

```
steel-run/
├── app/
│   ├── main.py                  # FastAPI application
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseAction class
│   │   ├── twitter.py           # Twitter actions
│   │   ├── amazon.py            # Amazon actions
│   │   ├── linkedin.py          # LinkedIn actions
│   │   └── gmail.py             # Gmail actions
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── executor.py          # Claude + Steel integration
│   │   └── parser.py            # Natural language parser
│   ├── api/
│   │   ├── __init__.py
│   │   ├── execute.py           # Execution endpoints
│   │   ├── actions.py           # Action management & storage
│   │   ├── stored_actions.py    # User action CRUD operations
│   │   └── auth.py              # API key & credential management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── stored_action.py     # StoredAction data model
│   │   ├── execution_run.py     # Action execution tracking
│   │   └── database.py          # SQLite database setup
│   ├── frontend/
│   │   ├── static/
│   │   │   ├── style.css
│   │   │   └── app.js
│   │   ├── templates/
│   │   │   ├── index.html       # Landing page
│   │   │   ├── dashboard.html   # Actions gallery
│   │   │   ├── editor.html      # Code editor
│   │   │   └── my_actions.html  # User's saved actions
│   │   └── __init__.py
│   └── config.py                # Configuration
├── requirements.txt
├── .env.example
└── README.md
```

### Core Components

#### BaseAction - Atomic Function Template

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from steel import Steel
from datetime import datetime

class BaseAction(ABC):
    """Base class for all atomic web actions"""
    
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    requires_auth: bool = False
    timeout_seconds: int = 30
    
    def __init__(self):
        self.steel = Steel()
    
    @abstractmethod
    async def execute(self, **params) -> Dict[str, Any]:
        """
        Execute atomic action - create session, run, release
        
        Returns:
            {
                "status": "success|failed",
                "message": "Human readable result",
                "data": {...},  # Action-specific data
                "screenshot": "base64...",  # Optional
                "timestamp": "ISO datetime"
            }
        """
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate input parameters against schema"""
        for param_name, param_config in self.parameters.items():
            if param_config.get("required", False) and param_name not in params:
                raise ValueError(f"Required parameter '{param_name}' missing")
            
            if param_name in params:
                value = params[param_name]
                param_type = param_config.get("type", "string")
                
                if param_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter '{param_name}' must be string")
                
                max_length = param_config.get("max_length")
                if max_length and len(value) > max_length:
                    raise ValueError(f"Parameter '{param_name}' exceeds max length {max_length}")
        
        return True
    
    def preview_code(self) -> str:
        """Return readable code for editor view"""
        import inspect
        return inspect.getsource(self.execute)
```

#### Natural Language Parser

```python
from anthropic import Anthropic
import re
from typing import Dict, Any

class ActionParser:
    """Parse natural language input into structured actions"""
    
    def __init__(self):
        self.claude = Anthropic()
        self.action_registry = {}  # Will be populated with available actions
    
    def parse(self, input_text: str) -> Dict[str, Any]:
        """
        Parse natural language into action and parameters
        
        Args:
            input_text: "Post 'Hello World' to Twitter"
            
        Returns:
            {
                "action_id": "twitter_post",
                "parameters": {"message": "Hello World"},
                "confidence": 0.95
            }
        """
        
        # Create action descriptions for Claude
        action_descriptions = ""
        for action_id, action_class in self.action_registry.items():
            action_descriptions += f"- {action_id}: {action_class.description}\n"
        
        prompt = f"""
        Parse this user request into a structured action:
        "{input_text}"
        
        Available actions:
        {action_descriptions}
        
        Return JSON with:
        - action_id: matching action identifier
        - parameters: extracted parameters as key-value pairs
        - confidence: 0.0-1.0 confidence score
        
        Examples:
        "Post 'Hello' to Twitter" -> {{"action_id": "twitter_post", "parameters": {{"message": "Hello"}}, "confidence": 0.95}}
        "Check Amazon price for iPhone" -> {{"action_id": "amazon_price_check", "parameters": {{"product": "iPhone"}}, "confidence": 0.90}}
        """
        
        response = self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse Claude's JSON response
        import json
        try:
            result = json.loads(response.content[0].text)
            return result
        except (json.JSONDecodeError, IndexError):
            return {
                "action_id": None,
                "parameters": {},
                "confidence": 0.0,
                "error": "Could not parse request"
            }
    
    def register_action(self, action_id: str, action_class):
        """Register available action for parsing"""
        self.action_registry[action_id] = action_class
```

### API Endpoints

#### Core API Structure

The Steel.run API provides both immediate execution and stored action management:

1. **Natural Language Execution** - Parse and execute actions from text
2. **Stored Action Management** - Save, update, and manage user actions
3. **External Service Integration** - Execute saved actions via API calls

#### Execute Natural Language Input

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Steel.run API")

class ExecuteRequest(BaseModel):
    input: str
    credentials: Optional[Dict[str, str]] = None

class ExecuteResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    timestamp: str

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_natural_language(request: ExecuteRequest):
    """Execute natural language web action"""
    
    try:
        # Parse natural language input
        parsed = parser.parse(request.input)
        
        if not parsed["action_id"]:
            raise HTTPException(400, "Could not understand request")
        
        if parsed["confidence"] < 0.7:
            raise HTTPException(400, f"Low confidence in parsing: {parsed['confidence']}")
        
        # Get action class
        action_class = action_registry.get(parsed["action_id"])
        if not action_class:
            raise HTTPException(400, f"Unknown action: {parsed['action_id']}")
        
        # Execute action
        action = action_class()
        
        # Add credentials if required
        if action.requires_auth and not request.credentials:
            raise HTTPException(400, "Credentials required for this action")
        
        if action.requires_auth:
            parsed["parameters"]["credentials"] = request.credentials
        
        # Validate parameters
        action.validate_parameters(parsed["parameters"])
        
        # Execute
        result = await action.execute(**parsed["parameters"])
        
        return ExecuteResponse(
            status=result["status"],
            message=result["message"],
            data=result.get("data"),
            screenshot=result.get("screenshot"),
            timestamp=result["timestamp"]
        )
        
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
```

#### Get Available Actions

```python
class ActionInfo(BaseModel):
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    requires_auth: bool

@app.get("/api/actions", response_model=List[ActionInfo])
async def list_actions():
    """Get all available atomic actions"""
    
    actions = []
    for action_id, action_class in action_registry.items():
        action = action_class()
        actions.append(ActionInfo(
            id=action_id,
            name=action.name,
            description=action.description,
            parameters=action.parameters,
            requires_auth=action.requires_auth
        ))
    
    return actions
```

#### Stored Action Management

```python
from datetime import datetime
from typing import Optional
from .models.stored_action import StoredAction, ExecutionRun

class StoredActionRequest(BaseModel):
    name: str
    description: str
    action_type: str
    parameters: Dict[str, Any]
    webhook_url: Optional[str] = None
    schedule: Optional[str] = None

@app.post("/api/actions/save")
async def save_action(request: StoredActionRequest, user_id: str = Depends(get_current_user)):
    """Save a custom action configuration for user"""
    
    action_id = f"user-{user_id}-{len(get_user_actions(user_id)) + 1}"
    
    stored_action = StoredAction(
        id=action_id,
        user_id=user_id,
        name=request.name,
        description=request.description,
        action_type=request.action_type,
        parameters=request.parameters,
        webhook_url=request.webhook_url,
        schedule=request.schedule,
        created_at=datetime.now()
    )
    
    # Save to database
    save_stored_action(stored_action)
    
    return {
        "action_id": action_id,
        "message": "Action saved successfully",
        "api_endpoint": f"/api/actions/{action_id}/run"
    }

@app.get("/api/actions/user")
async def get_user_actions(user_id: str = Depends(get_current_user)):
    """Get all saved actions for user"""
    
    actions = get_stored_actions_by_user(user_id)
    return [
        {
            "id": action.id,
            "name": action.name,
            "description": action.description,
            "action_type": action.action_type,
            "created_at": action.created_at,
            "last_run": action.last_run,
            "api_endpoint": f"/api/actions/{action.id}/run"
        }
        for action in actions
    ]

@app.put("/api/actions/{action_id}")
async def update_action(action_id: str, request: StoredActionRequest, user_id: str = Depends(get_current_user)):
    """Update saved action configuration"""
    
    stored_action = get_stored_action(action_id)
    if not stored_action or stored_action.user_id != user_id:
        raise HTTPException(404, "Action not found")
    
    # Update fields
    stored_action.name = request.name
    stored_action.description = request.description
    stored_action.parameters = request.parameters
    stored_action.webhook_url = request.webhook_url
    stored_action.schedule = request.schedule
    
    update_stored_action(stored_action)
    return {"message": "Action updated successfully"}

@app.delete("/api/actions/{action_id}")
async def delete_action(action_id: str, user_id: str = Depends(get_current_user)):
    """Delete saved action"""
    
    stored_action = get_stored_action(action_id)
    if not stored_action or stored_action.user_id != user_id:
        raise HTTPException(404, "Action not found")
    
    delete_stored_action(action_id)
    return {"message": "Action deleted successfully"}
```

#### External Service Integration

```python
@app.post("/api/actions/{action_id}/run")
async def run_stored_action(
    action_id: str, 
    override_params: Optional[Dict[str, Any]] = None,
    api_key: str = Depends(verify_api_key)
):
    """Execute stored action - used by external services like Zapier/n8n"""
    
    stored_action = get_stored_action(action_id)
    if not stored_action:
        raise HTTPException(404, "Action not found")
    
    # Create execution run record
    run_id = f"run-{int(time.time())}-{random.randint(1000, 9999)}"
    execution_run = ExecutionRun(
        id=run_id,
        action_id=action_id,
        status="executing",
        started_at=datetime.now(),
        parameters=override_params or stored_action.parameters
    )
    
    save_execution_run(execution_run)
    
    # Execute action asynchronously
    asyncio.create_task(execute_stored_action_async(stored_action, execution_run, override_params))
    
    return {
        "run_id": run_id,
        "status": "executing",
        "message": f"Action '{stored_action.name}' started",
        "status_url": f"/api/actions/{action_id}/status/{run_id}",
        "results_url": f"/api/actions/{action_id}/results/{run_id}",
        "webhook_url": stored_action.webhook_url
    }

@app.get("/api/actions/{action_id}/status/{run_id}")
async def get_execution_status(action_id: str, run_id: str):
    """Check execution status"""
    
    execution_run = get_execution_run(run_id)
    if not execution_run:
        raise HTTPException(404, "Run not found")
    
    return {
        "run_id": run_id,
        "action_id": action_id,
        "status": execution_run.status,  # executing, completed, failed
        "started_at": execution_run.started_at,
        "completed_at": execution_run.completed_at,
        "error": execution_run.error_message
    }

@app.get("/api/actions/{action_id}/results/{run_id}")
async def get_execution_results(action_id: str, run_id: str):
    """Get execution results"""
    
    execution_run = get_execution_run(run_id)
    if not execution_run:
        raise HTTPException(404, "Run not found")
    
    if execution_run.status != "completed":
        raise HTTPException(400, f"Execution not completed. Status: {execution_run.status}")
    
    return {
        "run_id": run_id,
        "action_id": action_id,
        "status": execution_run.status,
        "result": execution_run.result_data,
        "screenshot": execution_run.screenshot,
        "completed_at": execution_run.completed_at
    }

async def execute_stored_action_async(stored_action: StoredAction, execution_run: ExecutionRun, override_params: Optional[Dict]):
    """Execute stored action asynchronously"""
    
    try:
        # Get the base action class
        action_class = action_registry.get(stored_action.action_type)
        if not action_class:
            raise Exception(f"Unknown action type: {stored_action.action_type}")
        
        # Merge parameters
        params = stored_action.parameters.copy()
        if override_params:
            params.update(override_params)
        
        # Execute action
        action = action_class()
        result = await action.execute(**params)
        
        # Update execution run
        execution_run.status = "completed"
        execution_run.completed_at = datetime.now()
        execution_run.result_data = result.get("data", {})
        execution_run.screenshot = result.get("screenshot")
        
        # Send webhook if configured
        if stored_action.webhook_url:
            await send_webhook(stored_action.webhook_url, {
                "run_id": execution_run.id,
                "action_id": stored_action.id,
                "status": "completed",
                "result": execution_run.result_data
            })
        
    except Exception as e:
        execution_run.status = "failed"
        execution_run.completed_at = datetime.now()
        execution_run.error_message = str(e)
        
        # Send webhook for failure too
        if stored_action.webhook_url:
            await send_webhook(stored_action.webhook_url, {
                "run_id": execution_run.id,
                "action_id": stored_action.id,
                "status": "failed",
                "error": str(e)
            })
    
    finally:
        # Update stored action last run time
        stored_action.last_run = datetime.now()
        update_stored_action(stored_action)
        update_execution_run(execution_run)
```

#### Preview Action Code

```python
@app.get("/api/actions/{action_id}/code")
async def preview_action_code(action_id: str):
    """Get readable code for action"""
    
    # Handle both built-in and stored actions
    if action_id.startswith("user-"):
        stored_action = get_stored_action(action_id)
        if not stored_action:
            raise HTTPException(404, "Action not found")
        
        action_class = action_registry.get(stored_action.action_type)
        if not action_class:
            raise HTTPException(404, "Base action type not found")
        
        action = action_class()
        code = action.preview_code()
        
        return {
            "action_id": action_id,
            "name": stored_action.name,
            "description": stored_action.description,
            "code": code,
            "parameters": stored_action.parameters,
            "language": "python"
        }
    else:
        # Built-in action
        action_class = action_registry.get(action_id)
        if not action_class:
            raise HTTPException(404, "Action not found")
        
        action = action_class()
        code = action.preview_code()
        
        return {
            "action_id": action_id,
            "name": action.name,
            "code": code,
            "language": "python"
        }
```

### Frontend Implementation

#### Landing Page (index.html)

```html
<!DOCTYPE html>
<html>
<head>
    <title>steel.run - Atomic Web Functions</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>steel.run</h1>
            <p>Transform natural language into web actions</p>
        </header>
        
        <main>
            <div class="input-section">
                <textarea 
                    id="actionInput" 
                    placeholder="Type your web action..."
                    rows="3"
                ></textarea>
                <button id="executeBtn" class="primary-btn">Execute</button>
            </div>
            
            <div id="status" class="status hidden">
                <div class="spinner"></div>
                <span>Executing action...</span>
            </div>
            
            <div id="results" class="results hidden">
                <h3>Results</h3>
                <div class="result-content"></div>
                <img id="screenshot" class="screenshot" />
            </div>
            
            <div class="examples">
                <h3>Try these examples:</h3>
                <div class="example-grid">
                    <button class="example-btn" onclick="useExample(this)">
                        Post "Hello World!" to Twitter
                    </button>
                    <button class="example-btn" onclick="useExample(this)">
                        Check Amazon price for iPhone 15
                    </button>
                    <button class="example-btn" onclick="useExample(this)">
                        Take screenshot of apple.com
                    </button>
                </div>
            </div>
        </main>
        
        <nav>
            <a href="/dashboard">View All Actions</a>
            <a href="/editor">Code Editor</a>
        </nav>
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>
```

#### JavaScript Application Logic

```javascript
// app.js
class SteelRunApp {
    constructor() {
        this.executeBtn = document.getElementById('executeBtn');
        this.actionInput = document.getElementById('actionInput');
        this.status = document.getElementById('status');
        this.results = document.getElementById('results');
        
        this.executeBtn.addEventListener('click', () => this.execute());
        this.actionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.execute();
            }
        });
    }
    
    async execute() {
        const input = this.actionInput.value.trim();
        if (!input) return;
        
        this.showStatus();
        this.hideResults();
        
        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    input: input,
                    credentials: this.getStoredCredentials()
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Execution failed');
            }
            
            const result = await response.json();
            this.showResults(result);
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.hideStatus();
        }
    }
    
    showStatus() {
        this.status.classList.remove('hidden');
        this.executeBtn.disabled = true;
    }
    
    hideStatus() {
        this.status.classList.add('hidden');
        this.executeBtn.disabled = false;
    }
    
    showResults(result) {
        this.results.classList.remove('hidden');
        
        const content = this.results.querySelector('.result-content');
        content.innerHTML = `
            <div class="result-status ${result.status}">${result.status.toUpperCase()}</div>
            <p>${result.message}</p>
            ${result.data ? `<pre>${JSON.stringify(result.data, null, 2)}</pre>` : ''}
        `;
        
        if (result.screenshot) {
            const screenshot = document.getElementById('screenshot');
            screenshot.src = `data:image/png;base64,${result.screenshot}`;
            screenshot.classList.remove('hidden');
        }
    }
    
    showError(message) {
        this.results.classList.remove('hidden');
        const content = this.results.querySelector('.result-content');
        content.innerHTML = `
            <div class="result-status error">ERROR</div>
            <p>${message}</p>
        `;
    }
    
    hideResults() {
        this.results.classList.add('hidden');
    }
    
    getStoredCredentials() {
        // Simple credential storage (in production, use secure methods)
        const stored = localStorage.getItem('steel_credentials');
        return stored ? JSON.parse(stored) : null;
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    new SteelRunApp();
});

// Example button handler
function useExample(btn) {
    document.getElementById('actionInput').value = btn.textContent.trim();
}
```

### Action Library - Initial Implementation

#### Twitter Actions

```python
from .base import BaseAction
from ..agent.executor import ClaudeAgent, SteelBrowser
from datetime import datetime

class TwitterPostAction(BaseAction):
    name = "Post to Twitter"
    description = "Post a tweet to your Twitter timeline"
    requires_auth = True
    parameters = {
        "message": {
            "type": "string", 
            "required": True, 
            "max_length": 280,
            "description": "Tweet content"
        }
    }
    
    async def execute(self, message: str, credentials: dict) -> dict:
        session = self.steel.sessions.create(
            use_proxy=True,
            solve_captcha=True,
            api_timeout=30000
        )
        
        try:
            with SteelBrowser(session) as browser:
                agent = ClaudeAgent(browser)
                
                task = f"""
                Navigate to x.com and login using these credentials:
                Username: {credentials.get('username')}
                Password: {credentials.get('password')}
                
                After successful login, post this tweet: "{message}"
                
                Steps:
                1. Go to x.com/login
                2. Enter username and password
                3. Click login
                4. Find the tweet compose area
                5. Type the message
                6. Click the Post/Tweet button
                7. Verify the tweet appears on timeline
                
                TASK_COMPLETED when tweet is successfully posted and visible.
                """
                
                result = agent.execute_task(task)
                screenshot = browser.screenshot()
                
                return {
                    "status": "success",
                    "message": f"Tweet posted: {message[:50]}{'...' if len(message) > 50 else ''}",
                    "data": {
                        "tweet_content": message,
                        "platform": "twitter",
                        "char_count": len(message)
                    },
                    "screenshot": screenshot,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Failed to post tweet: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            self.steel.sessions.release(session.id)

class TwitterReplyAction(BaseAction):
    name = "Reply to Tweet"
    description = "Reply to a specific tweet"
    requires_auth = True
    parameters = {
        "tweet_url": {
            "type": "string",
            "required": True,
            "description": "URL of tweet to reply to"
        },
        "reply_text": {
            "type": "string", 
            "required": True,
            "max_length": 280,
            "description": "Reply content"
        }
    }
    
    async def execute(self, tweet_url: str, reply_text: str, credentials: dict) -> dict:
        # Similar implementation for replying to tweets
        pass
```

#### Amazon Actions

```python
class AmazonPriceCheckAction(BaseAction):
    name = "Check Amazon Price"
    description = "Get current price for a product on Amazon"
    requires_auth = False
    parameters = {
        "product": {
            "type": "string",
            "required": True,
            "description": "Product name or search term"
        },
        "max_results": {
            "type": "integer",
            "required": False,
            "default": 5,
            "description": "Maximum number of results"
        }
    }
    
    async def execute(self, product: str, max_results: int = 5) -> dict:
        session = self.steel.sessions.create(use_proxy=True)
        
        try:
            with SteelBrowser(session) as browser:
                agent = ClaudeAgent(browser)
                
                task = f"""
                Go to amazon.com and search for "{product}".
                Extract the top {max_results} results with:
                - Product title
                - Price
                - Rating
                - Number of reviews
                - Product URL
                
                Return this information in a structured format.
                TASK_COMPLETED when all product information is extracted.
                """
                
                result = agent.execute_task(task)
                screenshot = browser.screenshot()
                
                # Parse result from agent (would need structured extraction)
                return {
                    "status": "success",
                    "message": f"Found {max_results} results for '{product}'",
                    "data": {
                        "search_term": product,
                        "results_count": max_results,
                        "products": []  # Would be populated by agent
                    },
                    "screenshot": screenshot,
                    "timestamp": datetime.now().isoformat()
                }
                
        finally:
            self.steel.sessions.release(session.id)
```

### Data Models

#### StoredAction Schema

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import sqlite3
import json

@dataclass
class StoredAction:
    """User's saved action configuration"""
    id: str  # Format: user-{user_id}-{sequence}
    user_id: str
    name: str  # "My Daily Twitter Post"
    description: str  # "Posts my daily update to Twitter"
    action_type: str  # "twitter_post", "amazon_check", etc.
    parameters: Dict[str, Any]  # Saved parameters/credentials
    webhook_url: Optional[str] = None  # For result notifications
    schedule: Optional[str] = None  # Cron expression for scheduling
    created_at: datetime = None
    last_run: Optional[datetime] = None
    run_count: int = 0

@dataclass
class ExecutionRun:
    """Tracks individual action executions"""
    id: str  # Format: run-{timestamp}-{random}
    action_id: str
    status: str  # "executing", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = None  # Parameters used for this run

class DatabaseManager:
    """SQLite database operations for stored actions"""
    
    def __init__(self, db_path: str = "steel_actions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stored_actions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    action_type TEXT NOT NULL,
                    parameters TEXT NOT NULL,  -- JSON string
                    webhook_url TEXT,
                    schedule TEXT,
                    created_at TIMESTAMP,
                    last_run TIMESTAMP,
                    run_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_runs (
                    id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    result_data TEXT,  -- JSON string
                    screenshot TEXT,
                    error_message TEXT,
                    parameters TEXT,  -- JSON string
                    FOREIGN KEY (action_id) REFERENCES stored_actions(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    name TEXT,
                    created_at TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_stored_action(self, action: StoredAction):
        """Save stored action to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stored_actions
                (id, user_id, name, description, action_type, parameters, webhook_url, schedule, created_at, last_run, run_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.id, action.user_id, action.name, action.description,
                action.action_type, json.dumps(action.parameters),
                action.webhook_url, action.schedule, action.created_at,
                action.last_run, action.run_count
            ))
            conn.commit()
    
    def get_stored_action(self, action_id: str) -> Optional[StoredAction]:
        """Get stored action by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM stored_actions WHERE id = ?", (action_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return StoredAction(
                id=row['id'],
                user_id=row['user_id'],
                name=row['name'],
                description=row['description'],
                action_type=row['action_type'],
                parameters=json.loads(row['parameters']),
                webhook_url=row['webhook_url'],
                schedule=row['schedule'],
                created_at=row['created_at'],
                last_run=row['last_run'],
                run_count=row['run_count']
            )
    
    def get_stored_actions_by_user(self, user_id: str) -> List[StoredAction]:
        """Get all stored actions for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM stored_actions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            
            actions = []
            for row in cursor.fetchall():
                actions.append(StoredAction(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    description=row['description'],
                    action_type=row['action_type'],
                    parameters=json.loads(row['parameters']),
                    webhook_url=row['webhook_url'],
                    schedule=row['schedule'],
                    created_at=row['created_at'],
                    last_run=row['last_run'],
                    run_count=row['run_count']
                ))
            
            return actions
    
    def save_execution_run(self, run: ExecutionRun):
        """Save execution run to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO execution_runs
                (id, action_id, status, started_at, completed_at, result_data, screenshot, error_message, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.id, run.action_id, run.status, run.started_at,
                run.completed_at, json.dumps(run.result_data) if run.result_data else None,
                run.screenshot, run.error_message,
                json.dumps(run.parameters) if run.parameters else None
            ))
            conn.commit()
    
    def get_execution_run(self, run_id: str) -> Optional[ExecutionRun]:
        """Get execution run by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM execution_runs WHERE id = ?", (run_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return ExecutionRun(
                id=row['id'],
                action_id=row['action_id'],
                status=row['status'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                result_data=json.loads(row['result_data']) if row['result_data'] else None,
                screenshot=row['screenshot'],
                error_message=row['error_message'],
                parameters=json.loads(row['parameters']) if row['parameters'] else None
            )
```

### Security & Credentials Management

```python
import os
import json
import hashlib
import secrets
from cryptography.fernet import Fernet
from typing import Dict, Optional

class CredentialManager:
    """Secure credential storage and retrieval"""
    
    def __init__(self):
        # In production, store key securely (env var, vault, etc.)
        self.encryption_key = os.getenv('CREDENTIAL_ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key()
        
        self.cipher = Fernet(self.encryption_key)
        self.storage_file = "credentials.enc"
    
    def store(self, user_id: str, service: str, credentials: Dict[str, str]) -> bool:
        """Store encrypted credentials for user and service"""
        try:
            # Load existing credentials
            all_creds = self._load_all_credentials()
            
            # Add/update credentials
            if user_id not in all_creds:
                all_creds[user_id] = {}
            
            all_creds[user_id][service] = credentials
            
            # Encrypt and save
            encrypted_data = self.cipher.encrypt(json.dumps(all_creds).encode())
            
            with open(self.storage_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            print(f"Error storing credentials: {e}")
            return False
    
    def retrieve(self, user_id: str, service: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted credentials for user and service"""
        try:
            all_creds = self._load_all_credentials()
            return all_creds.get(user_id, {}).get(service)
        except Exception as e:
            print(f"Error retrieving credentials: {e}")
            return None
    
    def _load_all_credentials(self) -> Dict:
        """Load and decrypt all stored credentials"""
        try:
            if not os.path.exists(self.storage_file):
                return {}
            
            with open(self.storage_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
            
        except Exception:
            return {}
    
    def validate_twitter_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Twitter credentials by attempting login"""
        required_fields = ['username', 'password']
        return all(field in credentials and credentials[field] for field in required_fields)
```

### Configuration

```python
import os
from typing import Dict, Any

class Config:
    """Application configuration"""
    
    # API Keys
    STEEL_API_KEY: str = os.getenv("STEEL_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Execution limits
    MAX_EXECUTION_TIME: int = 30  # seconds
    MAX_CONCURRENT_SESSIONS: int = 10
    SESSION_TIMEOUT: int = 30000  # milliseconds
    
    # Rate limiting
    RATE_LIMIT_PER_IP: int = 100  # per hour
    RATE_LIMIT_PER_USER: int = 500  # per hour
    
    # Security
    CREDENTIAL_ENCRYPTION_KEY: str = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # Feature flags
    ENABLE_SCREENSHOT: bool = True
    ENABLE_CREDENTIAL_STORAGE: bool = True
    ENABLE_RATE_LIMITING: bool = True
    
    # Blocked domains (from cookbook)
    BLOCKED_DOMAINS = [
        "maliciousbook.com",
        "evilvideos.com", 
        "darkwebforum.com",
        "shadytok.com",
        "suspiciouspins.com",
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_keys = [
            "STEEL_API_KEY",
            "ANTHROPIC_API_KEY"
        ]
        
        missing_keys = [key for key in required_keys if not getattr(cls, key)]
        
        if missing_keys:
            print(f"Missing required configuration: {', '.join(missing_keys)}")
            return False
        
        return True

# Load configuration
config = Config()
```

### Deployment

#### Requirements

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
steel-sdk==1.0.0
anthropic==0.7.0
playwright==1.39.0
python-dotenv==1.0.0
cryptography==41.0.7
pillow==10.1.0
jinja2==3.1.2
python-multipart==0.0.6
```

#### Environment Variables

```bash
# .env.example
STEEL_API_KEY=your_steel_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CREDENTIAL_ENCRYPTION_KEY=generate_this_key
SECRET_KEY=your_secret_key_here
```

#### Startup Script

```python
# main.py
import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import config
from app.api import execute, actions, auth
from app.actions import twitter, amazon, linkedin, gmail

# Validate configuration
if not config.validate():
    exit(1)

# Create FastAPI app
app = FastAPI(
    title="Steel.run - Atomic Web Functions",
    description="Transform natural language into web actions",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/frontend/templates")

# Include API routes
app.include_router(execute.router, prefix="/api")
app.include_router(actions.router, prefix="/api") 
app.include_router(auth.router, prefix="/api")

# Frontend routes
@app.get("/")
async def landing_page():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/dashboard")
async def dashboard():
    return templates.TemplateResponse("dashboard.html", {"request": {}})

@app.get("/editor")
async def editor():
    return templates.TemplateResponse("editor.html", {"request": {}})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV") == "development"
    )
```

## Success Metrics

### Performance Targets
- **Twitter Post Execution**: <10 seconds average
- **Action Success Rate**: 90% for well-defined actions
- **API Response Time**: <200ms for non-execution endpoints
- **Concurrent Users**: Support 10+ simultaneous executions

### Feature Completeness
- ✅ Natural language input parsing
- ✅ Twitter posting action
- ✅ Dashboard with action gallery
- ✅ Code preview/editor
- ✅ Secure credential storage
- ✅ Screenshot capture
- ✅ Error handling and recovery

### User Experience
- Simple, one-click action execution
- Clear error messages for failures  
- Visual feedback with screenshots
- Template actions for common tasks
- Code transparency in editor view

## External Service Integration Strategy

### Universal API Approach

Instead of building separate integrations for each service, Steel.run provides a universal API that any external service can use:

**No Custom Connectors Needed:**
- Zapier uses HTTP requests to call stored actions
- n8n configures API endpoints directly  
- Make.com sets up webhook workflows
- Any service with HTTP support can integrate

### Integration Examples

#### Zapier Integration
```
Step 1: HTTP Request
  Method: POST
  URL: https://steel.run/api/actions/user-john-twitter-post/run
  Headers: Authorization: Bearer sk-abc123...
  Body: {
    "override_params": {
      "message": "{{trigger.message}}"
    }
  }

Step 2: HTTP Request (Check Status)
  Method: GET
  URL: https://steel.run/api/actions/user-john-twitter-post/status/{{run_id}}
  
Step 3: HTTP Request (Get Results)
  Method: GET
  URL: https://steel.run/api/actions/user-john-twitter-post/results/{{run_id}}
```

#### n8n Workflow
```json
{
  "nodes": [
    {
      "name": "Execute Steel Action",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "https://steel.run/api/actions/user-mary-amazon-check/run",
        "authentication": "genericCredentialType",
        "headers": {
          "Authorization": "Bearer sk-xyz789..."
        },
        "body": {
          "override_params": {
            "product": "{{$node[\"Trigger\"].json[\"product_name\"]}}"
          }
        }
      }
    }
  ]
}
```

#### Webhook Notifications

Users can configure webhook URLs for their stored actions to receive results:

```python
# User saves action with webhook
{
  "name": "Daily Price Check",
  "action_type": "amazon_check",
  "webhook_url": "https://hooks.zapier.com/hooks/catch/123456/abc123/",
  "parameters": {"product": "iPhone 15"}
}

# Steel.run sends results to webhook
POST https://hooks.zapier.com/hooks/catch/123456/abc123/
{
  "run_id": "run-1640995200-1234",
  "action_id": "user-john-price-check",
  "status": "completed",
  "result": {
    "product": "iPhone 15",
    "price": "$899.00",
    "in_stock": true
  },
  "screenshot": "base64..."
}
```

### Benefits of This Approach

1. **No Maintenance Overhead**: No custom connectors to build or maintain
2. **Universal Compatibility**: Works with any service that supports HTTP requests
3. **User Ownership**: Users control their action library and API keys
4. **Flexibility**: External services can customize parameters per execution
5. **Scalability**: One API serves all integration needs

### API Key Management for External Services

```python
class APIKeyManager:
    """Manage API keys for external service access"""
    
    def generate_api_key(self, user_id: str, name: str = "Default") -> str:
        """Generate new API key for user"""
        key_id = f"sk-{secrets.token_hex(8)}"
        api_key = f"sk-{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Store in database
        with sqlite3.connect("steel_actions.db") as conn:
            conn.execute("""
                INSERT INTO api_keys (key_id, user_id, key_hash, name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key_id, user_id, key_hash, name, datetime.now()))
            conn.commit()
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user_id"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with sqlite3.connect("steel_actions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT user_id FROM api_keys WHERE key_hash = ?", (key_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update last_used timestamp
                conn.execute(
                    "UPDATE api_keys SET last_used = ? WHERE key_hash = ?",
                    (datetime.now(), key_hash)
                )
                conn.commit()
                return row['user_id']
        
        return None

# FastAPI dependency for API key verification
async def verify_api_key(authorization: str = Header(None)) -> str:
    """Verify API key from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    api_key = authorization.replace("Bearer ", "")
    user_id = api_key_manager.verify_api_key(api_key)
    
    if not user_id:
        raise HTTPException(401, "Invalid API key")
    
    return user_id
```

## Implementation Timeline

### Week 1: Foundation + Storage
- [ ] FastAPI project setup with SQLite database
- [ ] Steel SDK integration  
- [ ] BaseAction class implementation
- [ ] StoredAction and ExecutionRun models
- [ ] Basic Claude agent integration

### Week 2: First Action + Storage API
- [ ] Twitter login flow and posting action
- [ ] Stored action CRUD endpoints
- [ ] API key generation and verification
- [ ] External service execution endpoint

### Week 3: Frontend + My Actions
- [ ] Landing page with input field and "Save Action" feature
- [ ] Dashboard with action gallery
- [ ] "My Actions" page for stored actions management
- [ ] Basic code editor view with stored action preview

### Week 4: Additional Actions + Webhooks
- [ ] Amazon price checking action
- [ ] LinkedIn profile extraction action
- [ ] Gmail unread count action
- [ ] Webhook notification system

### Week 5: Integration Examples + Deploy
- [ ] Create Zapier/n8n integration examples
- [ ] API documentation for external services
- [ ] Rate limiting and security review
- [ ] Deploy to Railway/Render with example workflows

This specification delivers the MVP of atomic web functions - self-contained actions that developers can call as easily as any other function, abstracting away all browser complexity while providing powerful web automation capabilities.