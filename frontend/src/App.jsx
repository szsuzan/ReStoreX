import React, { useState, useEffect, useRef } from 'react';
import { Activity, HardDrive, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { Sidebar } from './components/SideBar';
import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { FileGrid } from './components/FileGrid';
import { FileDetailsPanel } from './components/FileDetailsPanel';
import { Footer } from './components/Footer';
import { ScanProgressDialog } from './components/ScanProgressDialog';
import { RecoveryProgressDialog } from './components/RecoveryProgressDialog';
import { DriveSelectionDialog } from './components/DriveSelectionDialog';
import { SettingsDialog } from './components/SettingsDialog';
import { ExplorerDialog } from './components/ExplorerDialog';
import { FolderPickerDialog } from './components/FolderPickerDialog';
import { ScanReportsPanel } from './components/ScanReportsPanel';
import { NotificationBox } from './components/NotificationBox';
import { FilePreviewDialog } from './components/FilePreviewDialog';
import { ScanReportDialog } from './components/ScanReportDialog';
import { apiService } from './services/apiService';
import { useWebSocket } from './hooks/useWebSocket';

// Inline components for rendering reports
const ClusterReportContent = ({ reportData }) => {
  if (!reportData || !reportData.data) return <p className="text-gray-500">No cluster data available</p>;
  
  const { statistics, cluster_map } = reportData.data;
  
  return (
    <div className="space-y-6">
      {/* Statistics */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-sm text-blue-600 font-medium">Total Clusters</div>
          <div className="text-2xl font-bold text-blue-900">{statistics?.total_clusters?.toLocaleString() || 'N/A'}</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-sm text-green-600 font-medium">Sampled</div>
          <div className="text-2xl font-bold text-green-900">{statistics?.sampled_clusters?.toLocaleString() || 'N/A'}</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-sm text-gray-600 font-medium">Empty Clusters</div>
          <div className="text-2xl font-bold text-gray-900">{statistics?.empty_clusters?.toLocaleString() || 'N/A'}</div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <div className="text-sm text-purple-600 font-medium">Used Clusters</div>
          <div className="text-2xl font-bold text-purple-900">{statistics?.used_clusters?.toLocaleString() || 'N/A'}</div>
        </div>
      </div>

      {/* Cluster Map Preview */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-3">Cluster Map (First 10 samples)</h4>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {cluster_map && cluster_map.slice(0, 10).map((cluster, idx) => (
            <div key={idx} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-sm font-medium">Cluster #{cluster.cluster_id}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${cluster.is_empty ? 'bg-gray-200 text-gray-700' : 'bg-blue-100 text-blue-700'}`}>
                  {cluster.is_empty ? 'Empty' : 'Used'}
                </span>
              </div>
              <div className="text-xs text-gray-500 mb-2">Offset: 0x{cluster.offset?.toString(16).toUpperCase() || '0'}</div>
              
              {/* Hex Preview */}
              <div className="bg-gray-900 text-green-400 p-3 rounded font-mono text-xs overflow-x-auto mb-2">
                <div className="whitespace-pre">{cluster.hex_preview?.match(/.{1,32}/g)?.slice(0, 4).join('\n') || 'No data'}</div>
              </div>
              
              {/* ASCII Preview */}
              <div className="bg-gray-100 p-3 rounded font-mono text-xs overflow-x-auto">
                <div className="whitespace-pre text-gray-700">{cluster.ascii_preview?.substring(0, 128) || 'No ASCII data'}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const HealthReportContent = ({ reportData }) => {
  if (!reportData || !reportData.data) return <p className="text-gray-500">No health data available</p>;
  
  const { health_score, status, drive_path, smart_data, surface_map, recommendations, bad_sectors, total_sectors_tested } = reportData.data;
  
  const getStatusColor = () => {
    if (health_score >= 90) return 'bg-green-500';
    if (health_score >= 70) return 'bg-blue-500';
    if (health_score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };
  
  const getStatusIcon = () => {
    if (health_score >= 70) return <CheckCircle className="w-12 h-12 text-green-500" />;
    if (health_score >= 50) return <AlertCircle className="w-12 h-12 text-yellow-500" />;
    return <XCircle className="w-12 h-12 text-red-500" />;
  };
  
  return (
    <div className="space-y-6">
      {/* Health Score */}
      <div className="flex items-center justify-center mb-6">
        <div className="text-center">
          <div className="mb-4">{getStatusIcon()}</div>
          <div className="text-4xl font-bold text-gray-900 mb-2">{health_score}/100</div>
          <div className={`inline-block px-4 py-2 rounded-full text-white font-medium ${getStatusColor()}`}>
            {status || 'Unknown'}
          </div>
        </div>
      </div>

      {/* Drive Info */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <HardDrive className="w-5 h-5 text-gray-600" />
          <span className="font-medium text-gray-900">Drive: {drive_path}</span>
        </div>
      </div>

      {/* Surface Scan Results */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-sm text-blue-600 font-medium">Sectors Tested</div>
          <div className="text-2xl font-bold text-blue-900">{total_sectors_tested?.toLocaleString() || 'N/A'}</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg">
          <div className="text-sm text-red-600 font-medium">Bad Sectors</div>
          <div className="text-2xl font-bold text-red-900">{bad_sectors || 0}</div>
        </div>
      </div>

      {/* SMART Data */}
      {smart_data && Object.keys(smart_data).length > 0 && (
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">SMART Data</h4>
          <div className="bg-gray-50 p-4 rounded-lg space-y-2">
            {Object.entries(smart_data).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-600">{key.replace(/_/g, ' ')}:</span>
                <span className="font-medium text-gray-900">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">Recommendations</h4>
          <div className="space-y-2">
            {recommendations.map((rec, idx) => (
              <div key={idx} className={`p-3 rounded-lg flex items-start gap-3 ${
                rec.includes('✅') ? 'bg-green-50' : rec.includes('⚠️') ? 'bg-yellow-50' : 'bg-red-50'
              }`}>
                <span className="text-sm">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Surface Map Preview */}
      {surface_map && surface_map.length > 0 && (
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">Surface Map (Sample)</h4>
          <div className="flex flex-wrap gap-1">
            {surface_map.slice(0, 100).map((sector, idx) => (
              <div
                key={idx}
                className={`w-4 h-4 rounded-sm ${
                  sector.status === 'good' ? 'bg-green-500' : 
                  sector.status === 'bad' ? 'bg-red-500' : 'bg-yellow-500'
                }`}
                title={`Sector ${sector.sector}: ${sector.status}`}
              />
            ))}
          </div>
          <div className="flex gap-4 mt-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded-sm"></div>
              <span>Good</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded-sm"></div>
              <span>Bad</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded-sm"></div>
              <span>Error</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' or 'files'
  const [selectedCategory, setSelectedCategory] = useState('RAW');
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [files, setFiles] = useState([]);
  const [drives, setDrives] = useState([]);
  const [drivesLoading, setDrivesLoading] = useState(true);
  const [scanResults, setScanResults] = useState([]);
  const [currentScanId, setCurrentScanId] = useState(null);
  const [currentRecoveryId, setCurrentRecoveryId] = useState(null);
  const [viewMode, setViewMode] = useState('grid');
  const { subscribe } = useWebSocket();
  const [showDriveSelection, setShowDriveSelection] = useState(false);
  const [showScanProgress, setShowScanProgress] = useState(false);
  const [showRecoveryProgress, setShowRecoveryProgress] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showExplorer, setShowExplorer] = useState(false);
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [folderPickerMode, setFolderPickerMode] = useState(null); // 'output' or 'temp'
  const [selectedScanType, setSelectedScanType] = useState('normal'); // Track selected scan type
  const [scanMetadata, setScanMetadata] = useState(null); // Store scan reports data
  const [currentScanTypeForReports, setCurrentScanTypeForReports] = useState(''); // Track scan type for reports
  const [notification, setNotification] = useState(null); // Notification state
  const [scanCompletedIds, setScanCompletedIds] = useState(new Set()); // Track completed scans to avoid duplicate notifications
  const [showScanReport, setShowScanReport] = useState(false); // Show scan report dialog
  const [reportScanId, setReportScanId] = useState(null); // Current report scan ID
  const [reportScanType, setReportScanType] = useState(''); // Current report type (cluster/health)
  const [notificationTimeoutId, setNotificationTimeoutId] = useState(null); // Track notification timeout
  
  // Use ref to track ongoing loadScanResults operations to prevent race conditions
  const loadingScanIds = useRef(new Set());
  
  // Multiple scan tabs management
  const [scanTabs, setScanTabs] = useState([]); // Array of {id, scanId, scanType, files, metadata, timestamp}
  const [activeTabId, setActiveTabId] = useState(null); // Currently active tab
  
  // File preview dialog state
  const [showFilePreview, setShowFilePreview] = useState(false);
  const [previewFileId, setPreviewFileId] = useState(null);
  
  const [settings, setSettings] = useState({
    general: {
      defaultOutputPath: 'C:\\RecoveredFiles',
      tempPath: 'C:\\Temp\\ReStoreX',
      autoRefresh: true,
      showThumbnails: true,
      confirmRecovery: true
    },
    recovery: {
      preserveTimestamps: true,
      createSubdirectories: true,
      verifyFiles: true,
      duplicateHandling: 'rename',
      maxFileSize: 1000
    },
    performance: {
      maxConcurrentScans: 1,
      scanPriority: 'normal',
      memoryLimit: 2048,
      enableCaching: true,
      cacheSize: 500
    },
    notifications: {
      scanComplete: true,
      recoveryComplete: true,
      progressUpdates: false,
      soundEnabled: true,
      volume: 50
    },
    advanced: {
      logLevel: 'info',
      detailedLogging: false,
      requireAdmin: true,
      secureDelete: true
    }
  });
  
  const [filterOptions, setFilterOptions] = useState({
    fileType: 'RAW',
    recoveryChances: ['High', 'Average', 'Low', 'Unknown'],
    sortBy: 'name',
    sortOrder: 'asc',
    searchQuery: '',
    sizeFilter: 'all',
    dateFilter: 'all',
  });

  const [scanProgress, setScanProgress] = useState({
    isScanning: false,
    progress: 0,
    currentSector: 0,
    totalSectors: 0,
    filesFound: 0,
    estimatedTimeRemaining: '0 minutes',
    currentPass: 0,
    expectedTime: 'Calculating...',
  });

  const [recoveryProgress, setRecoveryProgress] = useState({
    isRecovering: false,
    progress: 0,
    currentFile: '',
    filesRecovered: 0,
    totalFiles: 0,
    estimatedTimeRemaining: '0 minutes',
  });

  // Statistics tracking
  const [statistics, setStatistics] = useState({
    totalFilesRecovered: 0,
    totalSizeRecovered: 0,
    totalScansCompleted: 0,
    lastScanDate: null,
    successfulRecoveries: 0,
    totalRecoveryAttempts: 0
  });

  // Recent activities tracking
  const [recentActivities, setRecentActivities] = useState(() => {
    // Load from localStorage on initial render
    try {
      const saved = localStorage.getItem('restorex_recent_activities');
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      console.error('Failed to load recent activities:', error);
      return [];
    }
  });
  
  // Save recent activities to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('restorex_recent_activities', JSON.stringify(recentActivities));
    } catch (error) {
      console.error('Failed to save recent activities:', error);
    }
  }, [recentActivities]);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const savedSettings = localStorage.getItem('restorex_settings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings(parsed);
        console.log('Settings loaded from localStorage:', parsed);
      }
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error);
    }
  }, []);

  // Load drives on mount
  useEffect(() => {
    loadDrives();
    
    // Handle browser back/forward navigation
    const handlePopState = (event) => {
      if (event.state && event.state.view) {
        setCurrentView(event.state.view);
      }
    };
    
    window.addEventListener('popstate', handlePopState);
    
    // Set initial state
    window.history.replaceState({ view: 'dashboard' }, '', window.location.pathname);
    
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  // Helper to navigate between views with browser history support
  const navigateToView = (view) => {
    if (view !== currentView) {
      setCurrentView(view);
      window.history.pushState({ view }, '', window.location.pathname);
      
      // Reset activeScanType when navigating to dashboard so all scan options are visible
      if (view === 'dashboard') {
        setCurrentScanTypeForReports('');
      }
    }
  };

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubscribeScan = subscribe('scan_progress', (data) => {
      console.log('WebSocket scan_progress update:', data);
      
      // Extract scan_stats if available
      const scanStats = data.scan_stats || {};
      
      setScanProgress(prev => ({
        ...prev,
        progress: data.progress || 0,
        currentSector: scanStats.scanned_sectors || data.currentSector || 0,
        totalSectors: scanStats.total_sectors || data.totalSectors || 0,
        filesFound: data.filesFound || 0,
        currentPass: scanStats.current_pass || 0,
        expectedTime: scanStats.expected_time || 'Calculating...',
        estimatedTimeRemaining: data.estimatedTimeRemaining || '0 minutes',
        isScanning: data.status === 'running' || data.status === undefined
      }));

      // Handle scan cancellation
      if (data.status === 'cancelled' && currentScanId) {
        console.log('Scan cancelled via WebSocket - checking for partial results');
        
        // Check if there are any files found
        if (data.filesFound > 0) {
          console.log(`Partial results available: ${data.filesFound} files`);
          // Load partial results
          loadScanResults(currentScanId).then(() => {
            showNotification('warning', 'Scan Cancelled', `Scan was cancelled. Found ${data.filesFound} files so far. You can still recover these files.`);
          });
        } else {
          console.log('No files found before cancellation');
          showNotification('warning', 'Scan Cancelled', 'The scan was cancelled with no files found yet.');
        }
        
        setShowScanProgress(false);
        setScanProgress({
          isScanning: false,
          progress: 0,
          currentSector: 0,
          totalSectors: 0,
          filesFound: 0,
          estimatedTimeRemaining: '0 minutes',
        });
        setCurrentScanId(null);
      }

      // If scan completed, load the results and close dialog
      if (data.status === 'completed' && currentScanId) {
        console.log('Scan completed via WebSocket, loading results for scanId:', currentScanId);
        
        // Check if we've already handled this scan completion
        if (!scanCompletedIds.has(currentScanId)) {
          setScanCompletedIds(prev => new Set(prev).add(currentScanId));
          loadScanResults(currentScanId);
          
          // Update statistics
          setStatistics(prev => ({
            ...prev,
            totalScansCompleted: prev.totalScansCompleted + 1,
            lastScanDate: new Date()
          }));
        }
        
        // Close the scan progress dialog after a short delay
        setTimeout(() => {
          setShowScanProgress(false);
        }, 1500);
      }
    });

    const unsubscribeRecovery = subscribe('recovery_progress', (data) => {
      setRecoveryProgress(prev => ({
        ...prev,
        progress: data.progress || 0,
        currentFile: data.currentFile || '',
        filesRecovered: data.filesRecovered || 0,
        totalFiles: data.totalFiles || 0,
        estimatedTimeRemaining: data.estimatedTimeRemaining || '0 minutes',
        isRecovering: data.status === 'running'
      }));

      // Update file statuses based on recovery progress
      if (data.status === 'completed') {
        console.log('Recovery completed via WebSocket');
        const recoveredCount = files.filter(f => f.isSelected).length;
        const recoveredSize = files.filter(f => f.isSelected).reduce((sum, f) => sum + f.sizeBytes, 0);
        
        setFiles(prevFiles => prevFiles.map(file =>
          file.isSelected ? { ...file, status: 'recovered', isSelected: false } : file
        ));
        
        // Update active tab's files as well
        setScanTabs(prevTabs => prevTabs.map(tab => 
          tab.id === activeTabId 
            ? { ...tab, files: tab.files.map(file => 
                file.isSelected ? { ...file, status: 'recovered', isSelected: false } : file
              )}
            : tab
        ));
        
        // Update statistics
        setStatistics(prev => ({
          ...prev,
          totalFilesRecovered: prev.totalFilesRecovered + recoveredCount,
          totalSizeRecovered: prev.totalSizeRecovered + recoveredSize,
          successfulRecoveries: prev.successfulRecoveries + 1,
          totalRecoveryAttempts: prev.totalRecoveryAttempts + 1
        }));
        
        // Close the recovery progress dialog after a short delay
        setTimeout(() => {
          setShowRecoveryProgress(false);
          showNotification('success', 'Recovery Completed', `${recoveredCount} files recovered to:\n${settings.general.defaultOutputPath}`);
        }, 1000);
      }
    });

    return () => {
      unsubscribeScan();
      unsubscribeRecovery();
    };
  }, [subscribe, currentScanId]);

  // Helper function to show notifications
  const showNotification = (type, title, message) => {
    // Clear any existing notification timeout
    if (notificationTimeoutId) {
      clearTimeout(notificationTimeoutId);
    }
    
    setNotification({ type, title, message });
    
    // Auto-dismiss after 5 seconds
    const timeoutId = setTimeout(() => {
      setNotification(null);
      setNotificationTimeoutId(null);
    }, 5000);
    
    setNotificationTimeoutId(timeoutId);
  };

  // Helper function to add recent activity
  const addRecentActivity = (activity) => {
    setRecentActivities(prev => {
      const newActivities = [activity, ...prev].slice(0, 10); // Keep only last 10
      return newActivities;
    });
  };

  // API Functions
  const loadDrives = async () => {
    try {
      setDrivesLoading(true);
      console.log('Loading drives from API...');
      const drivesData = await apiService.getDrives();
      console.log('Drives loaded:', drivesData);
      setDrives(drivesData);
    } catch (error) {
      console.error('Failed to load drives:', error);
      // Show error to user
      showNotification('error', 'Failed to Load Drives', `${error.message}\n\nPlease make sure the backend server is running on http://localhost:8000`);
    } finally {
      setDrivesLoading(false);
    }
  };

  const loadScanResults = async (scanId) => {
    try {
      console.log('Loading scan results for scan:', scanId);
      
      // Check if this scanId is already being loaded
      if (loadingScanIds.current.has(scanId)) {
        console.log('Already loading results for scanId:', scanId, '- skipping duplicate request');
        return;
      }
      
      // Mark this scanId as loading
      loadingScanIds.current.add(scanId);
      
      // Use functional update to check for existing tab with latest state
      let existingTabId = null;
      setScanTabs(prev => {
        const existingTab = prev.find(tab => tab.scanId === scanId);
        if (existingTab) {
          existingTabId = existingTab.id;
        }
        return prev;
      });
      
      // If tab already exists, just switch to it
      if (existingTabId) {
        console.log('Tab already exists for scanId:', scanId, '- switching to existing tab');
        loadingScanIds.current.delete(scanId);
        switchToTab(existingTabId);
        return;
      }
      
      // Get scan status to check for metadata (health reports, etc.)
      const scanStatus = await apiService.getScanStatus(scanId);
      console.log('Scan status:', scanStatus);
      
      const scanType = scanStatus.scan_type || 'normal';
      
      // Check if this is a cluster or health scan that needs report data
      if (scanType === 'cluster' || scanType === 'health') {
        console.log(`Loading ${scanType} scan report data...`);
        
        try {
          const reportData = await apiService.getScanReport(scanId);
          console.log('Report data loaded:', reportData);
          
          // Create a tab with report data
          const reportTab = {
            id: Date.now(),
            scanId: scanId,
            scanType: scanType,
            scanStatus: 'completed',
            files: [],
            metadata: null,
            reportData: reportData,
            timestamp: new Date(),
            name: `${scanType === 'cluster' ? 'Cluster' : 'Health'} Report`
          };
          
          // Add the new tab
          setScanTabs(prev => {
            const alreadyExists = prev.find(tab => tab.scanId === scanId);
            if (alreadyExists) {
              console.log('Tab already exists, skipping duplicate');
              return prev;
            }
            return [...prev, reportTab];
          });
          setActiveTabId(reportTab.id);
          
          // Remove from loading set
          loadingScanIds.current.delete(scanId);
          
          // Navigate to files view to show the report
          navigateToView('files');
          
          showNotification('success', `${scanType === 'cluster' ? 'Cluster' : 'Health'} Scan Complete`, 
            `Report generated successfully. View the report in the new tab.`);
          
          return;
        } catch (error) {
          console.error('Failed to load report:', error);
          showNotification('error', 'Report Load Failed', error.message);
          loadingScanIds.current.delete(scanId);
          return;
        }
      }
      
      // For regular scans, load file results
      const results = await apiService.getScanResults(scanId, {});
      console.log('Scan results loaded:', results.length, 'files');
      
      // Load thumbnails for image files
      const filesWithThumbnails = await Promise.all(
        results.map(async (file) => {
          // Only load thumbnails for image types
          const imageTypes = ['png', 'jpg', 'jpeg', 'heic', 'raw', 'gif', 'bmp', 'webp'];
          if (imageTypes.includes(file.type?.toLowerCase())) {
            try {
              const blob = await apiService.getFileThumbnail(file.id, 150);
              if (blob) {
                const url = URL.createObjectURL(blob);
                return { ...file, thumbnail: url };
              }
            } catch (error) {
              console.error(`Failed to load thumbnail for file ${file.id}:`, error);
            }
          }
          return file;
        })
      );
      
      console.log('Thumbnails loaded for image files');
      
      // Extract metadata from scan status
      const metadata = scanStatus.metadata || {};
      console.log('Scan metadata:', metadata);
      
      // Create a new tab for this scan
      const newTab = {
        id: Date.now(), // Unique tab ID
        scanId: scanId,
        scanType: scanStatus.scan_type || 'normal',
        scanStatus: scanStatus.status || 'completed', // Track if scan was completed or cancelled
        files: filesWithThumbnails,
        metadata: Object.keys(metadata).length > 0 ? metadata : null,
        timestamp: new Date(),
        name: getScanTabName(scanStatus.scan_type, filesWithThumbnails.length, scanStatus.status)
      };
      
      // Add the new tab and set it as active using functional update to prevent race conditions
      setScanTabs(prev => {
        // Double-check if tab was added by another concurrent call
        const alreadyExists = prev.find(tab => tab.scanId === scanId);
        if (alreadyExists) {
          console.log('Tab was created by concurrent call, skipping duplicate');
          return prev;
        }
        return [...prev, newTab];
      });
      setActiveTabId(newTab.id);
      
      // Remove from loading set
      loadingScanIds.current.delete(scanId);
      
      // Update current view data with the new tab's data
      setFiles(filesWithThumbnails);
      setScanResults(generateScanResultsTree(filesWithThumbnails));
      setScanMetadata(newTab.metadata);
      setCurrentScanTypeForReports(newTab.scanType);
      
      // Check if this is a health scan (no files but has health report)
      if (filesWithThumbnails.length === 0 && scanStatus.status === 'completed') {
        console.log('Scan completed with no files - might be a health/diagnostic scan');
        navigateToView('files');
        
        // If there's a health report, show it in the reports view
        if (metadata.health_report) {
          showNotification('success', 'Health Scan Completed', 'View the Health Report below for detailed analysis.');
          
          // Add to recent activities
          addRecentActivity({
            id: Date.now(),
            type: 'health_scan',
            icon: 'info',
            title: 'Drive health check completed',
            description: `Status: ${metadata.health_report.checks?.filter(c => c.status === 'pass').length || 0} checks passed`,
            timestamp: new Date()
          });
        } else {
          // Show a notification for other diagnostic scans
          showNotification('success', 'Scan Completed', 'This scan type performs analysis without recovering files.\nCheck the scan logs for detailed information.');
          
          // Add to recent activities
          const scanTypeNames = {
            cluster: 'Cluster analysis',
            forensic: 'Forensic analysis',
            signature: 'Signature scan',
            carving: 'File carving scan'
          };
          addRecentActivity({
            id: Date.now(),
            type: 'diagnostic_scan',
            icon: 'info',
            title: `${scanTypeNames[newTab.scanType] || 'Diagnostic scan'} completed`,
            description: 'Analysis complete, check reports for details',
            timestamp: new Date()
          });
        }
        return;
      }
      
      // Switch to files view and reset ALL filters to show all results
      navigateToView('files');
      setSelectedCategory('All Files');
      setFilterOptions({
        fileType: '', // Clear file type filter to show all types
        recoveryChances: ['High', 'Average', 'Low', 'Unknown'],
        sortBy: 'name',
        sortOrder: 'asc',
        searchQuery: '',
        sizeFilter: 'all',
        dateFilter: 'all',
      });
      
      // Show success notification
      showNotification('success', 'Scan Completed Successfully', `Found ${results.length} recoverable files.`);
      
      // Add to recent activities
      const scanTypeNames = {
        normal: 'Normal scan',
        deep: 'Deep scan',
        carving: 'File carving scan',
        cluster: 'Cluster scan',
        health: 'Health scan',
        signature: 'Signature scan',
        forensic: 'Forensic scan'
      };
      addRecentActivity({
        id: Date.now(),
        type: 'scan_completed',
        icon: 'success',
        title: `${scanTypeNames[newTab.scanType] || 'Scan'} completed`,
        description: `Found ${results.length} recoverable files`,
        timestamp: new Date()
      });
      
      console.log('Switched to files view with', results.length, 'files');
    } catch (error) {
      console.error('Failed to load scan results:', error);
      // Remove from loading set on error
      loadingScanIds.current.delete(scanId);
      showNotification('error', 'Error Loading Results', error.message);
    }
  };

  // Helper function to generate tab names
  const getScanTabName = (scanType, fileCount, scanStatus = 'completed') => {
    const typeNames = {
      normal: 'Normal',
      deep: 'Deep',
      carving: 'File Carving',
      cluster: 'Cluster',
      health: 'Health',
      signature: 'Signature',
      forensic: 'Forensic'
    };
    
    const typeName = typeNames[scanType] || 'Scan';
    const statusSuffix = scanStatus === 'cancelled' ? ' [Partial]' : '';
    
    if (fileCount > 0) {
      return `${typeName} (${fileCount} files)${statusSuffix}`;
    } else {
      return `${typeName} Report${statusSuffix}`;
    }
  };

  // Function to switch to a different tab
  const switchToTab = (tabId) => {
    const tab = scanTabs.find(t => t.id === tabId);
    console.log('🔄 Switching to tab:', { tabId, tab, hasReportData: !!tab?.reportData });
    
    if (tab) {
      setActiveTabId(tabId);
      setFiles(tab.files);
      setScanResults(generateScanResultsTree(tab.files));
      setScanMetadata(tab.metadata);
      setCurrentScanTypeForReports(tab.scanType);
      setSelectedCategory('All Files');
      setFilterOptions({
        fileType: '',
        recoveryChances: ['High', 'Average', 'Low', 'Unknown'],
        sortBy: 'name',
        sortOrder: 'asc',
        searchQuery: '',
        sizeFilter: 'all',
        dateFilter: 'all',
      });
      
      // If it's a report tab, make sure we're in files view
      if (tab.reportData) {
        console.log('📊 This is a report tab, ensuring files view is active');
        navigateToView('files');
      }
    }
  };

  // Function to close a tab
  const closeTab = (tabId) => {
    const tabIndex = scanTabs.findIndex(t => t.id === tabId);
    const newTabs = scanTabs.filter(t => t.id !== tabId);
    setScanTabs(newTabs);
    
    // If closing the active tab, switch to another tab
    if (tabId === activeTabId) {
      if (newTabs.length > 0) {
        // Switch to the previous tab or the first one
        const newActiveTab = tabIndex > 0 ? newTabs[tabIndex - 1] : newTabs[0];
        switchToTab(newActiveTab.id);
      } else {
        // No more tabs, clear everything
        setActiveTabId(null);
        setFiles([]);
        setScanResults([]);
        setScanMetadata(null);
        setCurrentScanTypeForReports('');
        navigateToView('dashboard');
      }
    }
  };

  const generateScanResultsTree = (files) => {
    // Group files by type to create a tree structure
    const typeCount = files.reduce((acc, file) => {
      acc[file.type] = (acc[file.type] || 0) + 1;
      return acc;
    }, {});

    const children = Object.entries(typeCount).map(([type, count]) => ({
      name: type,
      count,
      icon: getIconForType(type)
    }));

    return [{
      name: 'Scan Results',
      count: files.length,
      icon: 'HardDrive',
      isExpanded: true,
      children
    }];
  };

  const getIconForType = (type) => {
    const iconMap = {
      'RAW': 'FileImage',
      'PNG': 'FileImage',
      'JPG': 'FileImage',
      'JPEG': 'FileImage',
      'HEIC': 'FileImage',
      'PDF': 'FileText',
      'MP4': 'Video',
      'MP3': 'Music',
      'ZIP': 'Archive'
    };
    return iconMap[type] || 'File';
  };

  // Filter and sort files
  const filteredFiles = files.filter(file => {
    // File type filter
    if (filterOptions.fileType && file.type !== filterOptions.fileType) {
      return false;
    }
    
    // Recovery chances filter
    if (!filterOptions.recoveryChances.includes(file.recoveryChance)) {
      return false;
    }
    
    // Search filter
    if (filterOptions.searchQuery && !file.name.toLowerCase().includes(filterOptions.searchQuery.toLowerCase())) {
      return false;
    }
    
    // Size filter
    if (filterOptions.sizeFilter && filterOptions.sizeFilter !== 'all') {
      const sizeBytes = file.sizeBytes || 0;
      switch (filterOptions.sizeFilter) {
        case 'small': // < 1 MB
          if (sizeBytes >= 1024 * 1024) return false;
          break;
        case 'medium': // 1 MB - 10 MB
          if (sizeBytes < 1024 * 1024 || sizeBytes >= 10 * 1024 * 1024) return false;
          break;
        case 'large': // > 10 MB
          if (sizeBytes < 10 * 1024 * 1024) return false;
          break;
      }
    }
    
    // Date filter
    if (filterOptions.dateFilter && filterOptions.dateFilter !== 'all') {
      const fileDate = new Date(file.dateModified);
      const now = new Date();
      const daysDiff = Math.floor((now - fileDate) / (1000 * 60 * 60 * 24));
      
      switch (filterOptions.dateFilter) {
        case 'today':
          if (daysDiff > 1) return false;
          break;
        case 'week':
          if (daysDiff > 7) return false;
          break;
        case 'month':
          if (daysDiff > 30) return false;
          break;
        case 'year':
          if (daysDiff > 365) return false;
          break;
      }
    }
    
    return true;
  }).sort((a, b) => {
    const { sortBy, sortOrder } = filterOptions;
    let comparison = 0;
    
    switch (sortBy) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'size':
        comparison = a.sizeBytes - b.sizeBytes;
        break;
      case 'date':
        comparison = new Date(a.dateModified).getTime() - new Date(b.dateModified).getTime();
        break;
      case 'recovery':
        const recoveryOrder = { 'High': 4, 'Average': 3, 'Low': 2, 'Unknown': 1 };
        comparison = recoveryOrder[a.recoveryChance] - recoveryOrder[b.recoveryChance];
        break;
    }
    
    return sortOrder === 'asc' ? comparison : -comparison;
  });

  const selectedFile = files.find(f => f.id === selectedFileId) || null;
  const selectedFiles = files.filter(f => f.isSelected);
  const totalSelectedSize = selectedFiles.reduce((acc, file) => acc + file.sizeBytes, 0);
  
  // Calculate total size of filtered files
  const totalFilteredSize = filteredFiles.reduce((acc, file) => acc + file.sizeBytes, 0);
  
  const formatBytes = (bytes) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
  };

  const handleFileToggle = (fileId) => {
    setFiles(prev => {
      const updated = prev.map(file => 
        file.id === fileId ? { ...file, isSelected: !file.isSelected } : file
      );
      const selectedCount = updated.filter(f => f.isSelected).length;
      console.log('File toggled:', fileId, 'Selected count:', selectedCount);
      return updated;
    });
    
    // Update active tab's files as well
    setScanTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { ...tab, files: tab.files.map(file => 
            file.id === fileId ? { ...file, isSelected: !file.isSelected } : file
          )}
        : tab
    ));
  };

  const handleCategorySelect = (category) => {
    navigateToView('files');
    setSelectedCategory(category);
    if (['RAW', 'PNG', 'JPG', 'HEIC', 'AI', 'PDF', 'MP4'].includes(category)) {
      setFilterOptions(prev => ({ ...prev, fileType: category }));
    } else {
      setFilterOptions(prev => ({ ...prev, fileType: '' }));
    }
  };

  const handleStartNewScan = (scanType = 'normal') => {
    console.log('handleStartNewScan called with scan type:', scanType);
    navigateToView('files');
    // Store the selected scan type
    setSelectedScanType(scanType);
    
    // Use simple drive selection dialog for all scan types
    // Normal scan will use default options (partition 1, FAT/NTFS filesystem, default output path)
    setShowDriveSelection(true);
  };

  // Handler for recovery wizard (kept for backward compatibility, but no longer used)
  const handleWizardStartRecovery = async (drive, options = {}) => {
    console.log('Wizard starting recovery:', { drive, options });
    setShowRecoveryWizard(false);
    
    // Call handleStartScan with 'normal' scan type
    await handleStartScan(drive.id, 'normal', options);
  };

  const handleStartScan = async (driveId, scanType, options = {}) => {
    try {
      console.log('Starting scan:', { driveId, scanType, options });
      setShowDriveSelection(false);
      
      // Merge scan options with sensible defaults
      const scanOptions = {
        fileTypes: options.fileTypes || (filterOptions.fileType ? [filterOptions.fileType] : undefined),
        // Default options for Python-based recovery
        partition: options.partition || '1',  // Default to partition 1
        filesystem: options.filesystem || 'other',  // Default to FAT/NTFS/HFS+
        outputPath: options.outputPath || settings.general.defaultOutputPath || 'C:\\RecoveredFiles',
        ...options
      };
      
      console.log('Scan options with defaults:', scanOptions);
      
      // Start the scan via API
      const response = await apiService.startScan(driveId, scanType, scanOptions);
      
      console.log('Scan started successfully:', response);
      
      // Get drive name for activity log
      const drive = drives.find(d => d.id === driveId);
      const driveName = drive ? drive.name : driveId;
      
      // Get friendly scan type name
      const scanTypeNames = {
        'normal': 'Normal Scan',
        'deep': 'Deep Scan',
        'quick': 'Quick Scan',
        'carving': 'Signature File Carving',
        'cluster': 'Cluster Scan',
        'health': 'Disk Health Scan'
      };
      const scanTypeName = scanTypeNames[scanType] || scanType;
      
      // Add activity for scan start
      addRecentActivity({
        id: `scan-start-${response.scanId}`,
        title: `${scanTypeName} Started`,
        description: `Scanning drive ${driveName}`,
        icon: 'info',
        timestamp: new Date().toISOString(),
        scanId: response.scanId,
        driveId: driveId,
        scanType: scanType
      });
      
      setCurrentScanId(response.scanId);
      setScanProgress({
        isScanning: true,
        progress: 0,
        currentSector: 0,
        totalSectors: scanType === 'quick' ? 1000000 : 5000000,
        filesFound: 0,
        estimatedTimeRemaining: scanType === 'quick' ? '10 minutes' : '45 minutes',
      });
      setShowScanProgress(true);
      
      // Poll for scan status updates (WebSocket will also update in real-time)
      const pollInterval = setInterval(async () => {
        try {
          const status = await apiService.getScanStatus(response.scanId);
          console.log('Scan status update (polling):', status);
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            clearInterval(pollInterval);
            if (status.status === 'completed') {
              console.log('Scan completed (via polling), loading results...');
              console.log('Full status object:', status);
              
              // Check if we've already handled this scan completion
              if (!scanCompletedIds.has(response.scanId)) {
                setScanCompletedIds(prev => new Set(prev).add(response.scanId));
                
                // Load results for all scan types (including cluster/health)
                await loadScanResults(response.scanId);
                
                // Add activity for scan completion
                const filesCount = status.files_count || status.files_found || 0;
                addRecentActivity({
                  id: `scan-complete-${response.scanId}`,
                  title: `${scanTypeName} Completed`,
                  description: `Found ${filesCount} file${filesCount !== 1 ? 's' : ''} on ${driveName}`,
                  icon: 'success',
                  timestamp: new Date().toISOString(),
                  scanId: response.scanId,
                  driveId: driveId,
                  scanType: scanType,
                  filesFound: filesCount
                });
                
                // Update statistics
                setStatistics(prev => ({
                  ...prev,
                  totalScansCompleted: prev.totalScansCompleted + 1,
                  lastScanDate: new Date()
                }));
              }
              
              // Close dialog and navigate to files view
              setTimeout(() => {
                setShowScanProgress(false);
              }, 1500);
            } else if (status.status === 'failed') {
              setShowScanProgress(false);
              
              // Add activity for scan failure
              addRecentActivity({
                id: `scan-failed-${response.scanId}`,
                title: `${scanTypeName} Failed`,
                description: `Error scanning ${driveName}: ${status.error || 'Unknown error'}`,
                icon: 'error',
                timestamp: new Date().toISOString(),
                scanId: response.scanId,
                driveId: driveId,
                scanType: scanType
              });
              
              showNotification('error', 'Scan Failed', status.error || 'Unknown error');
            } else if (status.status === 'cancelled') {
              console.log('Scan cancelled (via polling) - checking for partial results');
              setShowScanProgress(false);
              
              // Try to load partial results if any files were found
              if (status.files_found && status.files_found > 0) {
                console.log(`Loading partial results from polling: ${status.files_found} files`);
                
                try {
                  await loadScanResults(response.scanId);
                  
                  // Add activity for cancelled scan with partial results
                  addRecentActivity({
                    id: `scan-cancelled-${response.scanId}`,
                    title: `${scanTypeName} Cancelled`,
                    description: `Partial results: ${status.files_found} file${status.files_found !== 1 ? 's' : ''} found on ${driveName}`,
                    icon: 'warning',
                    timestamp: new Date().toISOString(),
                    scanId: response.scanId,
                    driveId: driveId,
                    scanType: scanType,
                    filesFound: status.files_found
                  });
                  
                  showNotification('warning', 'Scan Cancelled - Partial Results Available', 
                    `Found ${status.files_found} files before cancellation. You can view and recover these files.`);
                } catch (error) {
                  console.error('Failed to load partial results:', error);
                  showNotification('warning', 'Scan Cancelled', 'The scan was cancelled. Unable to load partial results.');
                }
              } else {
                // Add activity for cancelled scan with no results
                addRecentActivity({
                  id: `scan-cancelled-${response.scanId}`,
                  title: `${scanTypeName} Cancelled`,
                  description: `Scan cancelled on ${driveName} with no files found`,
                  icon: 'warning',
                  timestamp: new Date().toISOString(),
                  scanId: response.scanId,
                  driveId: driveId,
                  scanType: scanType
                });
                
                showNotification('warning', 'Scan Cancelled', 'The scan was cancelled with no files found yet.');
              }
            }
          }
        } catch (error) {
          console.error('Failed to poll scan status:', error);
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start scan:', error);
      showNotification('error', 'Failed to Start Scan', error.message);
    }
  };

  const handleRecover = async () => {
    const selectedFiles = files.filter(f => f.isSelected);
    console.log('handleRecover called. Total files:', files.length, 'Selected files:', selectedFiles.length);
    
    if (selectedFiles.length === 0) {
      showNotification('warning', 'No Files Selected', 'Please select files to recover');
      return;
    }
    
    if (settings.general.confirmRecovery) {
      const confirmed = window.confirm(
        `Are you sure you want to recover ${selectedFiles.length} selected files?`
      );
      if (!confirmed) return;
    }
    
    try {
      console.log('Starting recovery for', selectedFiles.length, 'files');
      
      // Start recovery via API
      const response = await apiService.startRecovery(
        selectedFiles.map(f => f.id),
        settings.general.defaultOutputPath,
        {
          preserveTimestamps: settings.recovery.preserveTimestamps,
          createSubdirectories: settings.recovery.createSubdirectories,
          verifyFiles: settings.recovery.verifyFiles,
          duplicateHandling: settings.recovery.duplicateHandling
        }
      );
      
      console.log('Recovery started successfully:', response);
      
      // Add activity for recovery start
      addRecentActivity({
        id: `recovery-start-${response.recoveryId}`,
        title: 'File Recovery Started',
        description: `Recovering ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`,
        icon: 'info',
        timestamp: new Date().toISOString(),
        recoveryId: response.recoveryId,
        fileCount: selectedFiles.length
      });
      
      setCurrentRecoveryId(response.recoveryId);
      setRecoveryProgress({
        isRecovering: true,
        progress: 0,
        currentFile: selectedFiles[0].name,
        filesRecovered: 0,
        totalFiles: selectedFiles.length,
        estimatedTimeRemaining: `${Math.ceil(selectedFiles.length * 0.5)} minutes`,
      });
      setShowRecoveryProgress(true);
      
      // Poll for recovery status updates
      const pollInterval = setInterval(async () => {
        try {
          const status = await apiService.getRecoveryStatus(response.recoveryId);
          console.log('Recovery status update:', status);
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            clearInterval(pollInterval);
            if (status.status === 'completed') {
              console.log('Recovery completed successfully');
              const recoveredCount = selectedFiles.length;
              const recoveredSize = selectedFiles.reduce((sum, f) => sum + f.sizeBytes, 0);
              
              // Format size for display
              const formatBytes = (bytes) => {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const sizes = ['B', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
              };
              
              // Add activity for recovery completion
              addRecentActivity({
                id: `recovery-complete-${response.recoveryId}`,
                title: 'File Recovery Completed',
                description: `Successfully recovered ${recoveredCount} file${recoveredCount !== 1 ? 's' : ''} (${formatBytes(recoveredSize)})`,
                icon: 'success',
                timestamp: new Date().toISOString(),
                recoveryId: response.recoveryId,
                fileCount: recoveredCount,
                size: recoveredSize
              });
              
              setFiles(prevFiles => prevFiles.map(file =>
                file.isSelected ? { ...file, status: 'recovered', isSelected: false } : file
              ));
              
              // Update active tab's files as well
              setScanTabs(prevTabs => prevTabs.map(tab => 
                tab.id === activeTabId 
                  ? { ...tab, files: tab.files.map(file => 
                      file.isSelected ? { ...file, status: 'recovered', isSelected: false } : file
                    )}
                  : tab
              ));
              
              // Update statistics
              setStatistics(prev => ({
                ...prev,
                totalFilesRecovered: prev.totalFilesRecovered + recoveredCount,
                totalSizeRecovered: prev.totalSizeRecovered + recoveredSize,
                successfulRecoveries: prev.successfulRecoveries + 1,
                totalRecoveryAttempts: prev.totalRecoveryAttempts + 1
              }));
              
              // Close dialog and show success
              setTimeout(() => {
                setShowRecoveryProgress(false);
                showNotification('success', 'Recovery Completed', `${recoveredCount} files recovered to:\n${settings.general.defaultOutputPath}`);
                
                // Add to recent activities
                addRecentActivity({
                  id: Date.now(),
                  type: 'recovery_completed',
                  icon: 'success',
                  title: 'Files recovered successfully',
                  description: `${recoveredCount} files recovered (${formatBytes(recoveredSize)})`,
                  timestamp: new Date()
                });
              }, 1000);
            } else if (status.status === 'failed') {
              setShowRecoveryProgress(false);
              // Update failure stats
              setStatistics(prev => ({
                ...prev,
                totalRecoveryAttempts: prev.totalRecoveryAttempts + 1
              }));
              showNotification('error', 'Recovery Failed', status.error || 'Unknown error');
            }
          }
        } catch (error) {
          console.error('Failed to poll recovery status:', error);
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start recovery:', error);
      showNotification('error', 'Failed to Start Recovery', error.message);
    }
  };

  const handleRecoverSingle = async (fileId) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;
    
    try {
      setFiles(prev => prev.map(f =>
        f.id === fileId ? { ...f, status: 'recovering' } : f
      ));
      
      // Start recovery for single file
      await apiService.startRecovery(
        [fileId],
        settings.general.defaultOutputPath,
        {
          preserveTimestamps: settings.recovery.preserveTimestamps,
          createSubdirectories: settings.recovery.createSubdirectories,
          verifyFiles: settings.recovery.verifyFiles
        }
      );
      
      // Update status to recovered after a delay (in production, wait for WebSocket update)
      setTimeout(() => {
        setFiles(prev => prev.map(f =>
          f.id === fileId ? { ...f, status: 'recovered' } : f
        ));
      }, 3000);
    } catch (error) {
      console.error('Failed to recover file:', error);
      setFiles(prev => prev.map(f =>
        f.id === fileId ? { ...f, status: 'found' } : f
      ));
      showNotification('error', 'Failed to Recover File', error.message);
    }
  };

  const handleWindowAction = (action) => {
    console.log(`Window action: ${action}`);
    // These would interact with your C++ backend to control the window
  };

  const handleSelectOutputFolder = () => {
    // This would open a folder selection dialog
    console.log('Select output folder');
    setShowExplorer(true);
  };

  const handleShowInExplorer = () => {
    setShowExplorer(true);
  };

  const handleOpenSettings = () => {
    setShowSettings(true);
  };

  const handleSaveSettings = (newSettings) => {
    setSettings(newSettings);
    // Save to localStorage for persistence
    try {
      localStorage.setItem('restorex_settings', JSON.stringify(newSettings));
      console.log('Settings saved to localStorage:', newSettings);
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error);
    }
  };

  return (
    <>
      <div className="h-screen bg-gray-50 flex flex-col">
        {/* Notification Box */}
        {notification && (
          <NotificationBox
            type={notification.type}
            title={notification.title}
            message={notification.message}
            onClose={() => {
              if (notificationTimeoutId) {
                clearTimeout(notificationTimeoutId);
                setNotificationTimeoutId(null);
              }
              setNotification(null);
            }}
          />
        )}

      {/* Window Header */}
      <Header 
        scanStatus={currentView === 'dashboard' ? 'Ready' : (scanResults.length > 0 ? `${files.length} files found` : 'Ready')}
        searchQuery={filterOptions.searchQuery}
        onSearchChange={(query) => setFilterOptions(prev => ({ ...prev, searchQuery: query }))}
        onNavigateToDashboard={() => navigateToView('dashboard')}
        showSearch={currentView !== 'dashboard'}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          scanResults={scanResults}
          selectedCategory={selectedCategory}
          onCategorySelect={handleCategorySelect}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onStartNewScan={handleStartNewScan}
          currentView={currentView}
          onViewChange={navigateToView}
          onShowInExplorer={handleShowInExplorer}
          onOpenSettings={handleOpenSettings}
          scanTabs={scanTabs}
          activeTabId={activeTabId}
          onSwitchTab={switchToTab}
          onCloseTab={closeTab}
        />

        {/* Main Content Area */}
        {currentView === 'dashboard' ? (
          <Dashboard 
            onStartScan={handleStartNewScan}
            drives={drives}
            drivesLoading={drivesLoading}
            statistics={statistics}
            activeScanType={currentScanTypeForReports}
            recentActivities={recentActivities}
          />
        ) : (
          <div className="flex-1 flex flex-col">
            {/* Check if active tab has report data (cluster/health scan) */}
            {(() => {
              console.log('🎯 FILES VIEW RENDERING - currentView:', currentView);
              const activeTab = scanTabs.find(t => t.id === activeTabId);
              console.log('🔍 Checking active tab:', { 
                activeTabId, 
                activeTab, 
                hasReportData: activeTab?.reportData ? 'YES' : 'NO',
                scanType: activeTab?.scanType,
                allTabs: scanTabs.map(t => ({ id: t.id, name: t.name, hasReport: !!t.reportData }))
              });
              
              if (activeTab && activeTab.reportData) {
                console.log('✅ Rendering report for tab:', activeTab.name);
                // Display report directly in the main content area without dialog wrapper
                const reportData = activeTab.reportData;
                const scanType = activeTab.scanType;
                
                return (
                  <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
                    <div className="bg-white rounded-xl shadow-sm w-full max-w-6xl mx-auto p-6">
                      {/* Report Header */}
                      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-200">
                        <Activity className="w-6 h-6 text-blue-600" />
                        <h3 className="text-xl font-bold text-gray-900">
                          {scanType === 'cluster' ? 'Cluster Map Report' : 'Drive Health Report'}
                        </h3>
                      </div>
                      
                      {/* Report Content - Render based on scan type */}
                      {scanType === 'cluster' ? (
                        <ClusterReportContent reportData={reportData} />
                      ) : (
                        <HealthReportContent reportData={reportData} />
                      )}
                    </div>
                  </div>
                );
              }
              return null;
            })()}
            
            {/* Scan Reports Panel - Shows when there's metadata (but no dedicated report tab) */}
            {scanMetadata && !scanTabs.find(t => t.id === activeTabId)?.reportData && (
              <div className="border-b border-gray-200 bg-gray-50">
                <ScanReportsPanel 
                  scanMetadata={scanMetadata}
                  scanType={currentScanTypeForReports}
                />
              </div>
            )}
            
            {/* Only show Filter Bar and File Grid if there are files and no report data */}
            {files.length > 0 && !scanTabs.find(t => t.id === activeTabId)?.reportData && (
              <>
                {/* Filter Bar */}
                <FilterBar
                  filterOptions={filterOptions}
                  onFilterChange={setFilterOptions}
                  fileCount={filteredFiles.length}
                  totalSize={formatBytes(totalFilteredSize)}
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                  isPartialResults={scanTabs.find(t => t.id === activeTabId)?.scanStatus === 'cancelled'}
                  onResetAll={() => {
                    // Deselect all files
                    setFiles(prev => prev.map(file => ({ ...file, isSelected: false })));
                    
                    // Update active tab if exists
                    if (activeTabId !== null) {
                      setScanTabs(prev => prev.map(tab => 
                        tab.id === activeTabId
                          ? { ...tab, files: tab.files.map(file => ({ ...file, isSelected: false })) }
                          : tab
                      ));
                    }
                  }}
                />

                {/* File Grid */}
                <div className="flex-1 overflow-y-auto bg-gray-50">
                  <FileGrid
                    files={filteredFiles}
                    onFileSelect={setSelectedFileId}
                    onFileToggle={handleFileToggle}
                    selectedFileId={selectedFileId}
                    viewMode={viewMode}
                  />
                </div>
              </>
            )}

            {/* Footer - Only show when there are files */}
            {files.length > 0 && !scanTabs.find(t => t.id === activeTabId)?.reportData && (
              <Footer
                selectedCount={selectedFiles.length}
                totalSize={formatBytes(totalSelectedSize)}
                totalFiles={files.length}
                onRecover={handleRecover}
                onSelectOutputFolder={handleSelectOutputFolder}
              />
            )}
          </div>
        )}

        {/* File Details Panel */}
        {selectedFile && currentView === 'files' && (
          <FileDetailsPanel
            file={selectedFile}
            onClose={() => setSelectedFileId(null)}
            onRecover={handleRecoverSingle}
            onPreview={(fileId) => {
              setPreviewFileId(fileId);
              setShowFilePreview(true);
            }}
          />
        )}
      </div>

      {/* Dialogs */}
      {/* Drive Selection Dialog - For all scan types with sensible defaults */}
      <DriveSelectionDialog
        isOpen={showDriveSelection}
        onClose={() => {
          setShowDriveSelection(false);
          navigateToView('dashboard');
        }}
        onStartScan={handleStartScan}
        drives={drives}
        initialScanType={selectedScanType}
      />

      <ScanProgressDialog
        isOpen={showScanProgress}
        onClose={() => setShowScanProgress(false)}
        onCancel={async () => {
          if (currentScanId) {
            try {
              console.log('Cancelling scan:', currentScanId);
              
              // Get current files found count before cancelling
              const filesFoundSoFar = scanProgress.filesFound;
              
              await apiService.cancelScan(currentScanId);
              console.log('Scan cancelled successfully');
              
              // Close the progress dialog first
              setShowScanProgress(false);
              
              // Wait a bit for backend to save partial results
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              // Try to load partial results if any files were found
              if (filesFoundSoFar > 0) {
                console.log(`Loading partial results: ${filesFoundSoFar} files found before cancellation`);
                
                try {
                  await loadScanResults(currentScanId);
                  
                  // Show notification about partial results
                  showNotification('warning', 'Scan Cancelled - Partial Results Available', 
                    `Found ${filesFoundSoFar} files before cancellation. You can view and recover these files.`);
                  
                  // Add to recent activities
                  addRecentActivity({
                    id: Date.now(),
                    type: 'scan_cancelled',
                    icon: 'warning',
                    title: 'Scan cancelled (partial results)',
                    description: `Stopped early with ${filesFoundSoFar} files found`,
                    timestamp: new Date()
                  });
                  
                  // Don't navigate away - stay on results page
                  console.log('Partial results loaded, staying on results page');
                  
                } catch (error) {
                  console.error('Failed to load partial results:', error);
                  showNotification('warning', 'Scan Cancelled', 'The scan was cancelled. Unable to load partial results.');
                  navigateToView('dashboard');
                }
              } else {
                // No files found, show notification and go to dashboard
                showNotification('warning', 'Scan Cancelled', 'The scan was cancelled with no files found yet.');
                
                // Add to recent activities
                addRecentActivity({
                  id: Date.now(),
                  type: 'scan_cancelled',
                  icon: 'warning',
                  title: 'Scan cancelled',
                  description: 'The scan was stopped by user',
                  timestamp: new Date()
                });
                
                // Navigate back to dashboard
                navigateToView('dashboard');
              }
              
              // Reset scan state
              setCurrentScanId(null);
              setScanProgress({
                isScanning: false,
                progress: 0,
                currentSector: 0,
                totalSectors: 0,
                filesFound: 0,
                estimatedTimeRemaining: '0 minutes',
              });
              
            } catch (error) {
              console.error('Failed to cancel scan:', error);
              showNotification('error', 'Cancel Failed', `Failed to cancel scan: ${error.message}`);
            }
          } else {
            console.warn('No active scan to cancel');
            setShowScanProgress(false);
            setScanProgress(prev => ({ ...prev, isScanning: false }));
          }
        }}
        progress={scanProgress}
      />

      <RecoveryProgressDialog
        isOpen={showRecoveryProgress}
        onClose={() => setShowRecoveryProgress(false)}
        onCancel={async () => {
          if (currentRecoveryId) {
            try {
              await apiService.cancelRecovery(currentRecoveryId);
            } catch (error) {
              console.error('Failed to cancel recovery:', error);
            }
          }
          setShowRecoveryProgress(false);
          setRecoveryProgress(prev => ({ ...prev, isRecovering: false }));
        }}
        progress={recoveryProgress}
      />

      <ExplorerDialog
        isOpen={showExplorer}
        onClose={() => setShowExplorer(false)}
        initialPath={settings.general.defaultOutputPath}
      />

      <FilePreviewDialog
        isOpen={showFilePreview}
        onClose={() => {
          setShowFilePreview(false);
          setPreviewFileId(null);
        }}
        fileId={previewFileId}
      />

      <ScanReportDialog
        isOpen={showScanReport}
        onClose={() => {
          setShowScanReport(false);
          setReportScanId(null);
          setReportScanType('');
        }}
        scanId={reportScanId}
        scanType={reportScanType}
      />
      </div>

      {/* Dialogs rendered outside main container to avoid stacking context issues */}
      <SettingsDialog
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onSave={handleSaveSettings}
        onBrowse={(mode) => {
          setFolderPickerMode(mode);
          setShowFolderPicker(true);
        }}
      />

      <FolderPickerDialog
        isOpen={showFolderPicker}
        onClose={() => setShowFolderPicker(false)}
        onSelect={(path) => {
          // Update the appropriate setting
          if (folderPickerMode === 'output') {
            setSettings(prev => ({
              ...prev,
              general: {
                ...prev.general,
                defaultOutputPath: path
              }
            }));
          } else if (folderPickerMode === 'temp') {
            setSettings(prev => ({
              ...prev,
              general: {
                ...prev.general,
                tempPath: path
              }
            }));
          }
          setShowFolderPicker(false);
          setFolderPickerMode(null);
        }}
        initialPath={
          folderPickerMode === 'output' 
            ? settings.general.defaultOutputPath 
            : folderPickerMode === 'temp'
              ? settings.general.tempPath
              : 'C:\\Users'
        }
        title={folderPickerMode === 'output' ? 'Select Output Directory' : 'Select Temporary Directory'}
      />
    </>
  );
}

export default App;