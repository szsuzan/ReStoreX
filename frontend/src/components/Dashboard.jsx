import React, { useState, useEffect } from 'react';
import { 
  HardDrive, 
  Search, 
  Zap, 
  Activity, 
  Shield, 
  FileSearch, 
  Clock, 
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Info,
  Play,
  Settings,
  BarChart3,
  Cpu,
  Thermometer,
  Database
} from 'lucide-react';

/**
 * @param {Object} props
 * @param {(scanType: string) => void} props.onStartScan
 * @param {import('../types/index.js').DriveInfo[]} props.drives
 * @param {boolean} props.drivesLoading
 * @param {Object} props.statistics
 */
export function Dashboard({ onStartScan, drives, drivesLoading = false, statistics = {} }) {
  const [systemInfo, setSystemInfo] = useState({
    totalDrives: 0,
    healthyDrives: 0,
    damagedDrives: 0,
    lastScanTime: null,
    recoveredFiles: 0,
    totalRecoveredSize: '0 MB',
    successRate: 0
  });

  useEffect(() => {
    // Calculate system statistics
    const healthyCount = drives.filter(d => d.status === 'healthy').length;
    const damagedCount = drives.filter(d => d.status === 'damaged').length;
    
    // Format recovered size
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
    };
    
    // Calculate success rate
    const successRate = statistics.totalRecoveryAttempts > 0
      ? Math.round((statistics.successfulRecoveries / statistics.totalRecoveryAttempts) * 100)
      : 0;
    
    setSystemInfo({
      totalDrives: drives.length,
      healthyDrives: healthyCount,
      damagedDrives: damagedCount,
      lastScanTime: statistics.lastScanDate ? new Date(statistics.lastScanDate).toLocaleDateString() : 'Never',
      recoveredFiles: statistics.totalFilesRecovered || 0,
      totalRecoveredSize: formatBytes(statistics.totalSizeRecovered || 0),
      successRate: successRate
    });
  }, [drives, statistics]);

  const scanOptions = [
    {
      id: 'normal',
      title: 'Normal Scan',
      description: 'Standard scan for recently deleted files with good recovery chances',
      icon: Search,
      color: 'blue',
      estimatedTime: '5-15 minutes',
      recommended: true,
      features: ['Quick file detection', 'Recent deletions', 'High success rate']
    },
    {
      id: 'deep',
      title: 'Deep Scan',
      description: 'Comprehensive sector-by-sector analysis for maximum file recovery',
      icon: Zap,
      color: 'purple',
      estimatedTime: '30-120 minutes',
      recommended: false,
      features: ['Complete disk analysis', 'Fragmented files', 'Old deletions']
    },
    {
      id: 'cluster',
      title: 'Cluster Scan',
      description: 'Advanced cluster-level analysis for corrupted file systems',
      icon: Database,
      color: 'green',
      estimatedTime: '15-45 minutes',
      recommended: false,
      features: ['Cluster analysis', 'File system repair', 'Metadata recovery']
    },
    {
      id: 'health',
      title: 'Disk Health Scan',
      description: 'Analyze drive health, bad sectors, and overall disk condition',
      icon: Activity,
      color: 'orange',
      estimatedTime: '10-30 minutes',
      recommended: false,
      features: ['SMART analysis', 'Bad sector detection', 'Health assessment']
    },
    {
      id: 'signature',
      title: 'File Signature Scan',
      description: 'Raw file carving based on file signatures and headers',
      icon: FileSearch,
      color: 'indigo',
      estimatedTime: '20-60 minutes',
      recommended: false,
      features: ['File carving', 'Signature detection', 'Raw recovery']
    },
    {
      id: 'forensic',
      title: 'Forensic Scan',
      description: 'Professional forensic analysis with detailed logging',
      icon: Shield,
      color: 'red',
      estimatedTime: '60+ minutes',
      recommended: false,
      features: ['Forensic logging', 'Chain of custody', 'Evidence preservation']
    }
  ];

  const getColorClasses = (color, variant = 'primary') => {
    const colorMap = {
      blue: {
        primary: 'bg-blue-600 hover:bg-blue-700 text-white',
        secondary: 'bg-blue-50 text-blue-700 border-blue-200',
        icon: 'text-blue-600'
      },
      purple: {
        primary: 'bg-purple-600 hover:bg-purple-700 text-white',
        secondary: 'bg-purple-50 text-purple-700 border-purple-200',
        icon: 'text-purple-600'
      },
      green: {
        primary: 'bg-green-600 hover:bg-green-700 text-white',
        secondary: 'bg-green-50 text-green-700 border-green-200',
        icon: 'text-green-600'
      },
      orange: {
        primary: 'bg-orange-600 hover:bg-orange-700 text-white',
        secondary: 'bg-orange-50 text-orange-700 border-orange-200',
        icon: 'text-orange-600'
      },
      indigo: {
        primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
        secondary: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        icon: 'text-indigo-600'
      },
      red: {
        primary: 'bg-red-600 hover:bg-red-700 text-white',
        secondary: 'bg-red-50 text-red-700 border-red-200',
        icon: 'text-red-600'
      }
    };
    
    return colorMap[color]?.[variant] || colorMap.blue[variant];
  };

  const handleScanStart = (scanType) => {
    console.log(`Starting ${scanType} scan`);
    if (typeof onStartScan === 'function') {
      onStartScan(scanType);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">ReStoreX Dashboard</h1>
          <p className="text-gray-600">Professional data recovery and disk analysis tools</p>
        </div>

        {/* System Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <HardDrive className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Drives</p>
                <p className="text-2xl font-bold text-gray-900">{systemInfo.totalDrives}</p>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              {systemInfo.healthyDrives} healthy • {systemInfo.damagedDrives} damaged
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Files Recovered</p>
                <p className="text-2xl font-bold text-gray-900">{systemInfo.recoveredFiles.toLocaleString()}</p>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              Total size: {systemInfo.totalRecoveredSize}
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Last Scan</p>
                <p className="text-2xl font-bold text-gray-900">
                  {systemInfo.lastScanTime === 'Never' ? 'Never' : 
                   systemInfo.lastScanTime === new Date().toLocaleDateString() ? 'Today' : systemInfo.lastScanTime}
                </p>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              {statistics.totalScansCompleted || 0} total scans
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">{systemInfo.successRate}%</p>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              {statistics.successfulRecoveries || 0} of {statistics.totalRecoveryAttempts || 0} recoveries successful
            </div>
          </div>
        </div>

        {/* Drive Status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Connected Drives</h2>
            <p className="text-sm text-gray-600">Monitor and analyze your storage devices</p>
          </div>
          <div className="p-6">
            {drivesLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
                <p className="text-sm text-gray-600">Loading drives...</p>
              </div>
            ) : drives.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                  <HardDrive className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Drives Found</h3>
                <p className="text-sm text-gray-600 mb-4 max-w-md">
                  No storage drives were detected. Please make sure your drives are properly connected
                  and the backend server is running.
                </p>
                <button 
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Refresh
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {drives.map(drive => (
                <div key={drive.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    drive.status === 'healthy' ? 'bg-green-100' : 'bg-orange-100'
                  }`}>
                    <HardDrive className={`w-6 h-6 ${
                      drive.status === 'healthy' ? 'text-green-600' : 'text-orange-600'
                    }`} />
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">{drive.name}</h3>
                      {drive.status === 'healthy' ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-orange-600" />
                      )}
                    </div>
                    <div className="text-sm text-gray-600">
                      {drive.size} • {drive.fileSystem} • {drive.status}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors">
                      <Cpu className="w-3 h-3 inline mr-1" />
                      Health
                    </button>
                    <button className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors">
                      <Settings className="w-3 h-3 inline mr-1" />
                      Details
                    </button>
                  </div>
                </div>
              ))}
              </div>
            )}
          </div>
        </div>

        {/* Scan Options */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Recovery Scan Options</h2>
            <p className="text-sm text-gray-600">Choose the appropriate scan type for your recovery needs</p>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {scanOptions.map(option => {
                const Icon = option.icon;
                
                return (
                  <div
                    key={option.id}
                    className="group relative bg-white border-2 border-gray-200 rounded-xl p-6 hover:border-gray-300 hover:shadow-lg transition-all duration-200 cursor-pointer"
                    onClick={() => handleScanStart(option.id)}
                  >
                    {/* Recommended Badge */}
                    {option.recommended && (
                      <div className="absolute -top-2 -right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full font-medium">
                        Recommended
                      </div>
                    )}

                    {/* Icon */}
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 ${
                      getColorClasses(option.color, 'secondary')
                    } border`}>
                      <Icon className={`w-6 h-6 ${getColorClasses(option.color, 'icon')}`} />
                    </div>

                    {/* Content */}
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">{option.title}</h3>
                      <p className="text-sm text-gray-600 mb-3 leading-relaxed">
                        {option.description}
                      </p>
                      
                      {/* Features */}
                      <div className="space-y-1 mb-4">
                        {option.features.map((feature, index) => (
                          <div key={index} className="flex items-center gap-2 text-xs text-gray-600">
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                            {feature}
                          </div>
                        ))}
                      </div>

                      {/* Time Estimate */}
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>Estimated time: {option.estimatedTime}</span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <button
                      className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group-hover:shadow-md ${
                        getColorClasses(option.color, 'primary')
                      }`}
                    >
                      <Play className="w-4 h-4" />
                      Start {option.title}
                      <ChevronRight className="w-4 h-4 ml-auto group-hover:translate-x-1 transition-transform" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          {/* Recent Activity */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Deep scan completed</p>
                    <p className="text-xs text-gray-600">SD card (S:) • 2,847 files recovered</p>
                  </div>
                  <span className="text-xs text-gray-500">2 hours ago</span>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <HardDrive className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Drive health check</p>
                    <p className="text-xs text-gray-600">USB Drive (D:) • Status: Healthy</p>
                  </div>
                  <span className="text-xs text-gray-500">1 day ago</span>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                    <AlertTriangle className="w-4 h-4 text-orange-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Scan interrupted</p>
                    <p className="text-xs text-gray-600">External HDD • User cancelled</p>
                  </div>
                  <span className="text-xs text-gray-500">3 days ago</span>
                </div>
              </div>
            </div>
          </div>

          {/* System Performance */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">System Performance</h3>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                {/* CPU Usage */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium text-gray-700">CPU Usage</span>
                    </div>
                    <span className="text-sm text-gray-600">23%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '23%' }} />
                  </div>
                </div>

                {/* Memory Usage */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-green-600" />
                      <span className="text-sm font-medium text-gray-700">Memory</span>
                    </div>
                    <span className="text-sm text-gray-600">4.2 GB / 16 GB</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: '26%' }} />
                  </div>
                </div>

                {/* Temperature */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Thermometer className="w-4 h-4 text-orange-600" />
                      <span className="text-sm font-medium text-gray-700">Temperature</span>
                    </div>
                    <span className="text-sm text-gray-600">42°C</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-orange-600 h-2 rounded-full" style={{ width: '42%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tips and Information */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Info className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Recovery Tips</h3>
              <div className="space-y-2 text-sm text-gray-700">
                <p>• <strong>Stop using the drive immediately</strong> to prevent overwriting deleted files</p>
                <p>• <strong>Start with Normal Scan</strong> for recently deleted files - it's faster and often sufficient</p>
                <p>• <strong>Use Deep Scan</strong> only when Normal Scan doesn't find your files</p>
                <p>• <strong>Check drive health</strong> before recovery if you suspect hardware issues</p>
                <p>• <strong>Save recovered files</strong> to a different drive to avoid data corruption</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}