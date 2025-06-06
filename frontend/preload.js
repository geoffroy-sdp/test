const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // Backend communication
    getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
    restartBackend: () => ipcRenderer.invoke('restart-backend'),
    
    // Dialog functions
    showErrorDialog: (title, content) => ipcRenderer.invoke('show-error-dialog', title, content),
    showInfoDialog: (title, content) => ipcRenderer.invoke('show-info-dialog', title, content),
    
    // App info
    getAppInfo: () => ipcRenderer.invoke('get-app-info'),
    
    // Event listeners for backend status updates
    onBackendStatusChange: (callback) => {
        ipcRenderer.on('backend-status-changed', callback);
        return () => ipcRenderer.removeListener('backend-status-changed', callback);
    }
});

// Create API client object first, then expose it
const apiClient = {
    // Base URL for backend API
    baseURL: 'http://localhost:8080',
    
    // Generic request function
    request: async (method, endpoint, data = null) => {
        const url = `http://localhost:8080${endpoint}`;
        const options = {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data && (method.toLowerCase() === 'post' || method.toLowerCase() === 'put')) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }
            
            return result;
        } catch (error) {
            console.error(`API Error [${method} ${endpoint}]:`, error);
            throw error;
        }
    }
};

// Add convenience methods to the apiClient object
apiClient.get = (endpoint) => {
    return apiClient.request('GET', endpoint);
};

apiClient.post = (endpoint, data) => {
    return apiClient.request('POST', endpoint, data);
};

apiClient.put = (endpoint, data) => {
    return apiClient.request('PUT', endpoint, data);
};

apiClient.delete = (endpoint) => {
    return apiClient.request('DELETE', endpoint);
};

// Now expose the complete apiClient
contextBridge.exposeInMainWorld('apiClient', apiClient);

// Console utilities for debugging
contextBridge.exposeInMainWorld('debug', {
    log: (...args) => console.log('[Renderer]', ...args),
    error: (...args) => console.error('[Renderer]', ...args),
    warn: (...args) => console.warn('[Renderer]', ...args),
    info: (...args) => console.info('[Renderer]', ...args)
});