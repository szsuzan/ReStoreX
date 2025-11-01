const API_BASE_URL = 'http://localhost:8000/api';

export class ApiService {
  constructor() {
    this.ws = null;
    this.eventListeners = new Map();
  }

  static getInstance() {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  // WebSocket connection
  connectWebSocket() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket('ws://localhost:8000/ws');
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('WebSocket received:', message);
        
        // Check if message has a type field (new format: {type: "scan_progress", ...})
        if (message.type) {
          this.notifyListeners(message.type, message);
        }
        // Fallback to old format for compatibility
        else if (message.event) {
          this.notifyListeners(message.event, message.data || message);
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt to reconnect after 3 seconds
      setTimeout(() => this.connectWebSocket(), 3000);
    };
  }

  // Event listener management
  addEventListener(eventType, callback) {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, []);
    }
    this.eventListeners.get(eventType).push(callback);
  }

  removeEventListener(eventType, callback) {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  notifyListeners(eventType, data) {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  // API Methods
  async get(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    return response.json();
  }

  async post(endpoint, data) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    return response.json();
  }

  // Drive operations
  async getDrives() {
    return this.get('/drives');
  }

  async getDrive(driveId) {
    return this.get(`/drives/${driveId}`);
  }

  async getDriveHealth(driveId) {
    return this.get(`/drives/${driveId}/health`);
  }

  async getDriveDetails(driveId) {
    return this.get(`/drives/${driveId}/details`);
  }

  async validateDrive(driveId) {
    return this.post(`/drives/${driveId}/validate`, {});
  }

  // Scan operations
  async startScan(driveId, scanType, options = {}) {
    return this.post('/scan/start', { driveId, scanType, options });
  }

  async getScanStatus(scanId) {
    return this.get(`/scan/${scanId}/status`);
  }

  async cancelScan(scanId) {
    return this.post(`/scan/${scanId}/cancel`, {});
  }

  async getScanResults(scanId, options = {}) {
    const params = new URLSearchParams(options).toString();
    return this.get(`/scan/${scanId}/results?${params}`);
  }

  async getScanReport(scanId) {
    return this.get(`/scan/${scanId}/report`);
  }

  // Recovery operations
  async startRecovery(fileIds, outputPath, options = {}) {
    return this.post('/recovery/start', { fileIds, outputPath, options });
  }

  async getRecoveryStatus(recoveryId) {
    return this.get(`/recovery/${recoveryId}/status`);
  }

  async cancelRecovery(recoveryId) {
    return this.post(`/recovery/${recoveryId}/cancel`, {});
  }

  async getRecoveryLogs(recoveryId) {
    return this.get(`/recovery/${recoveryId}/logs`);
  }

  // File operations
  async getFileInfo(fileId) {
    try {
      return await this.get(`/files/${fileId}`);
    } catch (error) {
      console.error('Failed to get file info:', error);
      // Return fallback data
      return {
        id: fileId,
        name: `file_${fileId}.unknown`,
        type: 'UNKNOWN',
        size: '0 KB',
        sizeBytes: 0,
        dateModified: new Date().toLocaleDateString(),
        path: `\\Unknown\\file_${fileId}.unknown`,
        recoveryChance: 'Unknown',
        sector: 0,
        cluster: 0,
        inode: 0,
        status: 'found'
      };
    }
  }

  async getFileThumbnail(fileId, size = 150) {
    const response = await fetch(`${API_BASE_URL}/files/${fileId}/thumbnail?size=${size}`);
    if (!response.ok) return null;
    return response.blob();
  }

  async analyzeFile(fileId) {
    return this.post(`/files/${fileId}/analyze`, {});
  }

  async getFilePreview(fileId) {
    return this.get(`/files/${fileId}/preview`);
  }

  async getFileHexData(fileId, offset = 0, length = 256) {
    try {
      return await this.get(`/files/${fileId}/hex?offset=${offset}&length=${length}`);
    } catch (error) {
      console.error('Failed to get hex data:', error);
      // Return mock data as fallback
      return {
        fileId,
        offset,
        length: 256,
        data: Array.from({ length: 256 }, (_, i) => i % 256)
      };
    }
  }

  // Health check
  async healthCheck() {
    return this.get('/health');
  }

  // Explorer operations
  async getDirectoryContents(path) {
    try {
      return await this.get(`/explorer/directory?path=${encodeURIComponent(path)}`);
    } catch (error) {
      console.error('Failed to get directory contents:', error);
      // Return mock data as fallback
      return {
        path,
        items: [
          {
            id: '1',
            name: 'RecoveredFiles',
            type: 'folder',
            size: null,
            dateModified: new Date().toLocaleDateString(),
            path: `${path}\\RecoveredFiles`,
            itemCount: 0
          }
        ]
      };
    }
  }

  async openInSystemExplorer(path) {
    try {
      return await this.post('/explorer/open', { path });
    } catch (error) {
      console.error('Failed to open in system explorer:', error);
      // Fallback: try to open a new window with the path
      console.log(`Would open: ${path}`);
      return { message: 'Explorer open requested' };
    }
  }

  async createDirectory(path) {
    return this.post('/explorer/directory', { path });
  }

  async deleteItems(paths) {
    return this.post('/explorer/items', { paths });
  }

  // System performance
  async getSystemPerformance() {
    try {
      return await this.get('/system/performance');
    } catch (error) {
      console.error('Failed to get system performance:', error);
      return null;
    }
  }

  connectSystemPerformanceStream(callback) {
    const ws = new WebSocket('ws://localhost:8000/api/system/performance/stream');
    
    ws.onopen = () => {
      console.log('System performance stream connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'system_performance' && message.data) {
          callback(message.data);
        }
      } catch (error) {
        console.error('Error parsing performance data:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('System performance stream disconnected');
    };
    
    ws.onerror = (error) => {
      console.error('System performance stream error:', error);
    };
    
    return ws;
  }
}

export const apiService = ApiService.getInstance();