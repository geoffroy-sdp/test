// Bot Ops Lobby Tool - Renderer Process
class BotOpsApp {
    constructor() {
        this.isControllerConnected = false;
        this.isMovementRunning = false;
        this.isAntiAfkRunning = false;
        this.availableProfiles = 0;
        this.currentSettings = {};
        this.logContainer = null;
        this.activeSessions = [];
        this.lobbyContainer = null;
        
        this.init();
    }

    async init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }

        // Initialize components
        await this.checkBackendStatus();
        await this.loadProfiles();
        await this.loadSettings();
        
        this.addLog('Application initialized successfully', 'success');
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', () => this.switchTab(button.dataset.tab));
        });

        // Main controls
        document.getElementById('browser-button').addEventListener('click', () => this.handleBrowserAction());
        document.getElementById('connect-button').addEventListener('click', () => this.toggleController());
        document.getElementById('movement-button').addEventListener('click', () => this.toggleMovement());
        document.getElementById('anti-afk-button').addEventListener('click', () => this.toggleAntiAfk());
        document.getElementById('select-class-button').addEventListener('click', () => this.selectClass());

        // Lobby controls
        document.getElementById('close-sessions-button').addEventListener('click', () => this.closeAllSessions());

        // Settings
        document.querySelector('.btn-success').addEventListener('click', () => this.saveSettings());

        // Bot count slider - Fixed implementation
        const botCountSlider = document.getElementById('bot-count');
        const botCountValue = document.getElementById('bot-count-value');
        
        if (botCountSlider && botCountValue) {
            // Set initial value
            botCountValue.textContent = botCountSlider.value || '1';
            
            // Add input event listener
            botCountSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value) || 1;
                botCountValue.textContent = value.toString();
                this.addLog(`Selected ${value} bot${value === 1 ? '' : 's'}`, 'info');
            });
            
            // Add change event listener for final value
            botCountSlider.addEventListener('change', (e) => {
                const value = parseInt(e.target.value) || 1;
                botCountValue.textContent = value.toString();
                this.addLog(`Bot count set to ${value}`, 'info');
            });
        }

        // Initialize container references
        this.logContainer = document.getElementById('log-container');
        this.lobbyContainer = document.getElementById('lobby-container');

        // Setup sliders with real-time updates
        this.setupSliders();
    }

    setupSliders() {
        // Get all sliders and add event listeners
        document.querySelectorAll('.slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const container = e.target.closest('.slider-container');
                if (!container) return;
                
                const valueDisplay = container.querySelector('.slider-value');
                const labelElement = container.querySelector('.slider-label');
                
                if (!valueDisplay || !labelElement) return;
                
                const label = labelElement.textContent;
                const value = parseFloat(e.target.value);
                
                // Update display
                const unit = valueDisplay.textContent.includes('s') ? 's' : '';
                valueDisplay.textContent = value.toFixed(2) + unit;
                
                // Store setting temporarily
                this.currentSettings[this.getSettingKey(label)] = value;
            });
        });
    }

    getSettingKey(label) {
        // Convert label to setting key
        return label.toLowerCase()
            .replace(/\s+/g, '_')
            .replace(/[^\w]/g, '');
    }

    switchTab(tabName) {
        // Update active tab button
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (targetButton) {
            targetButton.classList.add('active');
        }
        
        // Update active tab pane
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        const targetPane = document.getElementById(tabName);
        if (targetPane) {
            targetPane.classList.add('active');
        }
        
        this.addLog(`Switched to ${tabName} tab`, 'info');
    }

    async checkBackendStatus() {
        try {
            const status = await window.electronAPI.getBackendStatus();
            if (status.running) {
                this.addLog('Backend connection established', 'success');
                // Also check the backend API status
                try {
                    const apiStatus = await window.apiClient.get('/api/status');
                    this.addLog(`Backend API status: ${apiStatus.status}`, 'success');
                } catch (apiError) {
                    this.addLog('Backend process running but API not responding', 'warning');
                }
            } else {
                this.addLog('Backend not running', 'error');
                await this.handleBackendError();
            }
        } catch (error) {
            this.addLog('Failed to check backend status', 'error');
            console.error('Backend status error:', error);
        }
    }

    async handleBackendError() {
        const restart = confirm('Backend is not running. Would you like to restart it?');
        if (restart) {
            try {
                this.addLog('Restarting backend...', 'info');
                await window.electronAPI.restartBackend();
                this.addLog('Backend restarted successfully', 'success');
                // Wait a moment for backend to fully start
                setTimeout(() => this.checkBackendStatus(), 3000);
            } catch (error) {
                this.addLog('Failed to restart backend', 'error');
                await window.electronAPI.showErrorDialog('Backend Error', 'Could not start the Python backend. Please check the console for details.');
            }
        }
    }

    async loadProfiles() {
        try {
            const response = await window.apiClient.get('/api/profiles');
            this.availableProfiles = response.count || (response.profiles ? response.profiles.length : 0);
            
            // Update UI
            const profilesCountElement = document.getElementById('profiles-count');
            if (profilesCountElement) {
                profilesCountElement.textContent = `Available Profiles: ${this.availableProfiles}/20`;
            }
            
            // Update bot count slider max value
            const botCountSlider = document.getElementById('bot-count');
            const botCountValue = document.getElementById('bot-count-value');
            
            if (botCountSlider && botCountValue) {
                // Set max value to available profiles, minimum 1
                const maxValue = Math.max(1, this.availableProfiles);
                botCountSlider.max = maxValue;
                
                // Set initial value
                const initialValue = Math.min(parseInt(botCountSlider.value) || 1, maxValue);
                botCountSlider.value = initialValue;
                botCountValue.textContent = initialValue.toString();
                
                // Enable/disable slider based on available profiles
                botCountSlider.disabled = this.availableProfiles === 0;
            }
            
            this.addLog(`Found ${this.availableProfiles} available profiles`, this.availableProfiles > 0 ? 'success' : 'warning');
        } catch (error) {
            this.addLog('Failed to load profiles', 'error');
            console.error('Profile loading error:', error);
            // Set defaults if API call fails
            this.availableProfiles = 0;
            const profilesCountElement = document.getElementById('profiles-count');
            if (profilesCountElement) {
                profilesCountElement.textContent = 'Available Profiles: 0/20';
            }
            
            // Set slider to minimum values
            const botCountSlider = document.getElementById('bot-count');
            const botCountValue = document.getElementById('bot-count-value');
            if (botCountSlider && botCountValue) {
                botCountSlider.max = 1;
                botCountSlider.value = 1;
                botCountValue.textContent = '1';
                botCountSlider.disabled = true;
            }
        }
    }

    async loadSettings() {
        try {
            const response = await window.apiClient.get('/api/config');
            this.currentSettings = response.settings || {};
            
            // Update slider values
            this.updateSlidersFromSettings(this.currentSettings);
            
            this.addLog('Settings loaded successfully', 'success');
        } catch (error) {
            this.addLog('Failed to load settings', 'error');
            console.error('Settings loading error:', error);
            // Initialize with empty settings if loading fails
            this.currentSettings = {};
        }
    }

    updateSlidersFromSettings(settings) {
        document.querySelectorAll('.slider-container').forEach(container => {
            const labelElement = container.querySelector('.slider-label');
            const slider = container.querySelector('.slider');
            const valueDisplay = container.querySelector('.slider-value');
            
            if (!labelElement || !slider || !valueDisplay) return;
            
            const label = labelElement.textContent;
            const key = this.getSettingKey(label);
            
            if (settings[key] !== undefined) {
                slider.value = settings[key];
                const unit = valueDisplay.textContent.includes('s') ? 's' : '';
                valueDisplay.textContent = parseFloat(settings[key]).toFixed(2) + unit;
            }
        });
    }

    async handleBrowserAction() {
        const button = document.getElementById('browser-button');
        const botCountSlider = document.getElementById('bot-count');
        
        if (!botCountSlider) {
            this.addLog('Bot count slider not found', 'error');
            return;
        }
        
        const botCount = parseInt(botCountSlider.value) || 1;
        
        if (button.textContent === 'Open Xbox Sessions') {
            try {
                // Validate bot count
                if (botCount < 1) {
                    this.addLog('Invalid bot count: must be at least 1', 'error');
                    return;
                }
                
                if (this.availableProfiles > 0 && botCount > this.availableProfiles) {
                    this.addLog(`Cannot open ${botCount} sessions: only ${this.availableProfiles} profiles available`, 'error');
                    return;
                }
                
                this.addLog(`Opening ${botCount} Xbox session${botCount === 1 ? '' : 's'}...`, 'info');
                
                const requestData = {
                    count: botCount
                };
                
                console.log('Sending browser open request:', requestData);
                
                const response = await window.apiClient.post('/api/browser/open', requestData);
                
                console.log('Browser open response:', response);
                
                if (response.success) {
                    // Create webviews for each session
                    await this.createWebViewSessions(response.profiles, response.base_url);
                    
                    button.textContent = 'Launch Black Ops 6';
                    button.style.backgroundColor = 'var(--accent-secondary)';
                    this.updateSessionsUI();
                    this.addLog('Xbox sessions opened successfully', 'success');
                } else {
                    throw new Error(response.error || 'Unknown error');
                }
            } catch (error) {
                this.addLog(`Failed to open Xbox sessions: ${error.message}`, 'error');
                console.error('Browser action error:', error);
            }
        } else {
            try {
                this.addLog('Launching Black Ops 6...', 'info');
                
                const response = await window.apiClient.post('/api/browser/launch');
                
                if (response.success) {
                    // Navigate existing webviews to Black Ops 6
                    await this.launchBlackOpsInSessions(response.launch_url);
                    this.addLog('Black Ops 6 launched successfully', 'success');
                } else {
                    throw new Error(response.error || 'Unknown error');
                }
            } catch (error) {
                this.addLog(`Failed to launch Black Ops 6: ${error.message}`, 'error');
                console.error('Launch error:', error);
            }
        }
    }

    async createWebViewSessions(profiles, baseUrl) {
        // Clear existing sessions
        this.clearWebViewSessions();
        
        // Hide no sessions message
        const noSessionsMessage = document.getElementById('no-sessions-message');
        if (noSessionsMessage) {
            noSessionsMessage.style.display = 'none';
        }
        
        if (!profiles || profiles.length === 0) {
            this.addLog('No profiles provided for session creation', 'error');
            return;
        }
        
        for (let i = 0; i < profiles.length; i++) {
            const profile = profiles[i];
            
            // Create session container
            const sessionContainer = document.createElement('div');
            sessionContainer.className = 'session-container';
            sessionContainer.id = `session-${profile.name}`;
            
            // Create session header
            const sessionHeader = document.createElement('div');
            sessionHeader.className = 'session-header';
            sessionHeader.innerHTML = `
                <span class="session-title">${profile.display_name || profile.name.toUpperCase()}</span>
                <button class="session-close-btn" onclick="window.botOpsApp.closeSession('${profile.name}')">×</button>
            `;
            
            // Create webview
            const webview = document.createElement('webview');
            webview.src = baseUrl || 'https://xbox.com/play';
            webview.className = 'session-webview';
            webview.partition = `persist:${profile.name}`;
            webview.allowpopups = true;
            webview.useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
            
            // Add webview event listeners
            webview.addEventListener('dom-ready', () => {
                this.addLog(`Session ${profile.name} loaded`, 'success');
            });
            
            webview.addEventListener('did-fail-load', (event) => {
                this.addLog(`Session ${profile.name} failed to load: ${event.errorDescription}`, 'error');
            });
            
            webview.addEventListener('did-start-loading', () => {
                this.addLog(`Session ${profile.name} starting to load...`, 'info');
            });
            
            webview.addEventListener('did-stop-loading', () => {
                this.addLog(`Session ${profile.name} finished loading`, 'info');
            });
            
            // Assemble session
            sessionContainer.appendChild(sessionHeader);
            sessionContainer.appendChild(webview);
            
            // Add to lobby container
            if (this.lobbyContainer) {
                this.lobbyContainer.appendChild(sessionContainer);
            } else {
                console.error('Lobby container not found');
            }
            
            // Store session reference
            this.activeSessions.push({
                name: profile.name,
                container: sessionContainer,
                webview: webview,
                profile: profile
            });
            
            // Small delay between session creation
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        this.addLog(`Created ${profiles.length} webview session${profiles.length === 1 ? '' : 's'}`, 'success');
    }

    async launchBlackOpsInSessions(launchUrl) {
        if (!launchUrl) {
            this.addLog('No launch URL provided', 'error');
            return;
        }
        
        for (const session of this.activeSessions) {
            try {
                session.webview.src = launchUrl;
                this.addLog(`Navigating ${session.name} to Black Ops 6`, 'info');
                
                // Small delay between navigations
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (error) {
                this.addLog(`Failed to navigate ${session.name}: ${error.message}`, 'error');
            }
        }
    }

    closeSession(sessionName) {
        const sessionIndex = this.activeSessions.findIndex(s => s.name === sessionName);
        if (sessionIndex !== -1) {
            const session = this.activeSessions[sessionIndex];
            
            // Remove from DOM
            if (session.container && session.container.parentNode) {
                session.container.remove();
            }
            
            // Remove from active sessions
            this.activeSessions.splice(sessionIndex, 1);
            
            this.addLog(`Closed session ${sessionName}`, 'info');
            this.updateSessionsUI();
        }
    }

    async closeAllSessions() {
        try {
            // Clear all webviews
            this.clearWebViewSessions();
            
            // Update backend state
            await window.apiClient.post('/api/browser/close');
            
            // Reset UI
            const button = document.getElementById('browser-button');
            if (button) {
                button.textContent = 'Open Xbox Sessions';
                button.style.backgroundColor = '';
            }
            
            this.updateSessionsUI();
            this.addLog('All sessions closed', 'info');
        } catch (error) {
            this.addLog(`Failed to close sessions: ${error.message}`, 'error');
            console.error('Close sessions error:', error);
        }
    }

    clearWebViewSessions() {
        // Remove all session containers
        this.activeSessions.forEach(session => {
            if (session.container && session.container.parentNode) {
                session.container.remove();
            }
        });
        
        // Clear sessions array
        this.activeSessions = [];
        
        // Show no sessions message
        const noSessionsMessage = document.getElementById('no-sessions-message');
        if (noSessionsMessage) {
            noSessionsMessage.style.display = 'block';
        }
    }

    updateSessionsUI() {
        const activeCount = this.activeSessions.length;
        const closeButton = document.getElementById('close-sessions-button');
        const sessionCountSpan = document.getElementById('active-sessions-count');
        
        // Update counter
        if (sessionCountSpan) {
            sessionCountSpan.textContent = `Active Sessions: ${activeCount}`;
        }
        
        // Enable/disable close button
        if (closeButton) {
            closeButton.disabled = activeCount === 0;
        }
        
        // Show/hide no sessions message
        const noSessionsMessage = document.getElementById('no-sessions-message');
        if (noSessionsMessage) {
            noSessionsMessage.style.display = activeCount === 0 ? 'block' : 'none';
        }
    }

    async toggleController() {
        try {
            if (!this.isControllerConnected) {
                this.addLog('Connecting controller...', 'info');
                const response = await window.apiClient.post('/api/controller/connect');
                
                if (response.success) {
                    this.isControllerConnected = true;
                    this.updateControllerUI(true);
                    this.addLog('Controller connected successfully', 'success');
                } else {
                    throw new Error(response.error || 'Connection failed');
                }
            } else {
                this.addLog('Disconnecting controller...', 'info');
                const response = await window.apiClient.post('/api/controller/disconnect');
                
                if (response.success) {
                    this.isControllerConnected = false;
                    this.isMovementRunning = false;
                    this.isAntiAfkRunning = false;
                    this.updateControllerUI(false);
                    this.addLog('Controller disconnected', 'info');
                } else {
                    throw new Error(response.error || 'Disconnection failed');
                }
            }
        } catch (error) {
            this.addLog(`Controller error: ${error.message}`, 'error');
            console.error('Controller error:', error);
        }
    }

    updateControllerUI(connected) {
        const connectBtn = document.getElementById('connect-button');
        const movementBtn = document.getElementById('movement-button');
        const antiAfkBtn = document.getElementById('anti-afk-button');
        const selectClassBtn = document.getElementById('select-class-button');
        
        if (connected) {
            if (connectBtn) {
                connectBtn.textContent = 'Disconnect Controller';
                connectBtn.className = 'btn btn-danger';
            }
            
            if (movementBtn) movementBtn.disabled = false;
            if (antiAfkBtn) antiAfkBtn.disabled = false;
            if (selectClassBtn) selectClassBtn.disabled = false;
        } else {
            if (connectBtn) {
                connectBtn.textContent = 'Connect Controller';
                connectBtn.className = 'btn btn-secondary';
            }
            
            if (movementBtn) {
                movementBtn.disabled = true;
                movementBtn.textContent = 'Enable Movement Bot';
                movementBtn.className = 'btn btn-secondary';
            }
            if (antiAfkBtn) {
                antiAfkBtn.disabled = true;
                antiAfkBtn.textContent = 'Enable Anti-AFK';
                antiAfkBtn.className = 'btn btn-secondary';
            }
            if (selectClassBtn) selectClassBtn.disabled = true;
        }
    }

    async toggleMovement() {
        try {
            const response = await window.apiClient.post('/api/movement/toggle');
            
            if (response.success) {
                this.isMovementRunning = response.running;
                const button = document.getElementById('movement-button');
                
                if (button) {
                    if (this.isMovementRunning) {
                        button.textContent = 'Stop Movement';
                        button.className = 'btn btn-danger';
                        this.addLog('Movement bot started', 'success');
                    } else {
                        button.textContent = 'Enable Movement Bot';
                        button.className = 'btn btn-secondary';
                        this.addLog('Movement bot stopped', 'info');
                    }
                }
            } else {
                throw new Error(response.error || 'Toggle failed');
            }
        } catch (error) {
            this.addLog(`Movement error: ${error.message}`, 'error');
            console.error('Movement error:', error);
        }
    }

    async toggleAntiAfk() {
        try {
            const response = await window.apiClient.post('/api/anti-afk/toggle');
            
            if (response.success) {
                this.isAntiAfkRunning = response.running;
                const button = document.getElementById('anti-afk-button');
                
                if (button) {
                    if (this.isAntiAfkRunning) {
                        button.textContent = 'Stop Anti-AFK';
                        button.className = 'btn btn-danger';
                        this.addLog('Anti-AFK started', 'success');
                    } else {
                        button.textContent = 'Enable Anti-AFK';
                        button.className = 'btn btn-secondary';
                        this.addLog('Anti-AFK stopped', 'info');
                    }
                }
            } else {
                throw new Error(response.error || 'Toggle failed');
            }
        } catch (error) {
            this.addLog(`Anti-AFK error: ${error.message}`, 'error');
            console.error('Anti-AFK error:', error);
        }
    }

    async selectClass() {
        try {
            this.addLog('Starting class selection...', 'info');
            const response = await window.apiClient.post('/api/class/select');
            
            if (response.success) {
                this.addLog('Class selection completed', 'success');
            } else {
                throw new Error(response.error || 'Class selection failed');
            }
        } catch (error) {
            this.addLog(`Class selection error: ${error.message}`, 'error');
            console.error('Class selection error:', error);
        }
    }

    async saveSettings() {
        try {
            this.addLog('Saving settings...', 'info');
            
            const response = await window.apiClient.post('/api/config', {
                settings: this.currentSettings
            });
            
            if (response.success) {
                this.addLog('Settings saved successfully', 'success');
            } else {
                throw new Error(response.error || 'Save failed');
            }
        } catch (error) {
            this.addLog(`Failed to save settings: ${error.message}`, 'error');
            console.error('Save settings error:', error);
        }
    }

    addLog(message, type = 'info') {
        if (!this.logContainer) {
            console.log(`[${type.toUpperCase()}] ${message}`);
            return;
        }
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        
        this.logContainer.appendChild(logEntry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
        
        // Limit log entries to prevent memory issues
        if (this.logContainer.children.length > 1000) {
            this.logContainer.removeChild(this.logContainer.firstChild);
        }
    }
}

// Initialize the application when the page loads
window.addEventListener('DOMContentLoaded', () => {
    window.botOpsApp = new BotOpsApp();
});