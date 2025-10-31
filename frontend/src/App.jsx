import React, { useState, useEffect } from 'react';
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

  // Load drives on mount
  useEffect(() => {
    loadDrives();
  }, []);

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubscribeScan = subscribe('scan_progress', (data) => {
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
        console.log('Scan completed via WebSocket, loading results...');
        loadScanResults(currentScanId);
        // Update statistics
        setStatistics(prev => ({
          ...prev,
          totalScansCompleted: prev.totalScansCompleted + 1,
          lastScanDate: new Date()
        }));
        // Close the scan progress dialog after a short delay
        setTimeout(() => {
          setShowScanProgress(false);
        }, 1000);
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
          alert(`Recovery completed successfully!\n\n${recoveredCount} files recovered to:\n${settings.general.defaultOutputPath}`);
        }, 1000);
      }
    });

    return () => {
      unsubscribeScan();
      unsubscribeRecovery();
    };
  }, [subscribe, currentScanId]);

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
      alert(`Failed to load drives: ${error.message}\n\nPlease make sure the backend server is running on http://localhost:8000`);
    } finally {
      setDrivesLoading(false);
    }
  };

  const loadScanResults = async (scanId) => {
    try {
      console.log('Loading scan results for scan:', scanId);
      const results = await apiService.getScanResults(scanId, {});
      console.log('Scan results loaded:', results.length, 'files');
      setFiles(results);
      setScanResults(generateScanResultsTree(results));
      
      // Switch to files view and clear filters to show all results
      setCurrentView('files');
      setSelectedCategory('All Files');
      setFilterOptions(prev => ({ ...prev, fileType: '' }));
    } catch (error) {
      console.error('Failed to load scan results:', error);
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
    setCurrentView('files');
    setSelectedCategory(category);
    if (['RAW', 'PNG', 'JPG', 'HEIC', 'AI', 'PDF', 'MP4'].includes(category)) {
      setFilterOptions(prev => ({ ...prev, fileType: category }));
    } else {
      setFilterOptions(prev => ({ ...prev, fileType: '' }));
    }
  };

  const handleStartNewScan = (scanType = 'normal') => {
    console.log('handleStartNewScan called with scan type:', scanType);
    setCurrentView('files');
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
          console.log('Scan status update:', status);
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            clearInterval(pollInterval);
            if (status.status === 'completed') {
              console.log('Scan completed, loading results...');
              await loadScanResults(response.scanId);
              // Update statistics
              setStatistics(prev => ({
                ...prev,
                totalScansCompleted: prev.totalScansCompleted + 1,
                lastScanDate: new Date()
              }));
              // Close dialog and navigate to files view
              setTimeout(() => {
                setShowScanProgress(false);
              }, 1000);
            } else if (status.status === 'failed') {
              setShowScanProgress(false);
              alert('Scan failed: ' + (status.error || 'Unknown error'));
            }
          }
        } catch (error) {
          console.error('Failed to poll scan status:', error);
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start scan:', error);
      alert('Failed to start scan: ' + error.message);
    }
  };

  const handleRecover = async () => {
    const selectedFiles = files.filter(f => f.isSelected);
    console.log('handleRecover called. Total files:', files.length, 'Selected files:', selectedFiles.length);
    
    if (selectedFiles.length === 0) {
      alert('Please select files to recover');
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
                alert(`Recovery completed successfully!\n\n${recoveredCount} files recovered to:\n${settings.general.defaultOutputPath}`);
              }, 1000);
            } else if (status.status === 'failed') {
              setShowRecoveryProgress(false);
              // Update failure stats
              setStatistics(prev => ({
                ...prev,
                totalRecoveryAttempts: prev.totalRecoveryAttempts + 1
              }));
              alert('Recovery failed: ' + (status.error || 'Unknown error'));
            }
          }
        } catch (error) {
          console.error('Failed to poll recovery status:', error);
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to start recovery:', error);
      alert('Failed to start recovery: ' + error.message);
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
      alert('Failed to recover file: ' + error.message);
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
      {/* Window Header */}
      <Header 
        scanStatus="Scan completed successfully"
        searchQuery={filterOptions.searchQuery}
        onSearchChange={(query) => setFilterOptions(prev => ({ ...prev, searchQuery: query }))}
        onMinimize={() => handleWindowAction('minimize')}
        onMaximize={() => handleWindowAction('maximize')}
        onClose={() => handleWindowAction('close')}
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
          onViewChange={setCurrentView}
          onShowInExplorer={handleShowInExplorer}
          onOpenSettings={handleOpenSettings}
        />

        {/* Main Content Area */}
        {currentView === 'dashboard' ? (
          <Dashboard 
            onStartScan={handleStartNewScan}
            drives={drives}
            drivesLoading={drivesLoading}
            statistics={statistics}
          />
        ) : (
          <div className="flex-1 flex flex-col">
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

            {/* Footer */}
            <Footer
              selectedCount={selectedFiles.length}
              totalSize={formatBytes(totalSelectedSize)}
              totalFiles={files.length}
              onRecover={handleRecover}
              onSelectOutputFolder={handleSelectOutputFolder}
            />
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