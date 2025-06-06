const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

class ElectronApp {
    constructor() {
        this.mainWindow = null;
        this.pythonProcess = null;
        this.isDev = process.argv.includes('--dev');
    }

    createWindow() {
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 900,
            minWidth: 800,
            minHeight: 600,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                preload: path.join(__dirname, 'preload.js'),
                webSecurity: false, // Allow webview access
                allowRunningInsecureContent: true
            },
            icon: path.join(__dirname, 'assets', 'icon.png'),
            show: false,
            titleBarStyle: 'default',
            autoHideMenuBar: !this.isDev
        });

        // Load the HTML file
        this.mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

        // Show window when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
            
            if (this.isDev) {
                this.mainWindow.webContents.openDevTools();
            }
        });

        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Handle window close request
        this.mainWindow.on('close', async (event) => {
            if (this.pythonProcess) {
                event.preventDefault();
                await this.stopPythonBackend();
                this.mainWindow.destroy();
            }
        });
    }

    async startPythonBackend() {
        return new Promise((resolve, reject) => {
            const backendPath = path.join(__dirname, '..', 'backend', 'main.py');
            
            console.log('Starting Python backend from:', backendPath);
            
            // Check if Python is available
            this.pythonProcess = spawn('python', [backendPath], {
                cwd: path.join(__dirname, '..', 'backend'),
                stdio: ['pipe', 'pipe', 'pipe']
            });

            let backendStarted = false;

            this.pythonProcess.stdout.on('data', (data) => {
                const output = data.toString();
                console.log(`Backend: ${output}`);
                
                // Check for various startup indicators
                if (output.includes('Running on') || 
                    output.includes('Server running') || 
                    output.includes('Bot Ops Backend starting')) {
                    if (!backendStarted) {
                        backendStarted = true;
                        // Wait a bit more to ensure the server is fully ready
                        setTimeout(() => resolve(), 2000);
                    }
                }
            });

            this.pythonProcess.stderr.on('data', (data) => {
                console.error(`Backend Error: ${data}`);
            });

            this.pythonProcess.on('close', (code) => {
                console.log(`Backend process exited with code ${code}`);
                this.pythonProcess = null;
            });

            this.pythonProcess.on('error', (error) => {
                console.error('Failed to start backend:', error);
                reject(error);
            });

            // Timeout after 15 seconds
            setTimeout(() => {
                if (this.pythonProcess && !backendStarted) {
                    console.log('Backend startup timeout, assuming it started successfully');
                    resolve(); // Assume it started successfully
                }
            }, 15000);
        });
    }

    async stopPythonBackend() {
        if (this.pythonProcess) {
            return new Promise((resolve) => {
                this.pythonProcess.on('close', () => {
                    this.pythonProcess = null;
                    resolve();
                });
                
                this.pythonProcess.kill('SIGTERM');
                
                // Force kill after 5 seconds
                setTimeout(() => {
                    if (this.pythonProcess) {
                        this.pythonProcess.kill('SIGKILL');
                        this.pythonProcess = null;
                    }
                    resolve();
                }, 5000);
            });
        }
    }

    setupIPC() {
        // Handle backend status requests
        ipcMain.handle('get-backend-status', async () => {
            return {
                running: this.pythonProcess !== null,
                pid: this.pythonProcess ? this.pythonProcess.pid : null
            };
        });

        // Handle backend restart
        ipcMain.handle('restart-backend', async () => {
            try {
                await this.stopPythonBackend();
                await this.startPythonBackend();
                return { success: true };
            } catch (error) {
                return { success: false, error: error.message };
            }
        });

        // Handle API requests
        ipcMain.handle('api-request', async (event, method, endpoint, data) => {
            const fetch = require('node-fetch');
            
            try {
                const url = `http://localhost:8080${endpoint}`;
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                };
                
                if (data && (method === 'POST' || method === 'PUT')) {
                    options.body = JSON.stringify(data);
                }
                
                console.log(`API Request: ${method} ${url}`, data || '');
                
                const response = await fetch(url, options);
                const result = await response.json();
                
                console.log(`API Response:`, result);
                
                if (!response.ok) {
                    throw new Error(result.error || `HTTP ${response.status}`);
                }
                
                return result;
            } catch (error) {
                console.error(`API Error: ${method} ${endpoint}`, error);
                throw error;
            }
        });

        // Handle file dialogs
        ipcMain.handle('show-error-dialog', async (event, title, content) => {
            dialog.showErrorBox(title, content);
        });

        ipcMain.handle('show-info-dialog', async (event, title, content) => {
            const result = await dialog.showMessageBox(this.mainWindow, {
                type: 'info',
                title: title,
                message: content,
                buttons: ['OK']
            });
            return result;
        });

        // Handle app info
        ipcMain.handle('get-app-info', async () => {
            return {
                version: app.getVersion(),
                name: app.getName(),
                isDev: this.isDev
            };
        });
    }

    async initialize() {
        // Wait for Electron to be ready
        await app.whenReady();

        // Setup IPC handlers
        this.setupIPC();

        // Create the main window
        this.createWindow();

        // Start Python backend
        try {
            await this.startPythonBackend();
            console.log('Backend started successfully');
        } catch (error) {
            console.error('Failed to start backend:', error);
            dialog.showErrorBox(
                'Backend Error',
                'Failed to start Python backend. Please ensure Python is installed and all dependencies are available.'
            );
        }

        // Handle app activation (macOS)
        app.on('activate', () => {
            if (BrowserWindow.getAllWindows().length === 0) {
                this.createWindow();
            }
        });

        // Handle all windows closed
        app.on('window-all-closed', () => {
            if (process.platform !== 'darwin') {
                app.quit();
            }
        });

        // Handle app before quit
        app.on('before-quit', async (event) => {
            if (this.pythonProcess) {
                event.preventDefault();
                await this.stopPythonBackend();
                app.quit();
            }
        });
    }
}

// Create and initialize the app
const electronApp = new ElectronApp();
electronApp.initialize().catch(console.error);