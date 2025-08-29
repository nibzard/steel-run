/**
 * Steel.run Frontend Application
 * Modern ES6+ JavaScript for atomic web functions platform
 */

class SteelApp {
    constructor() {
        this.config = {
            apiBaseUrl: '/api/v1',
            wsBaseUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`,
            pollInterval: 2000,
            maxRetries: 3,
            notificationTimeout: 5000,
            websocketReconnectDelay: 3000
        };
        
        this.state = {
            currentUser: null,
            isAuthenticated: false,
            currentExecution: null,
            actions: [],
            categories: [],
            monacoEditor: null,
            credentials: [],
            templates: [],
            userPreferences: {
                theme: 'light',
                notifications: true,
                autoSave: true,
                keyboardShortcuts: true
            },
            websocket: null,
            isWebSocketConnected: false,
            draggedElement: null,
            bulkSelectedItems: new Set(),
            executionHistory: [],
            performanceMetrics: {}
        };
        
        this.apiClient = new SteelAPIClient(this.config.apiBaseUrl);
        this.eventManager = new EventManager();
        this.storage = new LocalStorage();
        this.websocketManager = new WebSocketManager(this);
        this.credentialManager = new CredentialManager(this);
        this.templateManager = new TemplateManager(this);
        this.keyboardManager = new KeyboardManager(this);
        this.notificationManager = new NotificationManager(this);
        
        this.init();
    }

    async init() {
        try {
            // Check authentication status
            await this.checkAuthStatus();
            
            // Load user preferences first
            this.loadUserPreferences();
            
            // Setup global event listeners
            this.setupGlobalEvents();
            
            // Initialize advanced features
            await this.initializeAdvancedFeatures();
            
            // Setup keyboard shortcuts
            this.keyboardManager.initialize();
            
            // Initialize WebSocket connection if authenticated
            if (this.state.isAuthenticated) {
                await this.websocketManager.connect();
            }
            
            console.log('Steel.run app initialized with advanced features');
        } catch (error) {
            console.error('Failed to initialize Steel app:', error);
            this.notificationManager.showError('Failed to initialize application');
        }
    }
    
    async initializeAdvancedFeatures() {
        // Initialize service worker for offline functionality
        this.initializeServiceWorker();
        
        // Setup theme system
        this.initializeThemeSystem();
        
        // Setup drag and drop
        this.initializeDragAndDrop();
        
        // Load performance metrics
        this.loadPerformanceMetrics();
    }
    
    initializeServiceWorker() {
        if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }
    }
    
    initializeThemeSystem() {
        const theme = this.state.userPreferences.theme;
        document.documentElement.setAttribute('data-theme', theme);
        
        // Add theme toggle button event listener
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }
    
    initializeDragAndDrop() {
        // Enable drag and drop for action cards
        document.addEventListener('dragstart', this.handleDragStart.bind(this));
        document.addEventListener('dragover', this.handleDragOver.bind(this));
        document.addEventListener('drop', this.handleDrop.bind(this));
    }
    
    handleDragStart(e) {
        // Store the data being dragged
        if (e.target.classList.contains('draggable')) {
            e.dataTransfer.setData('text/plain', e.target.dataset.action || e.target.textContent);
            e.dataTransfer.effectAllowed = 'move';
        }
    }
    
    handleDragOver(e) {
        // Allow drop by preventing default behavior
        if (e.target.classList.contains('drop-zone')) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        }
    }
    
    handleDrop(e) {
        // Handle the drop event
        if (e.target.classList.contains('drop-zone')) {
            e.preventDefault();
            const data = e.dataTransfer.getData('text/plain');
            
            // Add visual feedback or perform action with dropped data
            if (data) {
                console.log('Dropped:', data);
                // You can implement specific drop behavior here
            }
        }
    }
    
    loadPerformanceMetrics() {
        this.state.performanceMetrics = this.storage.get('performance_metrics') || {
            actionExecutions: 0,
            averageExecutionTime: 0,
            successRate: 0,
            lastActivity: null
        };
    }

    async checkAuthStatus() {
        try {
            // Check if running in dev mode with auth disabled
            const devStatus = await this.apiClient.getDevStatus();
            console.log('Dev status response:', devStatus);
            this.state.devMode = devStatus;
            
            if (devStatus && devStatus.auth_disabled) {
                // In dev mode with auth disabled, automatically authenticate
                this.state.currentUser = {
                    email: devStatus.dev_user_email,
                    username: 'developer',
                    full_name: 'Development User',
                    id: 'dev-user-id'
                };
                this.state.isAuthenticated = true;
                this.updateAuthUI(true);
                return;
            }
        } catch (error) {
            console.error('Failed to fetch dev status:', error);
            
            // Fallback: Check if we're in development based on hostname
            const isDevelopment = window.location.hostname === 'localhost' || 
                                  window.location.hostname === '127.0.0.1' ||
                                  window.location.hostname.includes('100.'); // Tailscale IPs
            
            if (isDevelopment) {
                console.log('Detected development environment, enabling dev mode auth bypass');
                this.state.devMode = { 
                    auth_disabled: true, 
                    dev_user_email: 'dev@steel.run',
                    is_development: true 
                };
                this.state.currentUser = {
                    email: 'dev@steel.run',
                    username: 'developer',
                    full_name: 'Development User',
                    id: 'dev-user-id'
                };
                this.state.isAuthenticated = true;
                this.updateAuthUI(true);
                return;
            }
        }
        
        const token = this.storage.get('auth_token');
        if (token) {
            try {
                const user = await this.apiClient.getCurrentUser();
                this.state.currentUser = user;
                this.state.isAuthenticated = true;
                this.updateAuthUI(true);
            } catch (error) {
                console.log('Token invalid, clearing storage');
                this.storage.remove('auth_token');
                this.updateAuthUI(false);
            }
        } else {
            this.updateAuthUI(false);
        }
    }

    setupGlobalEvents() {
        // Navigation toggle (mobile)
        const navToggle = document.getElementById('nav-toggle');
        const navMenu = document.querySelector('.nav-menu');
        
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', () => {
                navMenu.classList.toggle('active');
            });
        }

        // Auth button
        const authButton = document.getElementById('auth-button');
        if (authButton) {
            authButton.addEventListener('click', () => {
                console.log('Auth button clicked. isAuthenticated:', this.state.isAuthenticated, 'devMode:', this.state.devMode);
                if (this.state.isAuthenticated) {
                    this.logout();
                } else {
                    this.showAuthModal();
                }
            });
        }

        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case '/':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'Enter':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.executeCurrentAction();
                        }
                        break;
                }
            }
        });
    }

    updateAuthUI(isAuthenticated) {
        const authButton = document.getElementById('auth-button');
        if (authButton) {
            authButton.textContent = isAuthenticated ? 'Sign Out' : 'Sign In';
            authButton.className = isAuthenticated ? 'btn btn-secondary' : 'btn btn-primary';
        }
        
        // Add dev mode indicator if auth is disabled
        if (this.state.devMode && this.state.devMode.auth_disabled) {
            this.showDevModeIndicator();
        }
    }
    
    showDevModeIndicator() {
        // Remove existing dev mode indicator
        const existingIndicator = document.getElementById('dev-mode-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Create dev mode banner
        const devBanner = document.createElement('div');
        devBanner.id = 'dev-mode-indicator';
        devBanner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(90deg, #ff6b6b, #ffd93d);
            color: #333;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            z-index: 9999;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        `;
        devBanner.innerHTML = '🚧 DEVELOPMENT MODE - Authentication Disabled (dev@steel.run) 🚧';
        
        document.body.insertBefore(devBanner, document.body.firstChild);
        
        // Adjust body padding to account for banner
        document.body.style.paddingTop = '40px';
        
        // Also add indicator to navigation
        const navBrand = document.querySelector('.brand-text');
        if (navBrand && !navBrand.querySelector('.dev-badge')) {
            const devBadge = document.createElement('span');
            devBadge.className = 'dev-badge';
            devBadge.style.cssText = `
                background: #ff6b6b;
                color: white;
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 12px;
                margin-left: 8px;
                font-weight: bold;
            `;
            devBadge.textContent = 'DEV';
            navBrand.appendChild(devBadge);
        }
    }

    loadUserPreferences() {
        const theme = this.storage.get('theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    }

    focusSearch() {
        const searchInput = document.getElementById('action-search') || 
                           document.getElementById('action-input');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // === LANDING PAGE === //
    initializeLandingPage() {
        console.log('Initializing landing page');
        
        this.setupActionInput();
        this.setupExampleButtons();
        this.setupCredentialModal();
    }

    setupActionInput() {
        const form = document.getElementById('action-form');
        const input = document.getElementById('action-input');
        const charCount = document.getElementById('char-count');
        const executeBtn = document.getElementById('execute-button');

        if (!form || !input) return;

        // Character count
        input.addEventListener('input', () => {
            if (charCount) {
                charCount.textContent = input.value.length;
            }
            
            // Enable/disable execute button
            if (executeBtn) {
                executeBtn.disabled = input.value.trim().length < 10;
            }
        });

        // Form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const actionText = input.value.trim();
            
            if (actionText.length < 10) {
                this.showError('Please provide a more detailed action description (at least 10 characters).');
                return;
            }

            await this.executeNaturalLanguageAction(actionText);
        });
    }

    setupExampleButtons() {
        const exampleButtons = document.querySelectorAll('.example-btn');
        const actionInput = document.getElementById('action-input');

        exampleButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const actionText = btn.getAttribute('data-action');
                if (actionInput) {
                    actionInput.value = actionText;
                    actionInput.dispatchEvent(new Event('input'));
                }
                
                // Scroll to input
                actionInput.scrollIntoView({ behavior: 'smooth' });
                actionInput.focus();
            });
        });
    }

    setupCredentialModal() {
        const modal = document.getElementById('credential-modal');
        const closeBtn = document.getElementById('close-credential-modal');
        const cancelBtn = document.getElementById('cancel-credentials');
        const form = document.getElementById('credential-form');

        if (!modal) return;

        [closeBtn, cancelBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    modal.style.display = 'none';
                    this.state.currentExecution = null;
                });
            }
        });

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const credentials = {
                    website: document.getElementById('website-select').value,
                    username: document.getElementById('credential-username').value,
                    password: document.getElementById('credential-password').value,
                    saveCredentials: document.getElementById('save-credentials').checked
                };

                modal.style.display = 'none';
                await this.continueExecutionWithCredentials(credentials);
            });
        }

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
                this.state.currentExecution = null;
            }
        });
    }

    async executeNaturalLanguageAction(actionText) {
        try {
            this.showExecutionStatus();
            this.updateExecutionStatus('preparing', 'Analyzing your request...', 10);

            // First, analyze the action to determine if we need credentials
            const analysisResponse = await this.apiClient.analyzeAction(actionText);
            
            if (analysisResponse.requires_auth && !this.state.isAuthenticated) {
                this.promptForCredentials(analysisResponse);
                return;
            }

            // Execute the action
            await this.executeAction(actionText);
            
        } catch (error) {
            console.error('Action execution failed:', error);
            this.showExecutionError(error);
        }
    }

    async executeAction(actionText, credentials = null) {
        try {
            this.updateExecutionStatus('executing', 'Executing action...', 50);

            const payload = { 
                input: actionText,
                timeout_seconds: 60
            };

            if (credentials) {
                payload.credentials = credentials;
            }

            const response = await this.apiClient.executeAction(payload);
            this.state.currentExecution = response;

            // Start polling for results
            await this.pollExecutionStatus(response.run_id);
            
        } catch (error) {
            console.error('Action execution error:', error);
            this.showExecutionError(error);
        }
    }

    async pollExecutionStatus(runId) {
        const maxAttempts = 60; // 2 minutes with 2-second intervals
        let attempts = 0;

        const poll = async () => {
            try {
                attempts++;
                const status = await this.apiClient.getExecutionStatus(runId);
                
                this.updateExecutionProgress(status);

                if (status.status === 'completed') {
                    try {
                        const results = await this.apiClient.getExecutionResults(runId);
                        // Only show results if we got actual results (not 202)
                        if (results && results.status !== 'in_progress') {
                            this.showExecutionResults(results);
                            return;
                        }
                        // If still in progress, continue polling
                    } catch (error) {
                        console.warn('Results not ready yet:', error);
                    }
                } else if (status.status === 'failed') {
                    this.showExecutionError(new Error(status.error_message || 'Action failed'));
                    return;
                } else if (attempts >= maxAttempts) {
                    this.showExecutionError(new Error('Action timed out'));
                    return;
                }

                // Continue polling
                setTimeout(poll, this.config.pollInterval);
                
            } catch (error) {
                console.error('Polling error:', error);
                if (attempts < maxAttempts) {
                    setTimeout(poll, this.config.pollInterval);
                } else {
                    this.showExecutionError(error);
                }
            }
        };

        poll();
    }

    showExecutionStatus() {
        console.log('showExecutionStatus called');
        const section = document.getElementById('execution-section');
        console.log('Execution section exists:', !!section);
        if (section) {
            console.log('Setting execution section display to block');
            section.style.display = 'block';
            section.scrollIntoView({ behavior: 'smooth' });
            console.log('Execution section display after setting:', section.style.display);
        } else {
            console.error('Execution section not found!');
        }
    }

    updateExecutionStatus(phase, message, progress = 0) {
        const statusIcon = document.getElementById('status-icon');
        const statusTitle = document.getElementById('status-title');
        const statusMessage = document.getElementById('status-message');
        const progressFill = document.getElementById('progress-fill');

        if (statusIcon) {
            const icons = {
                preparing: '⚙️',
                executing: '🚀',
                completed: '✅',
                failed: '❌'
            };
            statusIcon.textContent = icons[phase] || '⏳';
        }

        if (statusTitle) {
            const titles = {
                preparing: 'Preparing Action...',
                executing: 'Executing Action...',
                completed: 'Action Completed!',
                failed: 'Action Failed'
            };
            statusTitle.textContent = titles[phase] || 'Processing...';
        }

        if (statusMessage) {
            statusMessage.textContent = message;
        }

        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }

        // Update elapsed time
        this.updateElapsedTime();
    }

    updateExecutionProgress(status) {
        const progress = status.progress || 
                        (status.status === 'running' ? 75 : 
                         status.status === 'completed' ? 100 : 50);
        
        this.updateExecutionStatus(status.status, status.error_message || 'Processing...', progress);
        
        // Show action details if available
        if (status.action_details) {
            this.showActionDetails(status.action_details);
        }
    }

    showActionDetails(details) {
        const detailsSection = document.getElementById('action-details');
        const actionType = document.getElementById('action-type');
        const actionWebsite = document.getElementById('action-website');
        const estimatedTime = document.getElementById('estimated-time');

        if (detailsSection) {
            detailsSection.style.display = 'block';
        }

        if (actionType) actionType.textContent = details.type || '-';
        if (actionWebsite) actionWebsite.textContent = details.website || '-';
        if (estimatedTime) estimatedTime.textContent = details.estimated_time || '-';
    }

    showExecutionResults(results) {
        console.log('showExecutionResults called with:', results);
        this.updateExecutionStatus('completed', 'Action completed successfully!', 100);
        
        // Ensure the main execution section is visible first
        const executionSection = document.getElementById('execution-section');
        if (executionSection) {
            console.log('Making sure execution section is visible');
            executionSection.style.display = 'block';
        }
        
        const resultsSection = document.getElementById('execution-results');
        console.log('Results section exists:', !!resultsSection);
        if (resultsSection) {
            console.log('Setting results section display to block');
            resultsSection.style.display = 'block';
        } else {
            console.error('Results section not found!');
        }

        // Show screenshot if available
        if (results.screenshot_url) {
            this.showScreenshot(results.screenshot_url);
        }

        // Show data results if available
        if (results.result_data) {
            this.showDataResults(results.result_data);
        }

        // Setup result actions
        this.setupResultActions(results);
    }

    showScreenshot(screenshotUrl) {
        const container = document.getElementById('screenshot-container');
        const image = document.getElementById('screenshot-image');
        const downloadBtn = document.getElementById('download-screenshot');

        if (container && image) {
            container.style.display = 'block';
            image.src = screenshotUrl;
            image.alt = 'Action screenshot';
        }

        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadFile(screenshotUrl, 'action-screenshot.png');
            });
        }
    }

    showDataResults(data) {
        const container = document.getElementById('data-results');
        const content = document.getElementById('results-data-content');

        if (container && content) {
            container.style.display = 'block';
            content.textContent = JSON.stringify(data, null, 2);
        }
    }

    setupResultActions(results) {
        const copyBtn = document.getElementById('copy-results');
        const saveBtn = document.getElementById('save-action');

        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                this.copyToClipboard(JSON.stringify(results, null, 2));
                this.showSuccess('Results copied to clipboard!');
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.showSaveActionModal(results);
            });
        }
    }

    showExecutionError(error) {
        this.updateExecutionStatus('failed', error.message, 0);
        
        const errorSection = document.getElementById('error-results');
        const errorType = document.getElementById('error-type');
        const errorDescription = document.getElementById('error-description');

        if (errorSection) {
            errorSection.style.display = 'block';
        }

        if (errorType) {
            errorType.textContent = error.name || 'ExecutionError';
        }

        if (errorDescription) {
            errorDescription.textContent = error.message || 'An unexpected error occurred.';
        }
    }

    promptForCredentials(analysisResponse) {
        const modal = document.getElementById('credential-modal');
        const websiteSelect = document.getElementById('website-select');

        if (modal) {
            modal.style.display = 'flex';
        }

        // Pre-select website if detected
        if (websiteSelect && analysisResponse.detected_website) {
            websiteSelect.value = analysisResponse.detected_website;
        }
    }

    async continueExecutionWithCredentials(credentials) {
        if (this.state.currentExecution) {
            await this.executeAction(this.state.currentExecution.original_input, credentials);
        }
    }

    updateElapsedTime() {
        const timeElement = document.getElementById('elapsed-time');
        if (!timeElement) return;

        if (!this.state.executionStartTime) {
            this.state.executionStartTime = Date.now();
        }

        const updateTime = () => {
            const elapsed = Math.floor((Date.now() - this.state.executionStartTime) / 1000);
            timeElement.textContent = `${elapsed}s`;
            
            if (this.state.currentExecution) {
                setTimeout(updateTime, 1000);
            }
        };

        updateTime();
    }

    // === DASHBOARD PAGE === //
    async initializeDashboard() {
        console.log('Initializing dashboard');
        
        this.setupSearch();
        this.setupFilters();
        this.setupActionModal();
        this.setupExecutionModal();
        
        await this.loadActions();
        await this.loadFeaturedActions();
    }

    setupSearch() {
        const searchInput = document.getElementById('action-search');
        const searchButton = document.getElementById('search-button');

        if (!searchInput) return;

        let searchTimeout;

        const performSearch = () => {
            const query = searchInput.value.trim();
            this.searchActions(query);
        };

        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(performSearch, 300);
        });

        if (searchButton) {
            searchButton.addEventListener('click', performSearch);
        }

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    setupFilters() {
        const filterButtons = document.querySelectorAll('.filter-btn');
        const sortSelect = document.getElementById('sort-select');

        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active state
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Filter actions
                const category = btn.getAttribute('data-category');
                this.filterActions(category);
            });
        });

        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                this.sortActions(sortSelect.value);
            });
        }
    }

    setupActionModal() {
        const modal = document.getElementById('action-modal');
        const closeBtn = document.getElementById('close-action-modal');
        const previewBtn = document.getElementById('preview-action');
        const form = document.getElementById('action-parameters-form');

        if (!modal) return;

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        if (previewBtn) {
            previewBtn.addEventListener('click', () => {
                const actionId = modal.getAttribute('data-action-id');
                window.location.href = `/editor?action=${actionId}`;
            });
        }

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const actionId = modal.getAttribute('data-action-id');
                const formData = new FormData(form);
                const parameters = Object.fromEntries(formData.entries());
                
                modal.style.display = 'none';
                await this.executeStoredAction(actionId, parameters);
            });
        }

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    setupExecutionModal() {
        const modal = document.getElementById('execution-modal');
        const closeBtn = document.getElementById('close-execution-modal');
        const closeExecutionBtn = document.getElementById('close-execution');

        if (!modal) return;

        [closeBtn, closeExecutionBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    modal.style.display = 'none';
                    this.state.currentExecution = null;
                });
            }
        });

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
                this.state.currentExecution = null;
            }
        });
    }

    async loadActions() {
        try {
            this.showActionsLoading(true);
            
            const response = await this.apiClient.getActions();
            this.state.actions = response.actions || [];
            this.state.categories = response.categories || [];
            
            this.renderActions(this.state.actions);
            this.showActionsLoading(false);
            
        } catch (error) {
            console.error('Failed to load actions:', error);
            this.showActionsError();
        }
    }

    async loadFeaturedActions() {
        try {
            const featuredActions = await this.apiClient.getFeaturedActions();
            this.renderFeaturedActions(featuredActions);
        } catch (error) {
            console.error('Failed to load featured actions:', error);
        }
    }

    showActionsLoading(show) {
        const loading = document.getElementById('actions-loading');
        const grid = document.getElementById('actions-grid');
        const empty = document.getElementById('actions-empty');

        if (loading) loading.style.display = show ? 'flex' : 'none';
        if (grid) grid.style.display = show ? 'none' : 'grid';
        if (empty) empty.style.display = 'none';
    }

    showActionsError() {
        const loading = document.getElementById('actions-loading');
        const grid = document.getElementById('actions-grid');
        const empty = document.getElementById('actions-empty');

        if (loading) loading.style.display = 'none';
        if (grid) grid.style.display = 'none';
        if (empty) {
            empty.style.display = 'block';
            empty.querySelector('h3').textContent = 'Failed to load actions';
            empty.querySelector('p').textContent = 'Please try refreshing the page.';
        }
    }

    renderActions(actions) {
        const grid = document.getElementById('actions-grid');
        const empty = document.getElementById('actions-empty');

        if (!grid) return;

        if (actions.length === 0) {
            grid.style.display = 'none';
            if (empty) empty.style.display = 'block';
            return;
        }

        grid.style.display = 'grid';
        if (empty) empty.style.display = 'none';

        grid.innerHTML = '';
        
        actions.forEach(action => {
            const card = this.createActionCard(action);
            grid.appendChild(card);
        });
    }

    createActionCard(action) {
        const template = document.getElementById('action-card-template');
        if (!template) return this.createActionCardFallback(action);

        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.action-card');
        
        cardElement.setAttribute('data-action-id', action.id);
        
        // Set icon
        const icon = card.querySelector('.action-icon');
        icon.textContent = this.getActionIcon(action.category);
        
        // Set title and category
        card.querySelector('.action-title').textContent = action.name;
        card.querySelector('.action-category').textContent = action.category.replace('_', ' ').toUpperCase();
        
        // Set description
        card.querySelector('.action-description').textContent = action.description;
        
        // Set tags
        const tagsContainer = card.querySelector('.action-tags');
        tagsContainer.innerHTML = '';
        action.tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.textContent = tag;
            tagsContainer.appendChild(tagElement);
        });
        
        // Set stats
        card.querySelector('.success-rate').textContent = `${Math.round(action.success_rate * 100)}% success`;
        card.querySelector('.duration').textContent = `~${Math.round(action.avg_duration / 1000)}s`;
        
        // Show auth required if needed
        const authStat = card.querySelector('.auth-required');
        if (action.requires_auth) {
            authStat.style.display = 'flex';
        }
        
        // Setup event listeners
        const detailsBtn = card.querySelector('.action-details-btn');
        const executeBtn = card.querySelector('.action-execute-btn');
        
        detailsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showActionDetails(action);
        });
        
        executeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.quickExecuteAction(action);
        });
        
        // Card click for details
        cardElement.addEventListener('click', () => {
            this.showActionDetails(action);
        });
        
        return card;
    }

    createActionCardFallback(action) {
        const card = document.createElement('div');
        card.className = 'action-card';
        card.setAttribute('data-action-id', action.id);
        
        card.innerHTML = `
            <div class="action-card-header">
                <div class="action-icon">${this.getActionIcon(action.category)}</div>
                <div class="action-title-group">
                    <h3 class="action-title">${action.name}</h3>
                    <p class="action-category">${action.category.replace('_', ' ').toUpperCase()}</p>
                </div>
            </div>
            <div class="action-card-body">
                <p class="action-description">${action.description}</p>
                <div class="action-tags">
                    ${action.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="action-stats">
                    <div class="stat">
                        <span class="stat-icon">✓</span>
                        <span class="stat-text">${Math.round(action.success_rate * 100)}% success</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">⏱</span>
                        <span class="stat-text">~${Math.round(action.avg_duration / 1000)}s</span>
                    </div>
                    ${action.requires_auth ? '<div class="stat"><span class="stat-icon">🔒</span><span class="stat-text">Auth Required</span></div>' : ''}
                </div>
            </div>
            <div class="action-card-footer">
                <button class="btn btn-secondary btn-small">Details</button>
                <button class="btn btn-primary btn-small">Execute</button>
            </div>
        `;
        
        return card;
    }

    getActionIcon(category) {
        const icons = {
            'social_media': '📱',
            'web_scraping': '🕷️',
            'forms': '📝',
            'screenshots': '📸',
            'automation': '🤖',
            'default': '⚡'
        };
        return icons[category] || icons.default;
    }

    renderFeaturedActions(actions) {
        const grid = document.getElementById('featured-grid');
        if (!grid || !actions.length) return;

        grid.innerHTML = '';
        
        actions.slice(0, 6).forEach(action => {
            const card = this.createActionCard(action);
            grid.appendChild(card);
        });
    }

    async searchActions(query) {
        if (!query) {
            this.renderActions(this.state.actions);
            return;
        }

        try {
            const results = await this.apiClient.searchActions(query);
            this.renderActions(results);
        } catch (error) {
            console.error('Search failed:', error);
            // Fallback to client-side search
            const filteredActions = this.state.actions.filter(action => 
                action.name.toLowerCase().includes(query.toLowerCase()) ||
                action.description.toLowerCase().includes(query.toLowerCase()) ||
                action.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
            );
            this.renderActions(filteredActions);
        }
    }

    filterActions(category) {
        if (category === 'all') {
            this.renderActions(this.state.actions);
            return;
        }

        const filteredActions = this.state.actions.filter(action => 
            action.category === category
        );
        this.renderActions(filteredActions);
    }

    sortActions(sortBy) {
        let sortedActions = [...this.state.actions];

        switch (sortBy) {
            case 'name':
                sortedActions.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'newest':
                sortedActions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                break;
            case 'success_rate':
                sortedActions.sort((a, b) => b.success_rate - a.success_rate);
                break;
            case 'popular':
            default:
                sortedActions.sort((a, b) => b.usage_count - a.usage_count);
                break;
        }

        this.renderActions(sortedActions);
    }

    showActionDetails(action) {
        const modal = document.getElementById('action-modal');
        if (!modal) return;

        modal.setAttribute('data-action-id', action.id);
        
        // Update modal content
        document.getElementById('action-modal-title').textContent = action.name;
        document.getElementById('action-modal-description').textContent = action.description;
        
        // Update tags
        const tagsContainer = document.getElementById('action-modal-tags');
        tagsContainer.innerHTML = '';
        action.tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.textContent = tag;
            tagsContainer.appendChild(tagElement);
        });
        
        // Update stats
        document.getElementById('action-success-rate').textContent = `${Math.round(action.success_rate * 100)}%`;
        document.getElementById('action-duration').textContent = `${Math.round(action.avg_duration / 1000)}s`;
        document.getElementById('action-usage').textContent = action.usage_count || '0';
        
        // Show auth notice if needed
        const authNotice = document.getElementById('action-auth-notice');
        authNotice.style.display = action.requires_auth ? 'flex' : 'none';
        
        // Generate parameters form
        this.generateParametersForm(action.parameters);
        
        // Update example code
        this.updateExampleCode(action);
        
        modal.style.display = 'flex';
    }

    generateParametersForm(parameters) {
        const form = document.getElementById('action-parameters-form');
        if (!form) return;

        form.innerHTML = '';
        
        if (!parameters || Object.keys(parameters).length === 0) {
            form.innerHTML = '<p class="empty-state">This action has no configurable parameters.</p>';
            return;
        }

        Object.entries(parameters).forEach(([key, param]) => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';
            
            const label = document.createElement('label');
            label.textContent = param.description || key;
            label.setAttribute('for', `param-${key}`);
            
            let input;
            if (param.type === 'select' && param.options) {
                input = document.createElement('select');
                param.options.forEach(option => {
                    const opt = document.createElement('option');
                    opt.value = option.value || option;
                    opt.textContent = option.label || option;
                    input.appendChild(opt);
                });
            } else if (param.type === 'textarea') {
                input = document.createElement('textarea');
                input.rows = 3;
            } else if (param.type === 'checkbox') {
                input = document.createElement('input');
                input.type = 'checkbox';
            } else {
                input = document.createElement('input');
                input.type = param.type === 'password' ? 'password' : 'text';
            }
            
            input.id = `param-${key}`;
            input.name = key;
            input.className = 'form-control';
            
            if (param.required) {
                input.required = true;
            }
            
            if (param.placeholder) {
                input.placeholder = param.placeholder;
            }
            
            if (param.default !== undefined) {
                if (param.type === 'checkbox') {
                    input.checked = param.default;
                } else {
                    input.value = param.default;
                }
            }
            
            formGroup.appendChild(label);
            formGroup.appendChild(input);
            form.appendChild(formGroup);
        });
    }

    updateExampleCode(action) {
        const codeElement = document.getElementById('action-example-code');
        if (!codeElement) return;

        const example = `# Execute ${action.name} via API
import requests

response = requests.post('${window.location.origin}/api/v1/stored-actions/${action.id}/run', 
    json={
        "parameters": {
            // Add your parameters here
        }
    },
    headers={
        "Authorization": "Bearer YOUR_API_TOKEN"
    }
)

result = response.json()
print(f"Execution ID: {result['run_id']}")`;

        codeElement.textContent = example;
    }

    async quickExecuteAction(action) {
        if (action.requires_auth && !this.state.isAuthenticated) {
            this.showError('Please sign in to execute actions that require authentication.');
            return;
        }

        // If action has parameters, show the modal
        if (action.parameters && Object.keys(action.parameters).length > 0) {
            this.showActionDetails(action);
            return;
        }

        // Execute immediately if no parameters needed
        await this.executeStoredAction(action.id, {});
    }

    async executeStoredAction(actionId, parameters) {
        try {
            this.showExecutionModal();
            this.updateModalExecutionStatus('preparing', 'Preparing action execution...', 10);

            const response = await this.apiClient.executeStoredAction(actionId, { parameters });
            this.state.currentExecution = response;

            // Start polling for results
            await this.pollModalExecutionStatus(response.run_id);
            
        } catch (error) {
            console.error('Stored action execution failed:', error);
            this.showModalExecutionError(error);
        }
    }

    showExecutionModal() {
        const modal = document.getElementById('execution-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    updateModalExecutionStatus(phase, message, progress = 0) {
        const statusIcon = document.getElementById('modal-status-icon');
        const statusTitle = document.getElementById('modal-status-title');
        const statusMessage = document.getElementById('modal-status-message');
        const progressFill = document.getElementById('modal-progress-fill');

        if (statusIcon) {
            const icons = {
                preparing: '⚙️',
                executing: '🚀',
                completed: '✅',
                failed: '❌'
            };
            statusIcon.textContent = icons[phase] || '⏳';
        }

        if (statusTitle) {
            const titles = {
                preparing: 'Preparing Action...',
                executing: 'Executing Action...',
                completed: 'Action Completed!',
                failed: 'Action Failed'
            };
            statusTitle.textContent = titles[phase] || 'Processing...';
        }

        if (statusMessage) {
            statusMessage.textContent = message;
        }

        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }

        // Update elapsed time
        this.updateModalElapsedTime();
    }

    updateModalElapsedTime() {
        const timeElement = document.getElementById('modal-elapsed-time');
        if (!timeElement) return;

        if (!this.state.modalExecutionStartTime) {
            this.state.modalExecutionStartTime = Date.now();
        }

        const updateTime = () => {
            const elapsed = Math.floor((Date.now() - this.state.modalExecutionStartTime) / 1000);
            timeElement.textContent = `${elapsed}s`;
            
            if (this.state.currentExecution) {
                setTimeout(updateTime, 1000);
            }
        };

        updateTime();
    }

    async pollModalExecutionStatus(runId) {
        const maxAttempts = 60;
        let attempts = 0;

        const poll = async () => {
            try {
                attempts++;
                const status = await this.apiClient.getExecutionStatus(runId);
                
                const progress = status.progress || 
                                (status.status === 'running' ? 75 : 
                                 status.status === 'completed' ? 100 : 50);
                
                this.updateModalExecutionStatus(status.status, status.error_message || 'Processing...', progress);

                if (status.status === 'completed') {
                    const results = await this.apiClient.getExecutionResults(runId);
                    this.showModalExecutionResults(results);
                    return;
                } else if (status.status === 'failed') {
                    this.showModalExecutionError(new Error(status.error_message || 'Action failed'));
                    return;
                } else if (attempts >= maxAttempts) {
                    this.showModalExecutionError(new Error('Action timed out'));
                    return;
                }

                setTimeout(poll, this.config.pollInterval);
                
            } catch (error) {
                console.error('Modal polling error:', error);
                if (attempts < maxAttempts) {
                    setTimeout(poll, this.config.pollInterval);
                } else {
                    this.showModalExecutionError(error);
                }
            }
        };

        poll();
    }

    showModalExecutionResults(results) {
        const resultsContainer = document.getElementById('modal-execution-results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = '';
        resultsContainer.style.display = 'block';

        // Create results display
        if (results.screenshot_url) {
            const screenshotDiv = document.createElement('div');
            screenshotDiv.innerHTML = `
                <h4>Screenshot</h4>
                <div class="screenshot-wrapper">
                    <img src="${results.screenshot_url}" alt="Action screenshot" class="screenshot-image" style="max-width: 100%; height: auto;">
                </div>
            `;
            resultsContainer.appendChild(screenshotDiv);
        }

        if (results.result_data) {
            const dataDiv = document.createElement('div');
            dataDiv.innerHTML = `
                <h4>Results</h4>
                <pre class="results-data">${JSON.stringify(results.result_data, null, 2)}</pre>
            `;
            resultsContainer.appendChild(dataDiv);
        }

        // Update footer with success actions
        const footer = document.getElementById('execution-modal-footer');
        footer.innerHTML = `
            <button type="button" class="btn btn-secondary" onclick="this.closest('.modal-overlay').style.display='none'">Close</button>
            <button type="button" class="btn btn-primary" onclick="window.steelApp.copyToClipboard(JSON.stringify(${JSON.stringify(results)}, null, 2))">Copy Results</button>
        `;
    }

    showModalExecutionError(error) {
        const resultsContainer = document.getElementById('modal-execution-results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <div class="error-results">
                <h4>Execution Failed</h4>
                <div class="error-message">
                    <div class="error-type">${error.name || 'ExecutionError'}</div>
                    <div class="error-description">${error.message || 'An unexpected error occurred.'}</div>
                </div>
            </div>
        `;
        resultsContainer.style.display = 'block';

        // Update footer
        const footer = document.getElementById('execution-modal-footer');
        footer.innerHTML = `
            <button type="button" class="btn btn-secondary" onclick="this.closest('.modal-overlay').style.display='none'">Close</button>
            <button type="button" class="btn btn-primary" onclick="window.location.reload()">Try Again</button>
        `;
    }

    // === MY ACTIONS PAGE === //
    async initializeMyActions() {
        console.log('Initializing my actions page');
        
        // Check authentication
        if (!this.state.isAuthenticated) {
            this.showAuthRequiredNotice();
            return;
        }
        
        this.setupMyActionsSearch();
        this.setupMyActionsFilters();
        this.setupActionEditor();
        this.setupBulkActions();
        
        await this.loadMyActions();
        await this.loadActionStats();
    }

    showAuthRequiredNotice() {
        const notice = document.getElementById('auth-notice');
        const content = document.getElementById('my-actions-content');
        
        if (notice) notice.style.display = 'block';
        if (content) content.style.display = 'none';
        
        // Setup auth button
        const authBtn = document.getElementById('auth-sign-in');
        if (authBtn) {
            authBtn.addEventListener('click', () => this.showAuthModal());
        }
    }

    setupMyActionsSearch() {
        const searchInput = document.getElementById('actions-search');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.filterMyActions();
            }, 300);
        });
    }

    setupMyActionsFilters() {
        const statusFilter = document.getElementById('status-filter');
        const categoryFilter = document.getElementById('category-filter');

        [statusFilter, categoryFilter].forEach(filter => {
            if (filter) {
                filter.addEventListener('change', () => {
                    this.filterMyActions();
                });
            }
        });
    }

    setupActionEditor() {
        const modal = document.getElementById('action-editor-modal');
        const createBtn = document.getElementById('create-action-btn');
        const createFirstBtn = document.getElementById('create-first-action');
        const closeBtn = document.getElementById('close-action-editor');
        const cancelBtn = document.getElementById('cancel-action-editor');
        const form = document.getElementById('action-editor-form');
        const addParamBtn = document.getElementById('add-parameter');

        if (!modal) return;

        // Open modal buttons
        [createBtn, createFirstBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    this.openActionEditor();
                });
            }
        });

        // Close modal buttons
        [closeBtn, cancelBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    modal.style.display = 'none';
                });
            }
        });

        // Form submission
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveAction();
            });
        }

        // Add parameter button
        if (addParamBtn) {
            addParamBtn.addEventListener('click', () => {
                this.addParameterField();
            });
        }

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    setupBulkActions() {
        const bulkBtn = document.getElementById('bulk-actions-btn');
        const exportBtn = document.getElementById('export-all-btn');

        if (bulkBtn) {
            bulkBtn.addEventListener('click', () => {
                this.showBulkActionsMenu();
            });
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportAllActions();
            });
        }
    }

    async loadMyActions() {
        try {
            this.showMyActionsLoading(true);
            
            const response = await this.apiClient.getStoredActions();
            this.state.userActions = response.actions || [];
            
            this.renderMyActions(this.state.userActions);
            this.showMyActionsLoading(false);
            
        } catch (error) {
            console.error('Failed to load user actions:', error);
            this.showMyActionsError();
        }
    }

    async loadActionStats() {
        try {
            const stats = await this.apiClient.getActionStats();
            this.updateActionStats(stats);
        } catch (error) {
            console.log('Failed to load action stats:', error);
            // Use default stats
            this.updateActionStats({
                total_actions: this.state.userActions?.length || 0,
                successful_runs: 0,
                avg_runtime: 0,
                last_run: null
            });
        }
    }

    updateActionStats(stats) {
        const elements = {
            'total-actions': stats.total_actions,
            'successful-runs': stats.successful_runs,
            'avg-runtime': stats.avg_runtime ? `${Math.round(stats.avg_runtime / 1000)}s` : '0s',
            'last-run': stats.last_run ? new Date(stats.last_run).toLocaleDateString() : 'Never'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
    }

    showMyActionsLoading(show) {
        const loading = document.getElementById('my-actions-loading');
        const list = document.getElementById('my-actions-list');
        const empty = document.getElementById('my-actions-empty');

        if (loading) loading.style.display = show ? 'flex' : 'none';
        if (list) list.style.display = show ? 'none' : 'block';
        if (empty) empty.style.display = 'none';
    }

    showMyActionsError() {
        const loading = document.getElementById('my-actions-loading');
        const list = document.getElementById('my-actions-list');
        const empty = document.getElementById('my-actions-empty');

        if (loading) loading.style.display = 'none';
        if (list) list.style.display = 'none';
        if (empty) {
            empty.style.display = 'block';
            empty.querySelector('h3').textContent = 'Failed to load actions';
            empty.querySelector('p').textContent = 'Please try refreshing the page.';
        }
    }

    renderMyActions(actions) {
        const list = document.getElementById('my-actions-list');
        const empty = document.getElementById('my-actions-empty');

        if (!list) return;

        if (actions.length === 0) {
            list.style.display = 'none';
            if (empty) empty.style.display = 'block';
            return;
        }

        list.style.display = 'block';
        if (empty) empty.style.display = 'none';

        list.innerHTML = '';
        
        actions.forEach(action => {
            const item = this.createMyActionItem(action);
            list.appendChild(item);
        });
    }

    createMyActionItem(action) {
        const template = document.getElementById('my-action-item-template');
        if (!template) return this.createMyActionItemFallback(action);

        const item = template.content.cloneNode(true);
        const itemElement = item.querySelector('.action-item');
        
        itemElement.setAttribute('data-action-id', action.id);
        
        // Set basic info
        item.querySelector('.action-name').textContent = action.name;
        item.querySelector('.action-description').textContent = action.description || 'No description';
        item.querySelector('.action-category').textContent = action.action_type;
        item.querySelector('.action-status').textContent = action.is_active ? 'Active' : 'Inactive';
        item.querySelector('.action-last-run').textContent = action.last_run ? 
            new Date(action.last_run).toLocaleDateString() : 'Never run';
        
        // Set stats
        item.querySelector('.runs-count').textContent = action.run_count || 0;
        item.querySelector('.success-rate').textContent = action.success_rate || '0%';
        item.querySelector('.avg-time').textContent = action.avg_execution_time ? 
            `${Math.round(action.avg_execution_time / 1000)}s` : '0s';
        
        // Setup action buttons
        const runBtn = item.querySelector('.run-action-btn');
        const editBtn = item.querySelector('.edit-action-btn');
        
        runBtn.addEventListener('click', () => this.runMyAction(action.id));
        editBtn.addEventListener('click', () => this.editMyAction(action.id));
        
        return item;
    }

    createMyActionItemFallback(action) {
        const div = document.createElement('div');
        div.className = 'action-item';
        div.setAttribute('data-action-id', action.id);
        
        div.innerHTML = `
            <div class="action-item-header">
                <div class="action-info">
                    <h3 class="action-name">${action.name}</h3>
                    <p class="action-description">${action.description || 'No description'}</p>
                    <div class="action-meta">
                        <span class="action-category">${action.action_type}</span>
                        <span class="action-status">${action.is_active ? 'Active' : 'Inactive'}</span>
                        <span class="action-last-run">${action.last_run ? new Date(action.last_run).toLocaleDateString() : 'Never run'}</span>
                    </div>
                </div>
                <div class="action-stats">
                    <div class="stat-item">
                        <span class="stat-value">${action.run_count || 0}</span>
                        <span class="stat-label">Runs</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${action.success_rate || '0%'}</span>
                        <span class="stat-label">Success</span>
                    </div>
                </div>
                <div class="action-actions">
                    <button class="btn btn-small btn-primary" onclick="window.steelApp.runMyAction('${action.id}')">Run</button>
                    <button class="btn btn-small btn-secondary" onclick="window.steelApp.editMyAction('${action.id}')">Edit</button>
                </div>
            </div>
        `;
        
        return div;
    }

    filterMyActions() {
        const searchTerm = document.getElementById('actions-search')?.value.toLowerCase() || '';
        const statusFilter = document.getElementById('status-filter')?.value || 'all';
        const categoryFilter = document.getElementById('category-filter')?.value || 'all';

        if (!this.state.userActions) return;

        const filteredActions = this.state.userActions.filter(action => {
            // Search filter
            const matchesSearch = searchTerm === '' || 
                action.name.toLowerCase().includes(searchTerm) ||
                (action.description && action.description.toLowerCase().includes(searchTerm));

            // Status filter
            const matchesStatus = statusFilter === 'all' ||
                (statusFilter === 'active' && action.is_active) ||
                (statusFilter === 'inactive' && !action.is_active);

            // Category filter
            const matchesCategory = categoryFilter === 'all' ||
                action.action_type === categoryFilter;

            return matchesSearch && matchesStatus && matchesCategory;
        });

        this.renderMyActions(filteredActions);
    }

    openActionEditor(actionId = null) {
        const modal = document.getElementById('action-editor-modal');
        const title = document.getElementById('action-editor-title');
        const form = document.getElementById('action-editor-form');

        if (!modal || !form) return;

        // Reset form
        form.reset();
        
        if (actionId) {
            title.textContent = 'Edit Action';
            // Load action data for editing
            this.loadActionForEditing(actionId);
        } else {
            title.textContent = 'Create New Action';
        }

        modal.style.display = 'flex';
    }

    async loadActionForEditing(actionId) {
        try {
            const action = await this.apiClient.getStoredAction(actionId);
            // Populate form with action data
            document.getElementById('action-name').value = action.name;
            document.getElementById('action-description').value = action.description || '';
            document.getElementById('action-category').value = action.category || 'custom';
            document.getElementById('action-type').value = action.action_type;
            document.getElementById('action-public').checked = action.is_public;
            document.getElementById('action-active').checked = action.is_active;
            document.getElementById('webhook-url').value = action.webhook_url || '';
            
            // TODO: Populate parameters
            
        } catch (error) {
            console.error('Failed to load action for editing:', error);
            this.showError('Failed to load action details');
        }
    }

    addParameterField() {
        const builder = document.getElementById('parameters-builder');
        if (!builder) return;

        const paramDiv = document.createElement('div');
        paramDiv.className = 'parameter-item';
        paramDiv.innerHTML = `
            <input type="text" placeholder="Parameter name" class="param-name">
            <select class="param-type">
                <option value="string">Text</option>
                <option value="number">Number</option>
                <option value="boolean">Checkbox</option>
                <option value="url">URL</option>
            </select>
            <input type="text" placeholder="Description" class="param-description">
            <button type="button" class="btn btn-small btn-danger remove-param">Remove</button>
        `;

        // Setup remove button
        const removeBtn = paramDiv.querySelector('.remove-param');
        removeBtn.addEventListener('click', () => {
            paramDiv.remove();
        });

        builder.appendChild(paramDiv);
    }

    async saveAction() {
        const form = document.getElementById('action-editor-form');
        const formData = new FormData(form);
        
        // Collect parameters
        const parameterItems = document.querySelectorAll('.parameter-item');
        const parameters = {};
        
        parameterItems.forEach(item => {
            const name = item.querySelector('.param-name').value;
            const type = item.querySelector('.param-type').value;
            const description = item.querySelector('.param-description').value;
            
            if (name) {
                parameters[name] = {
                    type: type,
                    description: description,
                    required: false // Default to optional
                };
            }
        });

        const actionData = {
            name: formData.get('action-name'),
            description: formData.get('action-description'),
            action_type: formData.get('action-type'),
            parameters: parameters,
            is_public: formData.has('action-public'),
            is_active: formData.has('action-active'),
            webhook_url: formData.get('webhook-url') || null
        };

        try {
            await this.apiClient.createStoredAction(actionData);
            this.showSuccess('Action saved successfully!');
            
            // Close modal and refresh list
            document.getElementById('action-editor-modal').style.display = 'none';
            await this.loadMyActions();
            
        } catch (error) {
            console.error('Failed to save action:', error);
            this.showError('Failed to save action. Please try again.');
        }
    }

    async runMyAction(actionId) {
        try {
            const response = await this.apiClient.executeStoredAction(actionId, {});
            this.showSuccess(`Action execution started! Run ID: ${response.run_id}`);
            
            // Optionally show execution status
            // this.showExecutionModal();
            // await this.pollModalExecutionStatus(response.run_id);
            
        } catch (error) {
            console.error('Failed to run action:', error);
            this.showError('Failed to start action execution.');
        }
    }

    async editMyAction(actionId) {
        this.openActionEditor(actionId);
    }

    showBulkActionsMenu() {
        // TODO: Implement bulk actions menu
        this.showError('Bulk actions not implemented yet');
    }

    async exportAllActions() {
        try {
            const actions = await this.apiClient.getStoredActions();
            const exportData = {
                export_date: new Date().toISOString(),
                actions: actions.actions
            };
            
            const blob = new Blob([JSON.stringify(exportData, null, 2)], {
                type: 'application/json'
            });
            
            this.downloadFile(URL.createObjectURL(blob), 'my-steel-actions.json');
            this.showSuccess('Actions exported successfully!');
            
        } catch (error) {
            console.error('Failed to export actions:', error);
            this.showError('Failed to export actions.');
        }
    }

    // === EDITOR PAGE === //
    async initializeEditor() {
        console.log('Initializing editor');
        
        await this.setupMonacoEditor();
        this.setupActionSelector();
        this.setupEditorControls();
        this.setupTabs();
        this.setupTestExecution();
        
        // Load action from URL parameter if present
        const urlParams = new URLSearchParams(window.location.search);
        const actionId = urlParams.get('action');
        if (actionId) {
            await this.loadActionInEditor(actionId);
        }
    }

    async setupMonacoEditor() {
        return new Promise((resolve) => {
            require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }});
            
            require(['vs/editor/editor.main'], () => {
                this.state.monacoEditor = monaco.editor.create(document.getElementById('code-editor'), {
                    value: '# Select an action to view its implementation\n',
                    language: 'python',
                    theme: 'vs-light',
                    readOnly: true,
                    minimap: { enabled: true },
                    wordWrap: 'on',
                    lineNumbers: 'on',
                    renderWhitespace: 'selection',
                    fontSize: 14,
                    fontFamily: 'JetBrains Mono, SF Mono, Monaco, Cascadia Code, Roboto Mono, Consolas, monospace'
                });

                // Handle window resize
                window.addEventListener('resize', () => {
                    this.state.monacoEditor.layout();
                });

                resolve();
            });
        });
    }

    setupActionSelector() {
        const select = document.getElementById('action-select');
        if (!select) return;

        select.addEventListener('change', async (e) => {
            const actionId = e.target.value;
            if (actionId) {
                await this.loadActionInEditor(actionId);
            } else {
                this.clearEditor();
            }
        });

        // Load available actions
        this.loadActionsForSelector();
    }

    async loadActionsForSelector() {
        try {
            const response = await this.apiClient.getActions();
            const select = document.getElementById('action-select');
            
            if (select) {
                select.innerHTML = '<option value="">Select an action...</option>';
                
                response.actions.forEach(action => {
                    const option = document.createElement('option');
                    option.value = action.id;
                    option.textContent = `${action.name} (${action.category})`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load actions for selector:', error);
        }
    }

    setupEditorControls() {
        const copyBtn = document.getElementById('copy-code-btn');
        const downloadBtn = document.getElementById('download-code-btn');
        const testBtn = document.getElementById('test-action-btn');
        const readonlyBtn = document.getElementById('toggle-readonly');
        const minimapBtn = document.getElementById('toggle-minimap');
        const wordwrapBtn = document.getElementById('toggle-wordwrap');

        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const code = this.state.monacoEditor.getValue();
                this.copyToClipboard(code);
                this.showSuccess('Code copied to clipboard!');
            });
        }

        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                const code = this.state.monacoEditor.getValue();
                const actionName = this.state.currentAction?.name || 'action';
                this.downloadText(code, `${actionName.toLowerCase().replace(/\s+/g, '_')}.py`);
            });
        }

        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.startActionTest();
            });
        }

        if (readonlyBtn) {
            readonlyBtn.addEventListener('click', () => {
                const isReadOnly = this.state.monacoEditor.getOption(monaco.editor.EditorOption.readOnly);
                this.state.monacoEditor.updateOptions({ readOnly: !isReadOnly });
                readonlyBtn.querySelector('.control-icon').textContent = isReadOnly ? '✏️' : '🔒';
            });
        }

        if (minimapBtn) {
            minimapBtn.addEventListener('click', () => {
                const minimapEnabled = this.state.monacoEditor.getOption(monaco.editor.EditorOption.minimap).enabled;
                this.state.monacoEditor.updateOptions({ 
                    minimap: { enabled: !minimapEnabled }
                });
            });
        }

        if (wordwrapBtn) {
            wordwrapBtn.addEventListener('click', () => {
                const wordWrap = this.state.monacoEditor.getOption(monaco.editor.EditorOption.wordWrap);
                this.state.monacoEditor.updateOptions({ 
                    wordWrap: wordWrap === 'on' ? 'off' : 'on'
                });
            });
        }
    }

    setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-tab');
                
                // Update active states
                tabButtons.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(`${tabId}-tab`).classList.add('active');
            });
        });
    }

    setupTestExecution() {
        const testForm = document.getElementById('test-auth-form');
        const cancelBtn = document.getElementById('cancel-test');
        const authModal = document.getElementById('auth-modal');

        if (testForm) {
            testForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const credentials = {
                    username: document.getElementById('test-username').value,
                    password: document.getElementById('test-password').value
                };

                if (authModal) authModal.style.display = 'none';
                await this.executeActionTest(credentials);
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (authModal) authModal.style.display = 'none';
            });
        }
    }

    async loadActionInEditor(actionId) {
        try {
            const action = await this.apiClient.getAction(actionId);
            this.state.currentAction = action;
            
            // Load and display the action code
            const code = await this.apiClient.getActionCode(actionId);
            this.state.monacoEditor.setValue(code);
            
            // Update editor title and description
            this.updateEditorHeader(action);
            
            // Show action info banner
            this.showActionInfoBanner(action);
            
            // Load parameters for testing
            this.loadActionParameters(action);
            
            // Load execution history
            this.loadActionHistory(actionId);
            
        } catch (error) {
            console.error('Failed to load action in editor:', error);
            this.showError('Failed to load action code.');
        }
    }

    updateEditorHeader(action) {
        const title = document.getElementById('editor-title');
        const description = document.getElementById('editor-description');
        
        if (title) {
            title.textContent = `${action.name} - Code Preview`;
        }
        
        if (description) {
            description.textContent = action.description;
        }
    }

    showActionInfoBanner(action) {
        const banner = document.getElementById('action-info-banner');
        if (!banner) return;

        document.getElementById('action-info-name').textContent = action.name;
        document.getElementById('action-info-description').textContent = action.description;
        document.getElementById('action-info-category').textContent = action.category;
        document.getElementById('action-info-success-rate').textContent = `${Math.round(action.success_rate * 100)}%`;
        document.getElementById('action-info-duration').textContent = `${Math.round(action.avg_duration / 1000)}s`;

        banner.style.display = 'block';

        // Setup banner actions
        const galleryBtn = document.getElementById('view-in-gallery');
        const saveBtn = document.getElementById('save-action-btn');

        if (galleryBtn) {
            galleryBtn.onclick = () => window.location.href = `/dashboard#${action.id}`;
        }

        if (saveBtn) {
            saveBtn.onclick = () => this.saveActionToUser(action);
        }
    }

    loadActionParameters(action) {
        const container = document.getElementById('parameters-form');
        const empty = document.getElementById('parameters-empty');
        
        if (!container) return;

        if (!action.parameters || Object.keys(action.parameters).length === 0) {
            if (empty) empty.style.display = 'block';
            return;
        }

        if (empty) empty.style.display = 'none';
        
        // Generate parameters form (reuse from dashboard)
        this.generateParametersForm(action.parameters, container);
    }

    async loadActionHistory(actionId) {
        try {
            const history = await this.apiClient.getActionHistory(actionId);
            this.renderActionHistory(history);
        } catch (error) {
            console.log('No history available or failed to load:', error);
        }
    }

    renderActionHistory(history) {
        const list = document.getElementById('history-list');
        const empty = document.getElementById('history-empty');
        
        if (!list) return;

        if (!history || history.length === 0) {
            if (empty) empty.style.display = 'block';
            return;
        }

        if (empty) empty.style.display = 'none';
        
        list.innerHTML = '';
        
        history.forEach(run => {
            const item = this.createHistoryItem(run);
            list.appendChild(item);
        });
    }

    createHistoryItem(run) {
        const template = document.getElementById('history-item-template');
        if (!template) return this.createHistoryItemFallback(run);

        const item = template.content.cloneNode(true);
        const itemElement = item.querySelector('.history-item');
        
        itemElement.setAttribute('data-run-id', run.id);
        
        // Set status
        const statusIcon = item.querySelector('.status-icon');
        const statusText = item.querySelector('.status-text');
        
        statusIcon.textContent = run.status === 'completed' ? '✅' : 
                                run.status === 'failed' ? '❌' : '⏳';
        statusText.textContent = run.status.charAt(0).toUpperCase() + run.status.slice(1);
        
        // Set time
        item.querySelector('.history-time').textContent = 
            new Date(run.created_at).toLocaleString();
        
        // Set details
        item.querySelector('.history-duration').textContent = 
            run.execution_time ? `${Math.round(run.execution_time / 1000)}s` : 'N/A';
        item.querySelector('.history-parameters').textContent = 
            Object.keys(run.parameters || {}).length + ' parameters';
        
        // Setup view results button
        const viewBtn = item.querySelector('.view-result-btn');
        viewBtn.addEventListener('click', () => {
            this.viewExecutionResults(run.id);
        });
        
        return item;
    }

    createHistoryItemFallback(run) {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.setAttribute('data-run-id', run.id);
        
        div.innerHTML = `
            <div class="history-header">
                <div class="history-status">
                    <span class="status-icon">${run.status === 'completed' ? '✅' : run.status === 'failed' ? '❌' : '⏳'}</span>
                    <span class="status-text">${run.status.charAt(0).toUpperCase() + run.status.slice(1)}</span>
                </div>
                <div class="history-time">${new Date(run.created_at).toLocaleString()}</div>
            </div>
            <div class="history-details">
                <div class="history-duration">${run.execution_time ? Math.round(run.execution_time / 1000) + 's' : 'N/A'}</div>
                <div class="history-parameters">${Object.keys(run.parameters || {}).length} parameters</div>
            </div>
            <div class="history-actions">
                <button class="btn btn-small btn-secondary view-result-btn">View Results</button>
            </div>
        `;
        
        return div;
    }

    clearEditor() {
        if (this.state.monacoEditor) {
            this.state.monacoEditor.setValue('# Select an action to view its implementation\n');
        }
        
        const banner = document.getElementById('action-info-banner');
        if (banner) banner.style.display = 'none';
        
        // Reset tabs to parameters
        document.querySelector('.tab-btn[data-tab="parameters"]').click();
    }

    async startActionTest() {
        if (!this.state.currentAction) {
            this.showError('Please select an action first.');
            return;
        }

        // Collect parameters from form
        const form = document.getElementById('parameters-form');
        const formData = new FormData(form);
        const parameters = Object.fromEntries(formData.entries());

        // Check if authentication is required
        if (this.state.currentAction.requires_auth) {
            const authModal = document.getElementById('auth-modal');
            if (authModal) authModal.style.display = 'flex';
            return;
        }

        await this.executeActionTest(null, parameters);
    }

    async executeActionTest(credentials, parameters = {}) {
        try {
            // Switch to execution tab
            document.querySelector('.tab-btn[data-tab="execution"]').click();
            
            this.showExecutionStatus('preparing', 'Starting test execution...');

            const payload = { parameters };
            if (credentials) {
                payload.credentials = credentials;
            }

            const response = await this.apiClient.executeStoredAction(this.state.currentAction.id, payload);
            
            // Poll for results
            await this.pollTestExecution(response.run_id);
            
        } catch (error) {
            console.error('Test execution failed:', error);
            this.showTestExecutionError(error);
        }
    }

    showExecutionStatus(phase, message) {
        const container = document.getElementById('execution-status');
        const icon = document.getElementById('exec-status-icon');
        const title = document.getElementById('exec-status-title');
        const messageEl = document.getElementById('exec-status-message');

        if (container) container.style.display = 'block';
        
        if (icon) {
            const icons = { preparing: '⚙️', executing: '🚀', completed: '✅', failed: '❌' };
            icon.textContent = icons[phase] || '⏳';
        }
        
        if (title) title.textContent = message;
        if (messageEl) messageEl.textContent = 'Test execution in progress...';
    }

    async pollTestExecution(runId) {
        const maxAttempts = 60;
        let attempts = 0;

        const poll = async () => {
            try {
                attempts++;
                const status = await this.apiClient.getExecutionStatus(runId);
                
                this.updateTestProgress(status);

                if (status.status === 'completed') {
                    const results = await this.apiClient.getExecutionResults(runId);
                    this.showTestExecutionResults(results);
                    this.loadActionHistory(this.state.currentAction.id); // Refresh history
                    return;
                } else if (status.status === 'failed') {
                    this.showTestExecutionError(new Error(status.error_message || 'Test failed'));
                    return;
                } else if (attempts >= maxAttempts) {
                    this.showTestExecutionError(new Error('Test execution timed out'));
                    return;
                }

                setTimeout(poll, this.config.pollInterval);
                
            } catch (error) {
                console.error('Test polling error:', error);
                if (attempts < maxAttempts) {
                    setTimeout(poll, this.config.pollInterval);
                } else {
                    this.showTestExecutionError(error);
                }
            }
        };

        poll();
    }

    updateTestProgress(status) {
        const progressFill = document.getElementById('exec-progress-fill');
        const timeEl = document.getElementById('exec-elapsed-time');
        
        const progress = status.progress || 
                        (status.status === 'running' ? 75 : 
                         status.status === 'completed' ? 100 : 50);
        
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }

        if (timeEl && status.started_at) {
            const elapsed = Math.floor((Date.now() - new Date(status.started_at)) / 1000);
            timeEl.textContent = `${elapsed}s`;
        }
    }

    showTestExecutionResults(results) {
        const container = document.getElementById('execution-results');
        if (!container) return;

        container.innerHTML = `
            <div class="test-results-header">
                <h4>✅ Test Completed Successfully</h4>
            </div>
            ${results.screenshot_url ? `
                <div class="screenshot-container">
                    <h5>Screenshot</h5>
                    <img src="${results.screenshot_url}" alt="Test screenshot" style="max-width: 100%; border-radius: 8px;">
                </div>
            ` : ''}
            ${results.result_data ? `
                <div class="data-container">
                    <h5>Results Data</h5>
                    <pre class="results-data">${JSON.stringify(results.result_data, null, 2)}</pre>
                </div>
            ` : ''}
            <div class="test-actions">
                <button class="btn btn-secondary btn-small" onclick="window.steelApp.copyToClipboard(JSON.stringify(${JSON.stringify(results)}, null, 2))">
                    Copy Results
                </button>
            </div>
        `;
        
        container.style.display = 'block';
    }

    showTestExecutionError(error) {
        const container = document.getElementById('execution-results');
        if (!container) return;

        container.innerHTML = `
            <div class="test-results-header error">
                <h4>❌ Test Failed</h4>
            </div>
            <div class="error-details">
                <p><strong>Error:</strong> ${error.message}</p>
                <p>Please check your parameters and try again.</p>
            </div>
        `;
        
        container.style.display = 'block';
    }

    // === UTILITY METHODS === //
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (err) {
                console.error('Failed to copy text: ', err);
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
    }

    downloadText(text, filename) {
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }

    downloadFile(url, filename) {
        const element = document.createElement('a');
        element.setAttribute('href', url);
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // Delegate to notification manager
        if (this.notificationManager) {
            return this.notificationManager.show(message, type);
        }
        
        // Fallback for backward compatibility
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    logout() {
        this.storage.remove('auth_token');
        this.state.currentUser = null;
        this.state.isAuthenticated = false;
        this.updateAuthUI(false);
        this.showSuccess('Signed out successfully');
        
        // Redirect to home if on a protected page
        if (window.location.pathname !== '/') {
            window.location.href = '/';
        }
    }

    showAuthModal() {
        // Check if we're in dev mode and should already be authenticated
        if (this.state.devMode && this.state.devMode.auth_disabled) {
            console.log('Dev mode detected in showAuthModal, refreshing auth status');
            this.checkAuthStatus();
            return;
        }
        
        // For now, just redirect to a simple auth page or show a placeholder
        this.showError('Authentication not implemented yet. Coming soon!');
    }
}

// === API CLIENT === //
class SteelAPIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, config);
        
        if (!response.ok && response.status !== 202) {
            const error = await response.text();
            throw new Error(error || `HTTP ${response.status}`);
        }
        
        // Handle 202 as a special case (execution in progress)
        if (response.status === 202) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        
        return await response.text();
    }

    // Authentication
    async getCurrentUser() {
        return this.makeRequest('/auth/me');
    }

    // Actions
    async getActions(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.makeRequest(`/actions${queryString ? '?' + queryString : ''}`);
    }

    async getAction(actionId) {
        return this.makeRequest(`/actions/${actionId}`);
    }

    async getActionCode(actionId) {
        return this.makeRequest(`/actions/${actionId}/code`);
    }

    async searchActions(query) {
        return this.makeRequest(`/actions/search?q=${encodeURIComponent(query)}`);
    }

    async getFeaturedActions() {
        return this.makeRequest('/actions/featured');
    }

    async getActionHistory(actionId) {
        return this.makeRequest(`/actions/${actionId}/history`);
    }

    // Execution
    async executeAction(payload) {
        return this.makeRequest('/actions/execute', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    async executeStoredAction(actionId, payload) {
        return this.makeRequest(`/stored-actions/${actionId}/run`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    async getExecutionStatus(runId) {
        return this.makeRequest(`/actions/executions/${runId}/status`);
    }

    async getExecutionResults(runId) {
        return this.makeRequest(`/actions/executions/${runId}/results`);
    }

    async analyzeAction(actionText) {
        return this.makeRequest('/actions/analyze', {
            method: 'POST',
            body: JSON.stringify({ input: actionText })
        });
    }

    // Stored Actions
    async getStoredActions(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.makeRequest(`/stored-actions/user${queryString ? '?' + queryString : ''}`);
    }

    async getStoredAction(actionId) {
        return this.makeRequest(`/stored-actions/${actionId}`);
    }

    async createStoredAction(actionData) {
        return this.makeRequest('/stored-actions/save', {
            method: 'POST',
            body: JSON.stringify(actionData)
        });
    }

    async updateStoredAction(actionId, actionData) {
        return this.makeRequest(`/stored-actions/${actionId}`, {
            method: 'PUT',
            body: JSON.stringify(actionData)
        });
    }

    async deleteStoredAction(actionId) {
        return this.makeRequest(`/stored-actions/${actionId}`, {
            method: 'DELETE'
        });
    }

    async getActionStats() {
        return this.makeRequest('/monitoring/user-stats');
    }
    
    // === CREDENTIAL API METHODS === //
    async getCredentials(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.makeRequest(`/credentials${params ? '?' + params : ''}`);
    }
    
    async createCredential(credentialData) {
        return this.makeRequest('/credentials', {
            method: 'POST',
            body: JSON.stringify(credentialData)
        });
    }
    
    async updateCredential(credentialId, credentialData) {
        return this.makeRequest(`/credentials/${credentialId}`, {
            method: 'PUT',
            body: JSON.stringify(credentialData)
        });
    }
    
    async deleteCredential(credentialId) {
        return this.makeRequest(`/credentials/${credentialId}`, {
            method: 'DELETE'
        });
    }
    
    async validateCredential(credentialId, validationData = {}) {
        return this.makeRequest(`/credentials/${credentialId}/validate`, {
            method: 'POST',
            body: JSON.stringify(validationData)
        });
    }
    
    // === TEMPLATE API METHODS === //
    async getTemplates(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.makeRequest(`/templates${params ? '?' + params : ''}`);
    }
    
    async getTemplate(templateId) {
        return this.makeRequest(`/templates/${templateId}`);
    }
    
    async createActionFromTemplate(templateId, templateData) {
        return this.makeRequest(`/templates/use/${templateId}`, {
            method: 'POST',
            body: JSON.stringify(templateData)
        });
    }
    
    async shareActionAsTemplate(shareData) {
        return this.makeRequest('/templates/share', {
            method: 'POST',
            body: JSON.stringify(shareData)
        });
    }
    
    async getTemplateCategories() {
        return this.makeRequest('/templates/categories/list');
    }
    
    async getFeaturedTemplates() {
        return this.makeRequest('/templates/stats/featured');
    }
    
    async getPopularTemplates(limit = 10) {
        return this.makeRequest(`/templates/stats/popular?limit=${limit}`);
    }
    
    // === BULK OPERATIONS API METHODS === //
    async bulkDeleteActions(actionIds) {
        return this.makeRequest('/bulk/stored-actions/delete', {
            method: 'POST',
            body: JSON.stringify({ action_ids: actionIds })
        });
    }
    
    async bulkExecuteActions(actionIds, parameters = {}) {
        return this.makeRequest('/bulk/stored-actions/execute', {
            method: 'POST',
            body: JSON.stringify({ action_ids: actionIds, parameters })
        });
    }
    
    async bulkUpdateActions(actionIds, updateData) {
        return this.makeRequest('/bulk/stored-actions/update', {
            method: 'POST',
            body: JSON.stringify({ action_ids: actionIds, update_data: updateData })
        });
    }
    
    // === MONITORING API METHODS === //
    async getSystemHealth() {
        return this.makeRequest('/monitoring/health');
    }
    
    async getUserStats() {
        return this.makeRequest('/monitoring/user-stats');
    }
    
    async getExecutionMetrics(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.makeRequest(`/monitoring/executions${queryString ? '?' + queryString : ''}`);
    }
    
    async getPerformanceMetrics() {
        return this.makeRequest('/monitoring/performance');
    }
    
    // === DEV MODE API METHODS === //
    async getDevStatus() {
        return this.makeRequest('/actions/dev-status');
    }
}

// === EVENT MANAGER === //
class EventManager {
    constructor() {
        this.listeners = {};
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.listeners[event]) return;
        
        const index = this.listeners[event].indexOf(callback);
        if (index > -1) {
            this.listeners[event].splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.listeners[event]) return;
        
        this.listeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });
    }
}

// === LOCAL STORAGE WRAPPER === //
class LocalStorage {
    get(key) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    }

    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Error writing to localStorage:', error);
            return false;
        }
    }

    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Error removing from localStorage:', error);
            return false;
        }
    }

    clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Error clearing localStorage:', error);
            return false;
        }
    }
}

// === WEBSOCKET MANAGER === //
class WebSocketManager {
    constructor(app) {
        this.app = app;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.heartbeatInterval = null;
        this.messageQueue = [];
    }
    
    async connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }
        
        try {
            const token = this.app.storage.get('auth_token');
            if (!token) {
                console.log('No auth token, skipping WebSocket connection');
                return;
            }
            
            const wsUrl = `${this.app.config.wsBaseUrl}/connect?token=${encodeURIComponent(token)}`;
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
            this.ws.onerror = this.handleError.bind(this);
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.scheduleReconnect();
        }
    }
    
    handleOpen() {
        console.log('WebSocket connected');
        this.app.state.isWebSocketConnected = true;
        this.reconnectAttempts = 0;
        
        // Start heartbeat
        this.heartbeatInterval = setInterval(() => {
            this.send({ type: 'ping' });
        }, 30000);
        
        // Send queued messages
        this.messageQueue.forEach(message => this.send(message));
        this.messageQueue = [];
        
        this.app.notificationManager.showSuccess('Real-time updates connected');
    }
    
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.processMessage(data);
        } catch (error) {
            console.error('Invalid WebSocket message:', error);
        }
    }
    
    handleClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.app.state.isWebSocketConnected = false;
        
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000) {
            this.scheduleReconnect();
        }
    }
    
    handleError(error) {
        console.error('WebSocket error:', error);
        this.app.notificationManager.showError('Real-time connection error');
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        setTimeout(() => {
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            this.connect();
        }, delay);
    }
    
    processMessage(data) {
        switch (data.type) {
            case 'action_status_update':
                this.handleActionStatusUpdate(data);
                break;
            case 'system_notification':
                this.handleSystemNotification(data);
                break;
            case 'credential_validation_result':
                this.handleCredentialValidationResult(data);
                break;
            case 'bulk_operation_update':
                this.handleBulkOperationUpdate(data);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    handleActionStatusUpdate(data) {
        // Update execution status in real-time
        if (this.app.state.currentExecution && 
            this.app.state.currentExecution.execution_id === data.execution_id) {
            
            this.app.updateExecutionProgress(data);
            
            if (data.status === 'completed' && data.result) {
                this.app.showExecutionResults(data.result);
            } else if (data.status === 'failed') {
                this.app.showExecutionError(new Error(data.error || 'Action failed'));
            }
        }
        
        // Emit event for other components
        this.app.eventManager.emit('actionStatusUpdate', data);
    }
    
    handleSystemNotification(data) {
        this.app.notificationManager.show(data.message, data.severity, data.title);
    }
    
    handleCredentialValidationResult(data) {
        this.app.credentialManager.handleValidationResult(data);
    }
    
    handleBulkOperationUpdate(data) {
        // Update bulk operation progress
        this.app.updateBulkOperationProgress(data);
    }
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            // Queue message for when connection is restored
            this.messageQueue.push(message);
        }
    }
    
    disconnect() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        if (this.ws) {
            this.ws.close(1000, 'User disconnected');
            this.ws = null;
        }
        
        this.app.state.isWebSocketConnected = false;
    }
}

// === CREDENTIAL MANAGER === //
class CredentialManager {
    constructor(app) {
        this.app = app;
    }
    
    async initialize() {
        await this.loadCredentials();
        this.setupCredentialUI();
    }
    
    async loadCredentials() {
        try {
            if (this.app.state.isAuthenticated) {
                this.app.state.credentials = await this.app.apiClient.getCredentials();
            }
        } catch (error) {
            console.error('Failed to load credentials:', error);
        }
    }
    
    setupCredentialUI() {
        // Setup credential management modal
        const modal = document.getElementById('credential-manager-modal');
        if (!modal) return;
        
        const openBtn = document.getElementById('manage-credentials-btn');
        const closeBtn = document.getElementById('close-credential-manager');
        const addBtn = document.getElementById('add-credential-btn');
        
        if (openBtn) {
            openBtn.addEventListener('click', () => this.showCredentialManager());
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideCredentialManager());
        }
        
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddCredentialForm());
        }
    }
    
    async showCredentialManager() {
        const modal = document.getElementById('credential-manager-modal');
        if (!modal) return;
        
        await this.loadCredentials();
        this.renderCredentialList();
        modal.style.display = 'flex';
    }
    
    hideCredentialManager() {
        const modal = document.getElementById('credential-manager-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    renderCredentialList() {
        const container = document.getElementById('credentials-list');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.app.state.credentials.forEach(credential => {
            const item = this.createCredentialItem(credential);
            container.appendChild(item);
        });
    }
    
    createCredentialItem(credential) {
        const div = document.createElement('div');
        div.className = 'credential-item';
        div.innerHTML = `
            <div class="credential-header">
                <h4>${credential.name}</h4>
                <div class="credential-status ${
                    credential.is_valid ? 'status-valid' : 'status-invalid'
                }">
                    ${credential.is_valid ? 'Valid' : 'Invalid'}
                </div>
            </div>
            <div class="credential-details">
                <p><strong>Domain:</strong> ${credential.domain}</p>
                <p><strong>Type:</strong> ${credential.credential_type}</p>
                <p><strong>Last Used:</strong> ${credential.last_used ? new Date(credential.last_used).toLocaleDateString() : 'Never'}</p>
            </div>
            <div class="credential-actions">
                <button class="btn btn-small btn-secondary" onclick="window.steelApp.credentialManager.validateCredential('${credential.id}')">Validate</button>
                <button class="btn btn-small btn-secondary" onclick="window.steelApp.credentialManager.editCredential('${credential.id}')">Edit</button>
                <button class="btn btn-small btn-danger" onclick="window.steelApp.credentialManager.deleteCredential('${credential.id}')">Delete</button>
            </div>
        `;
        return div;
    }
    
    async validateCredential(credentialId) {
        try {
            const result = await this.app.apiClient.validateCredential(credentialId);
            
            if (result.is_valid) {
                this.app.notificationManager.showSuccess('Credential is valid');
            } else {
                this.app.notificationManager.showWarning(`Credential validation failed: ${result.validation_message}`);
            }
            
            await this.loadCredentials();
            this.renderCredentialList();
            
        } catch (error) {
            this.app.notificationManager.showError('Failed to validate credential');
        }
    }
    
    async deleteCredential(credentialId) {
        if (!confirm('Are you sure you want to delete this credential?')) {
            return;
        }
        
        try {
            await this.app.apiClient.deleteCredential(credentialId);
            this.app.notificationManager.showSuccess('Credential deleted successfully');
            
            await this.loadCredentials();
            this.renderCredentialList();
            
        } catch (error) {
            this.app.notificationManager.showError('Failed to delete credential');
        }
    }
    
    handleValidationResult(data) {
        // Handle real-time credential validation results
        if (data.is_valid) {
            this.app.notificationManager.showSuccess(
                `Credential "${data.credential_name}" validated successfully`
            );
        } else {
            this.app.notificationManager.showError(
                `Credential validation failed: ${data.validation_message}`
            );
        }
        
        // Refresh credential list if modal is open
        const modal = document.getElementById('credential-manager-modal');
        if (modal && modal.style.display === 'flex') {
            this.loadCredentials().then(() => this.renderCredentialList());
        }
    }
}

// === TEMPLATE MANAGER === //
class TemplateManager {
    constructor(app) {
        this.app = app;
    }
    
    async initialize() {
        await this.loadTemplates();
        this.setupTemplateUI();
    }
    
    async loadTemplates() {
        try {
            this.app.state.templates = await this.app.apiClient.getTemplates();
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }
    
    setupTemplateUI() {
        const modal = document.getElementById('template-marketplace-modal');
        if (!modal) return;
        
        const openBtn = document.getElementById('browse-templates-btn');
        const closeBtn = document.getElementById('close-template-marketplace');
        
        if (openBtn) {
            openBtn.addEventListener('click', () => this.showTemplateMarketplace());
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideTemplateMarketplace());
        }
        
        // Setup template filters
        this.setupTemplateFilters();
    }
    
    setupTemplateFilters() {
        const categoryFilter = document.getElementById('template-category-filter');
        const difficultyFilter = document.getElementById('template-difficulty-filter');
        const searchInput = document.getElementById('template-search');
        
        [categoryFilter, difficultyFilter].forEach(filter => {
            if (filter) {
                filter.addEventListener('change', () => this.applyTemplateFilters());
            }
        });
        
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => this.applyTemplateFilters(), 300);
            });
        }
    }
    
    async showTemplateMarketplace() {
        const modal = document.getElementById('template-marketplace-modal');
        if (!modal) return;
        
        await this.loadTemplates();
        await this.loadTemplateCategories();
        this.renderTemplateGrid();
        modal.style.display = 'flex';
    }
    
    hideTemplateMarketplace() {
        const modal = document.getElementById('template-marketplace-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    async loadTemplateCategories() {
        try {
            const categories = await this.app.apiClient.getTemplateCategories();
            this.renderCategoryFilter(categories);
        } catch (error) {
            console.error('Failed to load template categories:', error);
        }
    }
    
    renderCategoryFilter(categories) {
        const select = document.getElementById('template-category-filter');
        if (!select) return;
        
        select.innerHTML = '<option value="">All Categories</option>';
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = `${category.name} (${category.count})`;
            select.appendChild(option);
        });
    }
    
    renderTemplateGrid() {
        const grid = document.getElementById('template-grid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        this.app.state.templates.forEach(template => {
            const card = this.createTemplateCard(template);
            grid.appendChild(card);
        });
    }
    
    createTemplateCard(template) {
        const div = document.createElement('div');
        div.className = 'template-card';
        div.innerHTML = `
            <div class="template-card-header">
                <h3>${template.name}</h3>
                <div class="template-rating">
                    <span class="rating-stars">${this.renderStars(template.rating)}</span>
                    <span class="rating-value">${template.rating.toFixed(1)}</span>
                </div>
            </div>
            <div class="template-card-body">
                <p>${template.description}</p>
                <div class="template-tags">
                    ${template.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="template-stats">
                    <div class="stat">
                        <span class="stat-icon">👤</span>
                        <span>${template.author}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">🏃</span>
                        <span>~${template.estimated_runtime}s</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">📈</span>
                        <span>${template.difficulty_level}</span>
                    </div>
                </div>
            </div>
            <div class="template-card-footer">
                <button class="btn btn-secondary btn-small" onclick="window.steelApp.templateManager.previewTemplate('${template.id}')">Preview</button>
                <button class="btn btn-primary btn-small" onclick="window.steelApp.templateManager.useTemplate('${template.id}')">Use Template</button>
            </div>
        `;
        return div;
    }
    
    renderStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        
        return '★'.repeat(fullStars) + 
               (hasHalfStar ? '☆' : '') + 
               '☆'.repeat(emptyStars);
    }
    
    async useTemplate(templateId) {
        // Show template configuration modal
        this.showTemplateConfigurationModal(templateId);
    }
    
    async showTemplateConfigurationModal(templateId) {
        try {
            const template = await this.app.apiClient.getTemplate(templateId);
            
            // Create and show configuration modal
            const modal = this.createTemplateConfigModal(template);
            document.body.appendChild(modal);
            modal.style.display = 'flex';
            
        } catch (error) {
            this.app.notificationManager.showError('Failed to load template details');
        }
    }
    
    applyTemplateFilters() {
        const category = document.getElementById('template-category-filter')?.value;
        const difficulty = document.getElementById('template-difficulty-filter')?.value;
        const searchQuery = document.getElementById('template-search')?.value;
        
        // Filter templates based on criteria
        let filteredTemplates = [...this.app.state.templates];
        
        if (category) {
            filteredTemplates = filteredTemplates.filter(t => t.category === category);
        }
        
        if (difficulty) {
            filteredTemplates = filteredTemplates.filter(t => t.difficulty_level === difficulty);
        }
        
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filteredTemplates = filteredTemplates.filter(t => 
                t.name.toLowerCase().includes(query) ||
                t.description.toLowerCase().includes(query) ||
                t.tags.some(tag => tag.toLowerCase().includes(query))
            );
        }
        
        this.renderFilteredTemplates(filteredTemplates);
    }
    
    renderFilteredTemplates(templates) {
        const grid = document.getElementById('template-grid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        if (templates.length === 0) {
            grid.innerHTML = '<div class="empty-state"><h3>No templates found</h3><p>Try adjusting your filters</p></div>';
            return;
        }
        
        templates.forEach(template => {
            const card = this.createTemplateCard(template);
            grid.appendChild(card);
        });
    }
}

// === KEYBOARD MANAGER === //
class KeyboardManager {
    constructor(app) {
        this.app = app;
        this.shortcuts = {
            'ctrl+/': () => this.app.focusSearch(),
            'ctrl+shift+enter': () => this.app.executeCurrentAction(),
            'ctrl+n': () => this.app.createNewAction(),
            'ctrl+s': () => this.app.saveCurrentAction(),
            'ctrl+d': () => this.app.duplicateCurrentAction(),
            'ctrl+shift+d': () => this.app.toggleTheme(),
            'ctrl+k': () => this.app.showCommandPalette(),
            'ctrl+shift+k': () => this.app.clearBulkSelection(),
            'escape': () => this.app.closeActiveModal()
        };
    }
    
    initialize() {
        if (!this.app.state.userPreferences.keyboardShortcuts) {
            return;
        }
        
        document.addEventListener('keydown', this.handleKeydown.bind(this));
    }
    
    handleKeydown(event) {
        // Skip if user is typing in an input field
        if (event.target.tagName === 'INPUT' || 
            event.target.tagName === 'TEXTAREA' || 
            event.target.isContentEditable) {
            return;
        }
        
        const shortcut = this.getShortcutString(event);
        const handler = this.shortcuts[shortcut];
        
        if (handler) {
            event.preventDefault();
            handler();
        }
    }
    
    getShortcutString(event) {
        const parts = [];
        
        if (event.ctrlKey || event.metaKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        
        const key = event.key.toLowerCase();
        if (key !== 'control' && key !== 'alt' && key !== 'shift' && key !== 'meta') {
            parts.push(key);
        }
        
        return parts.join('+');
    }
    
    addShortcut(shortcut, handler) {
        this.shortcuts[shortcut] = handler;
    }
    
    removeShortcut(shortcut) {
        delete this.shortcuts[shortcut];
    }
}

// === NOTIFICATION MANAGER === //
class NotificationManager {
    constructor(app) {
        this.app = app;
        this.container = null;
        this.notifications = new Map();
        this.enabled = true;
        this.createContainer();
    }
    
    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
        
        // Add styles
        if (!document.querySelector('#notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'notification-styles';
            styles.textContent = `
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    pointer-events: none;
                }
                .notification {
                    background: var(--bg-primary, #ffffff);
                    border: 1px solid var(--border-color, #e2e8f0);
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    max-width: 400px;
                    pointer-events: auto;
                    animation: slideInRight 0.3s ease-out;
                    position: relative;
                }
                .notification-success { border-left: 4px solid #10b981; }
                .notification-error { border-left: 4px solid #ef4444; }
                .notification-warning { border-left: 4px solid #f59e0b; }
                .notification-info { border-left: 4px solid #3b82f6; }
                .notification-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 8px;
                }
                .notification-title {
                    font-weight: 600;
                    color: var(--text-primary, #1f2937);
                }
                .notification-message {
                    color: var(--text-secondary, #6b7280);
                    line-height: 1.4;
                }
                .notification-close {
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    color: var(--text-muted, #9ca3af);
                    padding: 0;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .notification-progress {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: var(--bg-secondary, #f3f4f6);
                    border-radius: 0 0 8px 8px;
                    overflow: hidden;
                }
                .notification-progress-bar {
                    height: 100%;
                    background: var(--primary-color, #3b82f6);
                    animation: progressBar 5s linear forwards;
                }
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                @keyframes progressBar {
                    from { width: 100%; }
                    to { width: 0%; }
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    show(message, type = 'info', title = null, options = {}) {
        if (!this.enabled && type !== 'error') {
            return null;
        }
        
        const id = Date.now().toString();
        const notification = this.createNotification(id, message, type, title, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Auto-remove after timeout
        const timeout = options.timeout || this.app.config.notificationTimeout;
        if (timeout > 0) {
            setTimeout(() => this.remove(id), timeout);
        }
        
        return id;
    }
    
    showSuccess(message, title = 'Success') {
        return this.show(message, 'success', title);
    }
    
    showError(message, title = 'Error') {
        return this.show(message, 'error', title, { timeout: 0 });
    }
    
    showWarning(message, title = 'Warning') {
        return this.show(message, 'warning', title);
    }
    
    showInfo(message, title = 'Info') {
        return this.show(message, 'info', title);
    }
    
    createNotification(id, message, type, title, options) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.setAttribute('data-notification-id', id);
        
        const hasTitle = title && title !== message;
        
        notification.innerHTML = `
            <div class="notification-header">
                ${hasTitle ? `<div class="notification-title">${title}</div>` : ''}
                <button class="notification-close" aria-label="Close">&times;</button>
            </div>
            <div class="notification-message">${message}</div>
            ${options.timeout > 0 ? '<div class="notification-progress"><div class="notification-progress-bar"></div></div>' : ''}
        `;
        
        // Setup close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => this.remove(id));
        
        return notification;
    }
    
    remove(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(id);
        }, 300);
    }
    
    clear() {
        this.notifications.forEach((_, id) => this.remove(id));
    }
    
    disable() {
        this.enabled = false;
    }
    
    enable() {
        this.enabled = true;
    }
}

// Make SteelApp globally available
window.SteelApp = SteelApp;
window.steelApp = null;

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.steelApp = new SteelApp();
});