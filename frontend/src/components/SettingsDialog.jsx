import React, { useState, useEffect } from 'react';
import { 
  X, 
  Settings, 
  Folder, 
  HardDrive, 
  Clock, 
  Shield, 
  Monitor, 
  Bell,
  Save,
  RotateCcw,
  Info,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {Object} props.settings
 * @param {(settings: Object) => void} props.onSave
 * @param {(mode: 'output' | 'temp') => void} props.onBrowse - Callback when browse button clicked
 */
export function SettingsDialog({ isOpen, onClose, settings, onSave, onBrowse }) {
  const [activeTab, setActiveTab] = useState('general');
  const [localSettings, setLocalSettings] = useState(settings);

  // Sync localSettings when settings prop changes
  useEffect(() => {
    if (settings) {
      console.log('SettingsDialog: Settings received:', settings);
      setLocalSettings(settings);
    }
  }, [settings]);

  console.log('SettingsDialog render - isOpen:', isOpen, 'localSettings:', localSettings);
  console.log('Safety checks:', {
    hasLocalSettings: !!localSettings,
    hasGeneral: !!(localSettings && localSettings.general),
    hasRecovery: !!(localSettings && localSettings.recovery),
    hasPerformance: !!(localSettings && localSettings.performance),
    hasNotifications: !!(localSettings && localSettings.notifications),
    hasAdvanced: !!(localSettings && localSettings.advanced)
  });

  if (!isOpen) return null;

  // Safety check - don't render if localSettings is not properly initialized
  if (!localSettings || !localSettings.general || !localSettings.recovery || 
      !localSettings.performance || !localSettings.notifications || !localSettings.advanced) {
    console.log('SettingsDialog: localSettings not initialized properly');
    return null;
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'recovery', label: 'Recovery', icon: HardDrive },
    { id: 'performance', label: 'Performance', icon: Monitor },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'advanced', label: 'Advanced', icon: Shield }
  ];

  const handleSave = () => {
    onSave(localSettings);
    
    // Show success notification
    if (typeof window !== 'undefined') {
      const successMsg = document.createElement('div');
      successMsg.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center gap-2';
      successMsg.innerHTML = `
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
        </svg>
        Settings saved successfully!
      `;
      document.body.appendChild(successMsg);
      setTimeout(() => {
        if (document.body.contains(successMsg)) {
          document.body.removeChild(successMsg);
        }
      }, 3000);
    }
    
    onClose();
  };

  const handleReset = () => {
    setLocalSettings(settings);
  };

  const updateSetting = (category, key, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const renderGeneralSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Default Paths</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default Recovery Output Directory
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localSettings.general.defaultOutputPath}
                onChange={(e) => updateSetting('general', 'defaultOutputPath', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button 
                onClick={() => {
                  onBrowse('output');
                }}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                title="Browse for folder"
              >
                <Folder className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temporary Files Directory
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localSettings.general.tempPath}
                onChange={(e) => updateSetting('general', 'tempPath', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button 
                onClick={() => {
                  onBrowse('temp');
                }}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                title="Browse for folder"
              >
                <Folder className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Interface</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Auto-refresh file list</label>
              <p className="text-xs text-gray-500">Automatically refresh when new files are found</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.general.autoRefresh}
              onChange={(e) => updateSetting('general', 'autoRefresh', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Show file thumbnails</label>
              <p className="text-xs text-gray-500">Display image previews in file grid</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.general.showThumbnails}
              onChange={(e) => updateSetting('general', 'showThumbnails', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Confirm before recovery</label>
              <p className="text-xs text-gray-500">Show confirmation dialog before starting recovery</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.general.confirmRecovery}
              onChange={(e) => updateSetting('general', 'confirmRecovery', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderRecoverySettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recovery Options</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Preserve original timestamps</label>
              <p className="text-xs text-gray-500">Keep original file creation and modification dates</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.recovery.preserveTimestamps}
              onChange={(e) => updateSetting('recovery', 'preserveTimestamps', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Create subdirectories by type</label>
              <p className="text-xs text-gray-500">Organize recovered files into folders by file type</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.recovery.createSubdirectories}
              onChange={(e) => updateSetting('recovery', 'createSubdirectories', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Verify recovered files</label>
              <p className="text-xs text-gray-500">Check file integrity after recovery</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.recovery.verifyFiles}
              onChange={(e) => updateSetting('recovery', 'verifyFiles', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">File Handling</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              When duplicate files are found
            </label>
            <select
              value={localSettings.recovery.duplicateHandling}
              onChange={(e) => updateSetting('recovery', 'duplicateHandling', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="skip">Skip duplicate files</option>
              <option value="rename">Rename with number suffix</option>
              <option value="overwrite">Overwrite existing files</option>
              <option value="ask">Ask for each file</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Maximum file size to recover (MB)
            </label>
            <input
              type="number"
              value={localSettings.recovery.maxFileSize}
              onChange={(e) => updateSetting('recovery', 'maxFileSize', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="1"
              max="10000"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderPerformanceSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Scan Performance</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Maximum concurrent scans
            </label>
            <select
              value={localSettings.performance.maxConcurrentScans}
              onChange={(e) => updateSetting('performance', 'maxConcurrentScans', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value={1}>1 (Recommended)</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Scan priority
            </label>
            <select
              value={localSettings.performance.scanPriority}
              onChange={(e) => updateSetting('performance', 'scanPriority', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="low">Low (Background)</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Memory usage limit (MB)
            </label>
            <input
              type="number"
              value={localSettings.performance.memoryLimit}
              onChange={(e) => updateSetting('performance', 'memoryLimit', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="512"
              max="8192"
              step="256"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Cache Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Enable scan result caching</label>
              <p className="text-xs text-gray-500">Cache scan results for faster subsequent access</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.performance.enableCaching}
              onChange={(e) => updateSetting('performance', 'enableCaching', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cache size limit (MB)
            </label>
            <input
              type="number"
              value={localSettings.performance.cacheSize}
              onChange={(e) => updateSetting('performance', 'cacheSize', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="100"
              max="2048"
              step="100"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderNotificationSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Scan Notifications</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Notify when scan completes</label>
              <p className="text-xs text-gray-500">Show notification when scanning finishes</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.notifications.scanComplete}
              onChange={(e) => updateSetting('notifications', 'scanComplete', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Notify when recovery completes</label>
              <p className="text-xs text-gray-500">Show notification when file recovery finishes</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.notifications.recoveryComplete}
              onChange={(e) => updateSetting('notifications', 'recoveryComplete', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Show progress notifications</label>
              <p className="text-xs text-gray-500">Display periodic progress updates</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.notifications.progressUpdates}
              onChange={(e) => updateSetting('notifications', 'progressUpdates', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Sound Alerts</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Enable sound notifications</label>
              <p className="text-xs text-gray-500">Play sounds for important events</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.notifications.soundEnabled}
              onChange={(e) => updateSetting('notifications', 'soundEnabled', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notification volume
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={localSettings.notifications.volume}
              onChange={(e) => updateSetting('notifications', 'volume', parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Silent</span>
              <span>{localSettings.notifications.volume}%</span>
              <span>Loud</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAdvancedSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logging</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Log level
            </label>
            <select
              value={localSettings.advanced.logLevel}
              onChange={(e) => updateSetting('advanced', 'logLevel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="error">Error only</option>
              <option value="warn">Warning and above</option>
              <option value="info">Info and above</option>
              <option value="debug">Debug (All)</option>
            </select>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Enable detailed logging</label>
              <p className="text-xs text-gray-500">Log detailed scan and recovery operations</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.advanced.detailedLogging}
              onChange={(e) => updateSetting('advanced', 'detailedLogging', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Security</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Require admin privileges</label>
              <p className="text-xs text-gray-500">Request elevated permissions for disk access</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.advanced.requireAdmin}
              onChange={(e) => updateSetting('advanced', 'requireAdmin', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Secure file deletion</label>
              <p className="text-xs text-gray-500">Securely delete temporary files after recovery</p>
            </div>
            <input
              type="checkbox"
              checked={localSettings.advanced.secureDelete}
              onChange={(e) => updateSetting('advanced', 'secureDelete', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-yellow-800 mb-1">Advanced Settings Warning</h4>
            <p className="text-xs text-yellow-700">
              Modifying these settings may affect recovery performance and system stability. 
              Only change these if you understand the implications.
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings();
      case 'recovery':
        return renderRecoverySettings();
      case 'performance':
        return renderPerformanceSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'advanced':
        return renderAdvancedSettings();
      default:
        return renderGeneralSettings();
    }
  };

  console.log('SettingsDialog: ABOUT TO RETURN JSX');

  return (
    <div 
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={(e) => {
        console.log('Overlay clicked');
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          width: '800px',
          height: '600px',
          maxWidth: '90vw',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <Settings className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900">ReStoreX Settings</h2>
          </div>
          <button
            onClick={() => {
              console.log('Close button clicked');
              onClose();
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 bg-gray-50 border-r border-gray-200 p-4">
            <div className="space-y-1">
              {tabs.map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors ${
                      activeTab === tab.id 
                        ? 'bg-blue-600 text-white' 
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {renderTabContent()}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Info className="w-4 h-4" />
            <span>Changes will be applied immediately</span>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-6 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}