# MCP Playwright Testing Plan for Steel.run

## Overview
This plan outlines how to test the Steel.run action execution system using MCP Playwright once it's enabled. The goal is to validate that the frontend properly displays action results and that the execution flow works correctly.

## Prerequisites
1. MCP Playwright server must be configured and enabled
2. Steel.run application running at http://100.126.153.59:8080/
3. Current implementation with real-time execution tracking system

## Test Scenarios

### 1. Frontend Display Validation
**Objective**: Verify that the homepage correctly shows action execution progress and results

**Steps using MCP Playwright**:
1. Navigate to http://100.126.153.59:8080/
2. Verify the new "Web Actions as a Service" messaging is displayed
3. Test the action input form with a screenshot request
4. Monitor the execution flow through browser developer tools
5. Validate that results are displayed in the UI

**Expected Behavior**:
- Action form submits successfully
- Progress indicators update in real-time
- Results section appears with screenshot or data
- No JavaScript errors in console

### 2. Steel SDK Integration Test
**Objective**: Validate that Steel SDK is properly executing actions

**Steps using MCP Playwright**:
1. Navigate to the application
2. Submit a screenshot action (e.g., "Take a screenshot of google.com")
3. Monitor network requests to `/api/v1/actions/execute`
4. Check status polling to `/api/v1/actions/executions/{run_id}/status`
5. Verify results retrieval from `/api/v1/actions/executions/{run_id}/results`

**Expected API Flow**:
```
POST /api/v1/actions/execute → 202 Accepted with run_id
GET /api/v1/actions/executions/{run_id}/status → queued/running/completed
GET /api/v1/actions/executions/{run_id}/results → actual results with screenshot
```

### 3. Real-time Progress Tracking
**Objective**: Ensure the execution tracker works correctly

**Test Cases**:
- **Successful Execution**: Action completes and shows results
- **Failed Execution**: Error handling and display
- **Multiple Concurrent Actions**: State isolation

**MCP Playwright Commands**:
```javascript
// Navigate to site
await page.goto('http://100.126.153.59:8080/');

// Fill and submit action
await page.fill('#action-input', 'Take a screenshot of google.com');
await page.click('button[type="submit"]');

// Wait for execution section to appear
await page.waitForSelector('#execution-section[style*="block"]');

// Monitor progress updates
const progressBar = page.locator('#progress-fill');
await expect(progressBar).toHaveCSS('width', /[1-9]\d*px/);

// Wait for completion
await page.waitForSelector('#execution-results[style*="block"]', { timeout: 30000 });

// Verify screenshot display
const screenshot = page.locator('#screenshot-image');
await expect(screenshot).toBeVisible();
await expect(screenshot).toHaveAttribute('src', /data:image/);
```

### 4. Error Handling Validation
**Objective**: Test error scenarios and recovery

**Test Cases**:
- Steel SDK connection failures
- Invalid action requests
- Network timeouts
- API error responses

### 5. Performance Testing
**Objective**: Validate system performance under load

**Metrics to Capture**:
- Time from submission to first progress update
- Total execution time for screenshot actions
- Memory usage during execution
- Frontend responsiveness during polling

## Implementation Notes

### Current System Architecture
- **Frontend**: Real-time polling for status and results
- **Backend**: Execution tracker with in-memory state management
- **Steel SDK**: Direct integration for browser automation
- **API Endpoints**: RESTful status and results retrieval

### Key Files Modified
- `/app/api/v1/actions.py` - Updated execution endpoints
- `/app/services/execution_tracker.py` - New execution state management
- `/app/frontend/static/app.js` - Updated polling logic (previous fixes)
- `/app/frontend/templates/index.html` - New "Web Actions as a Service" messaging

### Testing Commands (when MCP available)

```bash
# Basic functionality test
mcp playwright navigate http://100.126.153.59:8080/
mcp playwright screenshot landing-page.png
mcp playwright fill '#action-input' 'Take a screenshot of google.com'
mcp playwright click 'button[type="submit"]'
mcp playwright wait-for-selector '#execution-results'
mcp playwright screenshot action-complete.png

# Network monitoring test
mcp playwright network-monitor start
mcp playwright fill '#action-input' 'Take a screenshot of github.com'
mcp playwright click 'button[type="submit"]'
mcp playwright wait 10000
mcp playwright network-monitor stop
```

## Success Criteria
1. ✅ Action submission works without errors
2. ✅ Progress indicators update correctly
3. ✅ Results display with actual data (screenshot or extracted content)
4. ✅ Error states are handled gracefully
5. ✅ No console errors or broken functionality
6. ✅ API responses match expected format
7. ✅ Multiple concurrent actions work independently

## Debugging Checklist
If tests fail, check:
- [ ] Steel SDK API key configuration
- [ ] Network connectivity to Steel services
- [ ] Frontend polling interval and timeout settings
- [ ] Execution tracker memory management
- [ ] API endpoint response formats
- [ ] JavaScript console for errors
- [ ] Backend logs for Steel SDK errors

## Future Enhancements
1. Add WebSocket support for real-time updates
2. Implement action result caching
3. Add support for more action types beyond screenshots
4. Integrate with Steel's action reputation system
5. Add batch action execution capabilities

---
*This plan will be executed once MCP Playwright is enabled and configured.*