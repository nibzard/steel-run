# Steel.run Development TODO

## Style Guide & Development Principles

**Code Style:**
- Use uv for package management (10-100x faster than pip)
- Follow FastAPI + Pydantic patterns for all endpoints
- Use SQLAlchemy 2.0+ with async support
- Implement structured logging with structlog
- All async functions, no blocking I/O
- Type hints everywhere (Python 3.12+)
- Comprehensive error handling and validation

**Architecture:**
- Domain-driven design with atomic web functions
- Modular, self-contained components
- API-first approach with OpenAPI docs
- Secure credential storage with encryption
- Session lifecycle management (Create → Use → Release)
- Rate limiting and security best practices

---

## Backend API Development Agent Tasks

### Phase 1: Foundation & Database (Week 1)
- [ ] **Project Setup & Dependencies**
  - [ ] Initialize project with `uv init steel-run`
  - [ ] Add core dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `steel-sdk`, `anthropic`
  - [ ] Add development dependencies: `pytest`, `ruff`, `pytest-asyncio`, `httpx`
  - [ ] Configure `pyproject.toml` with tool settings (ruff, pytest)
  - [ ] Create `.env.example` with required environment variables
  - [ ] Set up Docker configuration with multi-stage build

- [ ] **Database Models & Schema**
  - [ ] Create `app/models/base.py` with SQLAlchemy base configuration
  - [ ] Implement `app/models/stored_action.py` - StoredAction data model
  - [ ] Implement `app/models/execution_run.py` - ExecutionRun tracking model
  - [ ] Implement `app/models/user.py` - User and API key models
  - [ ] Create `app/models/database.py` - async database connection setup
  - [ ] Initialize Alembic for database migrations
  - [ ] Create initial migration with all tables

- [ ] **Core API Structure**
  - [ ] Create `app/main.py` FastAPI application with middleware setup
  - [ ] Implement `app/core/config.py` using pydantic-settings
  - [ ] Create `app/core/security.py` with JWT authentication
  - [ ] Set up `app/core/database.py` with connection pooling
  - [ ] Add `app/api/dependencies.py` for FastAPI dependency injection
  - [ ] Create `app/api/__init__.py` with router registration

### Phase 2: Authentication & Basic API (Week 2)
- [ ] **Authentication System**
  - [ ] Implement JWT token generation and validation
  - [ ] Create API key generation and verification system
  - [ ] Add password hashing with bcrypt
  - [ ] Create user registration/login endpoints
  - [ ] Implement rate limiting middleware
  - [ ] Add CORS configuration for frontend

- [ ] **Stored Actions CRUD API**
  - [ ] Create `app/api/v1/stored_actions.py` router
  - [ ] POST `/api/actions/save` - Save user action configuration
  - [ ] GET `/api/actions/user` - List user's saved actions
  - [ ] PUT `/api/actions/{action_id}` - Update saved action
  - [ ] DELETE `/api/actions/{action_id}` - Delete saved action
  - [ ] Add Pydantic schemas in `app/schemas/stored_action.py`
  - [ ] Implement database service layer in `app/services/stored_actions.py`

- [ ] **External Service Integration API**
  - [ ] POST `/api/actions/{action_id}/run` - Execute stored action (for Zapier/n8n)
  - [ ] GET `/api/actions/{action_id}/status/{run_id}` - Check execution status
  - [ ] GET `/api/actions/{action_id}/results/{run_id}` - Get execution results
  - [ ] Implement asynchronous action execution with webhooks
  - [ ] Create execution tracking and result storage
  - [ ] Add proper error handling and status reporting

### Phase 3: Advanced Features (Week 3)
- [ ] **Credential Management**
  - [ ] Implement secure credential encryption using Fernet
  - [ ] Create credential CRUD operations
  - [ ] Add domain-based credential storage
  - [ ] Implement credential validation methods
  - [ ] Create secure credential retrieval for action execution

- [ ] **Monitoring & Observability**
  - [ ] Add structured logging throughout application
  - [ ] Implement Prometheus metrics collection
  - [ ] Create health check endpoints (`/health`, `/ready`)
  - [ ] Add request tracing and error tracking
  - [ ] Implement graceful shutdown handling

---

## Frontend Development Agent Tasks

### Phase 1: Core Views & UI (Week 3)
- [ ] **Landing Page Implementation**
  - [ ] Create `app/frontend/templates/index.html` with natural language input
  - [ ] Design clean, single-input interface for web actions
  - [ ] Add example buttons for common actions
  - [ ] Implement real-time execution status updates
  - [ ] Create result display area with screenshot support
  - [ ] Add credential prompt modal for authenticated actions

- [ ] **Dashboard - Action Gallery**
  - [ ] Create `app/frontend/templates/dashboard.html` with action grid
  - [ ] Display popular/featured atomic actions
  - [ ] Add action categories and filtering
  - [ ] Implement action search functionality
  - [ ] Show action descriptions, parameters, and auth requirements
  - [ ] Add one-click action execution from gallery

- [ ] **Code Editor - Action Preview**
  - [ ] Create `app/frontend/templates/editor.html` with code viewer
  - [ ] Implement syntax highlighting for Python code
  - [ ] Add read-only mode for built-in actions
  - [ ] Show action parameters and return values
  - [ ] Display action execution history and logs
  - [ ] Add code copying functionality

### Phase 2: User Actions Management (Week 4)
- [ ] **My Actions Page**
  - [ ] Create `app/frontend/templates/my_actions.html`
  - [ ] List user's saved actions with management controls
  - [ ] Add action editing and configuration interface
  - [ ] Show execution history and statistics
  - [ ] Implement action sharing and export
  - [ ] Add webhook URL configuration

- [ ] **Frontend JavaScript Application**
  - [ ] Create `app/frontend/static/app.js` with modern ES6+
  - [ ] Implement API client for all backend endpoints
  - [ ] Add real-time updates using WebSockets or Server-Sent Events
  - [ ] Create credential management interface
  - [ ] Add error handling and user feedback
  - [ ] Implement local storage for user preferences

- [ ] **Responsive Design & UX**
  - [ ] Create `app/frontend/static/style.css` with modern CSS
  - [ ] Implement responsive design for mobile/tablet
  - [ ] Add loading states and progress indicators
  - [ ] Create consistent component library
  - [ ] Add keyboard shortcuts and accessibility
  - [ ] Implement dark/light mode toggle

---

## Steel Integration Specialist Tasks

### Phase 1: Steel SDK Integration (Week 1)
- [ ] **BaseAction Framework**
  - [ ] Create `app/actions/base.py` with abstract BaseAction class
  - [ ] Implement session lifecycle management (create/use/release)
  - [ ] Add parameter validation and type checking
  - [ ] Create screenshot capture functionality
  - [ ] Implement error handling and recovery mechanisms
  - [ ] Add execution timeout and resource management

- [ ] **Claude Agent Integration**
  - [ ] Create `app/agent/executor.py` for Claude + Steel integration
  - [ ] Implement browser session management with Steel WebDriver
  - [ ] Add task execution with natural language instructions
  - [ ] Create structured result parsing and validation
  - [ ] Implement action completion detection
  - [ ] Add screenshot and evidence collection

### Phase 2: Core Actions Implementation (Week 2)
- [ ] **Twitter Actions**
  - [ ] Implement `app/actions/twitter.py` with TwitterPostAction
  - [ ] Add login flow with credential management
  - [ ] Create tweet composition and posting logic
  - [ ] Implement tweet verification and screenshot capture
  - [ ] Add TwitterReplyAction for responding to tweets
  - [ ] Create error handling for rate limits and blocks

- [ ] **Amazon Actions**
  - [ ] Implement `app/actions/amazon.py` with AmazonPriceCheckAction
  - [ ] Add product search and result extraction
  - [ ] Create price monitoring and comparison features
  - [ ] Implement inventory status checking
  - [ ] Add product detail extraction (reviews, ratings, specs)
  - [ ] Create wishlist and cart management actions

- [ ] **Website Actions**
  - [ ] Implement `app/actions/website.py` with screenshot/scraping actions
  - [ ] Add generic website screenshot capture
  - [ ] Create HTML content extraction and cleaning
  - [ ] Implement form filling and submission actions
  - [ ] Add PDF generation from web pages
  - [ ] Create generic data extraction patterns

### Phase 3: Advanced Automation (Week 3)
- [ ] **LinkedIn Actions**
  - [ ] Implement profile data extraction
  - [ ] Add connection request automation
  - [ ] Create job search and application tracking
  - [ ] Implement post creation and engagement
  - [ ] Add company research and data collection

- [ ] **Gmail Actions**
  - [ ] Create email reading and parsing
  - [ ] Implement email composition and sending
  - [ ] Add attachment handling and download
  - [ ] Create email filtering and organization
  - [ ] Implement unread count and notification actions

- [ ] **Action Registry & Discovery**
  - [ ] Create dynamic action registration system
  - [ ] Implement action metadata and documentation
  - [ ] Add action versioning and update mechanisms
  - [ ] Create action performance monitoring
  - [ ] Implement action reputation and reliability scoring

---

## Natural Language Processing Agent Tasks

### Phase 1: Parser Implementation (Week 2)
- [ ] **Claude-based Action Parser**
  - [ ] Create `app/agent/parser.py` with Anthropic integration
  - [ ] Implement natural language to action mapping
  - [ ] Add parameter extraction from text input
  - [ ] Create confidence scoring for parsed actions
  - [ ] Implement fallback and error handling
  - [ ] Add context-aware parsing improvements

- [ ] **Action Recognition**
  - [ ] Build action description templates for Claude
  - [ ] Create training examples for common patterns
  - [ ] Implement multi-action parsing for complex requests
  - [ ] Add parameter validation and type conversion
  - [ ] Create disambiguation for ambiguous inputs
  - [ ] Implement learning from user corrections

### Phase 2: Advanced NLP Features (Week 4)
- [ ] **Smart Action Suggestions**
  - [ ] Implement action recommendation engine
  - [ ] Add user behavior learning and preferences
  - [ ] Create contextual action suggestions
  - [ ] Implement auto-completion for common patterns
  - [ ] Add personalized action shortcuts

- [ ] **Multi-step Action Parsing**
  - [ ] Parse complex multi-action workflows
  - [ ] Create action chaining and dependencies
  - [ ] Implement conditional action execution
  - [ ] Add workflow templates and patterns
  - [ ] Create action sequence optimization

---

## General Purpose Agent Tasks

### Phase 1: Testing & Quality Assurance (Week 4)
- [ ] **Test Suite Development**
  - [ ] Create `tests/conftest.py` with test fixtures
  - [ ] Implement `tests/test_api/` for all API endpoints
  - [ ] Add `tests/test_actions/` for action execution tests
  - [ ] Create `tests/test_models/` for database model tests
  - [ ] Implement integration tests for Steel SDK
  - [ ] Add performance and load testing

- [ ] **Code Quality & Linting**
  - [ ] Configure Ruff with project-specific rules
  - [ ] Set up pre-commit hooks for code formatting
  - [ ] Add type checking with mypy
  - [ ] Create comprehensive docstrings
  - [ ] Implement security scanning with bandit
  - [ ] Add dependency vulnerability scanning

### Phase 2: Deployment & Infrastructure (Week 5)
- [ ] **Docker & Container Setup**
  - [ ] Create production-ready Dockerfile
  - [ ] Set up docker-compose for local development
  - [ ] Add health checks and proper signal handling
  - [ ] Configure environment variable management
  - [ ] Implement proper logging and log rotation

- [ ] **CI/CD Pipeline**
  - [ ] Create `.github/workflows/ci.yml` for automated testing
  - [ ] Add automated deployment pipeline
  - [ ] Configure environment-specific deployments
  - [ ] Implement security scanning in CI
  - [ ] Add performance regression testing
  - [ ] Create automated database migrations

- [ ] **Documentation & Examples**
  - [ ] Update README.md with setup instructions
  - [ ] Create API documentation with examples
  - [ ] Add Zapier/n8n integration guides
  - [ ] Create developer getting-started guide
  - [ ] Document action development patterns
  - [ ] Add troubleshooting and FAQ sections

### Phase 3: Security & Production Readiness (Week 5)
- [ ] **Security Implementation**
  - [ ] Implement proper HTTPS and TLS configuration
  - [ ] Add input sanitization and validation
  - [ ] Create API rate limiting and abuse protection
  - [ ] Implement secure session management
  - [ ] Add secrets management and rotation
  - [ ] Configure security headers and CORS

- [ ] **Monitoring & Alerting**
  - [ ] Set up application metrics collection
  - [ ] Create performance monitoring dashboards
  - [ ] Implement error tracking and alerting
  - [ ] Add uptime monitoring and health checks
  - [ ] Create backup and disaster recovery plans
  - [ ] Configure log aggregation and analysis

---

## External Integration Examples (Week 5)

### Zapier Integration Templates
- [ ] Create webhook action templates
- [ ] Add trigger configuration examples
- [ ] Document authentication setup
- [ ] Create common workflow patterns

### n8n Integration Examples
- [ ] Build n8n node configurations
- [ ] Create workflow templates
- [ ] Add error handling patterns
- [ ] Document parameter passing

### Make.com Integration
- [ ] Create module configurations
- [ ] Add scenario templates
- [ ] Document webhook setup
- [ ] Create testing procedures

---

## Success Metrics & Validation

### Performance Targets
- [ ] Twitter post execution: <10 seconds average
- [ ] Action success rate: 90%+ for well-defined actions
- [ ] API response time: <200ms for non-execution endpoints
- [ ] Support 10+ concurrent executions
- [ ] Database query performance: <50ms average

### Feature Completeness Validation
- [ ] ✅ Natural language input parsing
- [ ] ✅ At least 5 working atomic actions
- [ ] ✅ Dashboard with action gallery
- [ ] ✅ Code preview/editor functionality
- [ ] ✅ Secure credential storage
- [ ] ✅ Screenshot capture and display
- [ ] ✅ Error handling and recovery
- [ ] ✅ External API integration (Zapier/n8n ready)

### Security & Production Checklist
- [ ] HTTPS enforced in production
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] Rate limiting implemented
- [ ] Secrets properly managed
- [ ] Error handling doesn't leak sensitive info
- [ ] Logging configured for production
- [ ] Database backups automated
- [ ] Monitoring and alerting active

---

## Notes for Agents

**Backend API Agent:** Focus on creating robust, well-documented APIs that can handle external service integrations. Priority on security, validation, and proper async patterns.

**Frontend Agent:** Create intuitive UX that makes web automation feel simple. Focus on real-time feedback and clear error messaging.

**Steel Integration Agent:** Master the Steel SDK patterns and create reliable atomic actions. Priority on session management and error recovery.

**General Purpose Agent:** Ensure production readiness with comprehensive testing, documentation, and monitoring. Focus on maintainability and scalability.

Remember: Each atomic action should be self-contained, reliable, and provide clear success/failure feedback with screenshots where applicable.