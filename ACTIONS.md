# Steel.run Actions Framework

This document describes the enhanced BaseAction framework, Claude Agent integration, and Twitter actions implementation for Steel.run - the atomic web functions platform.

## Architecture Overview

### BaseAction Framework
The enhanced `BaseAction` class provides:

- **Session Lifecycle Management**: Automatic Steel browser session creation, usage, and cleanup
- **Parameter Validation**: Type checking, range validation, and required field enforcement
- **Error Recovery**: Comprehensive exception handling with retry mechanisms
- **Resource Management**: Automatic cleanup of sessions and resources
- **Screenshot Capture**: Evidence collection for debugging and verification
- **Timeout Handling**: Configurable execution timeouts with graceful failure

### Claude Agent Integration
The `ClaudeAgent` system enables:

- **Natural Language Processing**: Convert user intents to browser actions
- **Computer Use Integration**: Claude's visual understanding for web automation
- **Safety Controls**: Blocked domain lists and URL validation
- **Evidence Collection**: Screenshots and execution traces for verification
- **Adaptive Execution**: Multi-step task completion with feedback loops

### Action Types Implemented

#### TwitterPostAction
- **Purpose**: Post tweets to Twitter/X.com
- **Authentication**: Requires Twitter credentials
- **Features**: Message validation, character limit checking, posting verification
- **Safety**: Anti-detection measures, human-like interaction patterns

#### TwitterReplyAction  
- **Purpose**: Reply to specific tweets on Twitter/X.com
- **Authentication**: Requires Twitter credentials
- **Features**: Tweet URL validation, threaded reply handling, confirmation
- **Safety**: URL validation, context-aware replies

## Implementation Details

### Session Management Pattern
```python
# Create Steel browser session
session_id = await self.create_session(
    use_proxy=True,
    solve_captcha=True,
    stealth_config={
        "humanize_interactions": True,
        "skip_fingerprint_injection": False
    }
)

# Use session with automatic cleanup
try:
    browser_session = BrowserSession(self.steel, session_id)
    agent = ClaudeAgent(browser_session)
    result = await agent.execute_task(task_description, context)
    return await self._process_result(result, params)
finally:
    await self.release_session(session_id)
```

### Claude Computer Use Pattern
```python
# Initialize Claude agent with browser session
agent = ClaudeAgent(browser_session)

# Execute task with natural language
task = """
Navigate to x.com, login with credentials, and post this tweet:
'Hello from Steel.run! 🚀'

Requirements:
- Handle captchas and verification
- Verify successful posting
- Capture screenshots for evidence
"""

result = await agent.execute_task(task, context)
```

### Parameter Validation
```python
parameters = {
    "message": {
        "type": "string",
        "required": True,
        "min_length": 1,
        "max_length": 280,
        "description": "Tweet message (max 280 characters)"
    },
    "credentials": {
        "type": "object",
        "required": True,
        "properties": {
            "username": {"type": "string", "required": True},
            "password": {"type": "string", "required": True}
        }
    }
}
```

## Usage Examples

### Basic Twitter Posting
```python
from app.actions.twitter import TwitterPostAction

action = TwitterPostAction()

result = await action.execute_safely(
    message="Hello from Steel.run! 🚀",
    credentials={
        "username": "your_username",
        "password": "your_password"
    },
    wait_for_confirmation=True
)

print(f"Status: {result['status']}")
print(f"Message: {result['message']}")
```

### Twitter Reply
```python
from app.actions.twitter import TwitterReplyAction

action = TwitterReplyAction()

result = await action.execute_safely(
    tweet_url="https://twitter.com/user/status/123456789",
    reply_message="Great point! Thanks for sharing.",
    credentials={
        "username": "your_username", 
        "password": "your_password"
    }
)
```

### Action Registration
```python
from app.actions.registry import register_action
from app.actions.twitter import TwitterPostAction, TwitterReplyAction

# Register actions
register_action("twitter-post", TwitterPostAction)
register_action("twitter-reply", TwitterReplyAction)

# Actions are now available via registry
registry = get_action_registry()
action_instance = registry.create_instance("twitter-post")
```

## Configuration

### Environment Variables
```bash
# Steel API Configuration
STEEL_API_KEY=your_steel_api_key
DEFAULT_REGION=lax
MAX_CONCURRENT_SESSIONS=10
DEFAULT_SESSION_TIMEOUT=30000
ENABLE_CAPTCHA_SOLVING=true

# Claude/Anthropic Configuration  
ANTHROPIC_API_KEY=your_anthropic_api_key

# Security Settings
BLOCKED_DOMAINS=maliciousbook.com,evilvideos.com
```

### Action Settings
```python
class TwitterPostAction(BaseAction):
    # Performance settings
    timeout_seconds = 60
    estimated_duration_seconds = 30
    success_rate_threshold = 0.85
    
    # Categorization
    category = "social_media"
    tags = ["twitter", "x", "social", "posting"]
    
    # Authentication
    requires_auth = True
```

## Error Handling

### Action-Level Errors
- `ActionValidationError`: Parameter validation failures
- `ActionTimeoutError`: Execution timeout exceeded
- `ActionExecutionError`: General execution failures

### Recovery Mechanisms
- Automatic session cleanup on failure
- Screenshot capture for debugging
- Detailed error logging with context
- Graceful degradation for non-critical failures

### Example Error Response
```json
{
    "status": "failed",
    "message": "Failed to post tweet: Login failed",
    "error_code": "TWITTER_POST_ERROR", 
    "error_details": {
        "message": "Hello World!",
        "error_screenshot": "https://steel.run/screenshots/error_abc123.png",
        "session_id": "session_xyz789"
    },
    "execution_time_ms": 15420
}
```

## Testing

### Unit Tests
```bash
# Test Twitter actions
python -m pytest tests/test_actions/test_twitter.py -v

# Test Claude agent
python -m pytest tests/test_agent/test_executor.py -v

# Test base action framework
python -m pytest tests/test_actions/test_base.py -v
```

### Integration Tests
```python
# Example integration test
async def test_twitter_post_integration():
    action = TwitterPostAction()
    
    # Mock Steel and Anthropic APIs
    with patch('app.actions.base.Steel') as mock_steel, \
         patch('app.agent.executor.AsyncAnthropic') as mock_anthropic:
        
        result = await action.execute_safely(
            message="Test tweet",
            credentials={"username": "test", "password": "test"}
        )
        
        assert result["status"] == "success"
```

## Security Considerations

### Domain Blocking
- Automatic blocking of malicious domains
- URL validation before navigation
- Configurable blocked domain lists

### Credential Handling
- Credentials never logged or exposed
- Secure session configurations
- Encrypted credential storage (when implemented)

### Anti-Detection
- Humanized interaction patterns
- Stealth browser configurations
- Proxy rotation support
- Captcha solving integration

## Performance Optimization

### Session Reuse
- Connection pooling for Steel sessions
- Session warming for faster execution
- Concurrent session management

### Caching
- Screenshot caching for repeated tasks
- Action result caching where appropriate
- Metadata caching for fast discovery

### Monitoring
- Execution time tracking
- Success rate monitoring  
- Resource usage metrics
- Error rate analysis

## Future Enhancements

### Planned Features
- Session persistence across actions
- Advanced retry strategies
- Action chaining and workflows
- Real-time progress streaming
- Enhanced screenshot analysis

### Additional Actions
- Amazon product actions
- LinkedIn profile actions
- Gmail automation actions
- Generic web form actions

### Platform Integration
- Webhook support for notifications
- API rate limiting and throttling
- Action scheduling and queuing
- Multi-tenant session isolation

## Best Practices

### Action Development
1. **Atomic Operations**: Each action should be self-contained
2. **Idempotent**: Actions should be safe to retry
3. **Fail-Safe**: Graceful handling of all error conditions  
4. **Observable**: Comprehensive logging and evidence collection
5. **Testable**: Unit tests for all major code paths

### Security Guidelines
1. **Validate All Inputs**: Never trust user-provided data
2. **Sanitize URLs**: Check against blocked domain lists
3. **Secure Credentials**: Use encrypted storage and transmission
4. **Rate Limiting**: Respect website terms of service
5. **Privacy Conscious**: Minimize data collection and retention

### Performance Guidelines
1. **Resource Cleanup**: Always release sessions and resources
2. **Timeout Management**: Set appropriate timeouts for actions
3. **Concurrent Execution**: Use async/await patterns throughout
4. **Memory Efficiency**: Stream large responses when possible
5. **Error Recovery**: Implement exponential backoff for retries

This framework provides the foundation for reliable, scalable web automation using Steel.run's atomic actions approach combined with Claude's computer use capabilities.