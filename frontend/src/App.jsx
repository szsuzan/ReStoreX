import React, { useState, useEffect, useRef } from 'react';
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
import { ScanReportsPanel } from './components/ScanReportsPanel';
import { NotificationBox } from './components/NotificationBox';
import { apiService } from './services/apiService';
import { useWebSocket } from './hooks/useWebSocket';

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
  const [selectedScanType, setSelectedScanType] = useState('normal'); // Track selected scan type
  const [scanMetadata, setScanMetadata] = useState(null); // Store scan reports data
  const [currentScanTypeForReports, setCurrentScanTypeForReports] = useState(''); // Track scan type for reports
  const [notification, setNotification] = useState(null); // Notification state
  const [scanCompletedIds, setScanCompletedIds] = useState(new Set()); // Track completed scans to avoid duplicate notifications
  const [notificationTimeoutId, setNotificationTimeoutId] = useState(null); // Track notification timeout
  
  // Use ref to track ongoing loadScanResults operations to prevent race conditions
  const loadingScanIds = useRef(new Set());
  
  // Multiple scan tabs management
  const [scanTabs, setScanTabs] = useState([]); // Array of {id, scanId, scanType, files, metadata, timestamp}
  const [activeTabId, setActiveTabId] = useState(null); // Currently active tab
  
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
  });

  const [scanProgress, setScanProgress] = useState({
    isScanning: false,
    progress: 0,
    currentSector: 0,
    totalSectors: 0,
    filesFound: 0,
    estimatedTimeRemaining: '0 minutes',
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
  const [recentActivities, setRecentActivities] = useState([]);

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
      setScanProgress(prev => ({
        ...prev,
        progress: data.progress || 0,
        currentSector: data.currentSector || 0,
        totalSectors: data.totalSectors || 0,
        filesFound: data.filesFound || 0,
        estimatedTimeRemaining: data.estimatedTimeRemaining || '0 minutes',
        isScanning: data.status === 'running'
      }));

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
      
      const results = await apiService.getScanResults(scanId, {});
      console.log('Scan results loaded:', results.length, 'files');
      
      // Extract metadata from scan status
      const metadata = scanStatus.metadata || {};
      console.log('Scan metadata:', metadata);
      
      // Create a new tab for this scan
      const newTab = {
        id: Date.now(), // Unique tab ID
        scanId: scanId,
        scanType: scanStatus.scan_type || 'normal',
        files: results,
        metadata: Object.keys(metadata).length > 0 ? metadata : null,
        timestamp: new Date(),
        name: getScanTabName(scanStatus.scan_type, results.length)
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
      setFiles(results);
      setScanResults(generateScanResultsTree(results));
      setScanMetadata(newTab.metadata);
      setCurrentScanTypeForReports(newTab.scanType);
      
      // Check if this is a health scan (no files but has health report)
      if (results.length === 0 && scanStatus.status === 'completed') {
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
            signature: 'Signature scan'
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
      });
      
      // Show success notification
      showNotification('success', 'Scan Completed Successfully', `Found ${results.length} recoverable files.`);
      
      // Add to recent activities
      const scanTypeNames = {
        normal: 'Normal scan',
        deep: 'Deep scan',
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
  const getScanTabName = (scanType, fileCount) => {
    const typeNames = {
      normal: 'Normal',
      deep: 'Deep',
      cluster: 'Cluster',
      health: 'Health',
      signature: 'Signature',
      forensic: 'Forensic'
    };
    
    const typeName = typeNames[scanType] || 'Scan';
    
    if (fileCount > 0) {
      return `${typeName} (${fileCount} files)`;
    } else {
      return `${typeName} Report`;
    }
  };

  // Function to switch to a different tab
  const switchToTab = (tabId) => {
    const tab = scanTabs.find(t => t.id === tabId);
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
      });
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
    // Store the selected scan type for the drive selection dialog
    setSelectedScanType(scanType);
    setShowDriveSelection(true);
  };

  const handleStartScan = async (driveId, scanType) => {
    try {
      console.log('Starting scan:', { driveId, scanType });
      setShowDriveSelection(false);
      
      // Start the scan via API
      const response = await apiService.startScan(driveId, scanType, {
        fileTypes: filterOptions.fileType ? [filterOptions.fileType] : []
      });
      
      console.log('Scan started successfully:', response);
      
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
              
              // Check if we've already handled this scan completion
              if (!scanCompletedIds.has(response.scanId)) {
                setScanCompletedIds(prev => new Set(prev).add(response.scanId));
                await loadScanResults(response.scanId);
                
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
              showNotification('error', 'Scan Failed', status.error || 'Unknown error');
            } else if (status.status === 'cancelled') {
              setShowScanProgress(false);
              showNotification('warning', 'Scan Cancelled', 'The scan was cancelled by user.');
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
              
              setFiles(prevFiles => prevFiles.map(file =>
                file.isSelected ? { ...file, status: 'recovered', isSelected: false } : file
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
    // In production, this would save to your C++ backend or local storage
    console.log('Settings saved:', newSettings);
  };

  return (
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
            {/* Scan Reports Panel - Shows FIRST when there's metadata (health/cluster/forensic) */}
            {scanMetadata && (
              <div className="border-b border-gray-200 bg-gray-50">
                <ScanReportsPanel 
                  scanMetadata={scanMetadata}
                  scanType={currentScanTypeForReports}
                />
              </div>
            )}
            
            {/* Only show Filter Bar and File Grid if there are files (not for health/cluster/forensic scans) */}
            {files.length > 0 && (
              <>
                {/* Filter Bar */}
                <FilterBar
                  filterOptions={filterOptions}
                  onFilterChange={setFilterOptions}
                  fileCount={filteredFiles.length}
                  totalSize="4.21 MB"
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
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
            {files.length > 0 && (
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
          />
        )}
      </div>

      {/* Dialogs */}
      <DriveSelectionDialog
        isOpen={showDriveSelection}
        onClose={() => setShowDriveSelection(false)}
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
              await apiService.cancelScan(currentScanId);
            } catch (error) {
              console.error('Failed to cancel scan:', error);
            }
          }
          setShowScanProgress(false);
          setScanProgress(prev => ({ ...prev, isScanning: false }));
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

      <SettingsDialog
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onSave={handleSaveSettings}
      />

      <ExplorerDialog
        isOpen={showExplorer}
        onClose={() => setShowExplorer(false)}
        initialPath={settings.general.defaultOutputPath}
      />
    </div>
  );
}

export default App;