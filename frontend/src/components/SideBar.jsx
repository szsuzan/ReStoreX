import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  Menu, 
  LayoutDashboard, 
  HardDrive, 
  Image, 
  Video, 
  Music, 
  FileText, 
  Archive, 
  File,
  Settings,
  Info,
  ExternalLink,
  X
} from 'lucide-react';

/**
 * @param {Object} props
 * @param {import('../types/index.js').ScanResult[]} props.scanResults
 * @param {string} props.selectedCategory
 * @param {(category: string) => void} props.onCategorySelect
 * @param {boolean} props.isCollapsed
 * @param {() => void} props.onToggleCollapse
 * @param {() => void} props.onStartNewScan
 * @param {string} props.currentView
 * @param {(view: string) => void} props.onViewChange
 * @param {() => void} props.onShowInExplorer
 * @param {() => void} props.onOpenSettings
 * @param {Array} props.scanTabs - Array of scan tab objects
 * @param {number} props.activeTabId - Currently active tab ID
 * @param {(tabId: number) => void} props.onSwitchTab - Function to switch tabs
 * @param {(tabId: number) => void} props.onCloseTab - Function to close tabs
 */
export function Sidebar({ 
  scanResults, 
  selectedCategory, 
  onCategorySelect, 
  isCollapsed, 
  onToggleCollapse,
  onStartNewScan,
  currentView,
  onViewChange,
  onShowInExplorer,
  onOpenSettings,
  scanTabs = [],
  activeTabId,
  onSwitchTab,
  onCloseTab
}) {
  const [expandedItems, setExpandedItems] = useState(new Set(['SD card (S:)', 'Pictures']));

  const iconMap = {
    HardDrive,
    Image,
    Video,
    Music,
    FileText,
    Archive,
    File,
    FileImage: Image,
  };

  const toggleExpanded = (itemName) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemName)) {
      newExpanded.delete(itemName);
    } else {
      newExpanded.add(itemName);
    }
    setExpandedItems(newExpanded);
  };

  const renderScanResult = (result, depth = 0) => {
    const Icon = iconMap[result.icon] || File;
    const isSelected = selectedCategory === result.name;
    const hasChildren = result.children && result.children.length > 0;
    const isExpanded = expandedItems.has(result.name);
    
    return (
      <div key={result.name}>
        <div className="flex">
          <button
            onClick={() => onCategorySelect(result.name)}
            className={`flex-1 flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-100 transition-all duration-200 ${
              isSelected ? 'bg-blue-50 border-r-2 border-blue-600 text-blue-700' : 'text-gray-700'
            }`}
            style={{ paddingLeft: `${16 + depth * 20}px` }}
          >
            <Icon className={`w-4 h-4 ${isSelected ? 'text-blue-600' : 'text-gray-500'}`} />
            <span className="flex-1 text-sm font-medium">{result.name}</span>
            <span className={`text-xs px-2 py-1 rounded-full ${
              isSelected ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {result.count.toLocaleString()}
            </span>
          </button>
          
          {hasChildren && (
            <button
              onClick={() => toggleExpanded(result.name)}
              className="p-2 hover:bg-gray-100 transition-colors"
            >
              {isExpanded ? 
                <ChevronDown className="w-4 h-4 text-gray-400" /> : 
                <ChevronRight className="w-4 h-4 text-gray-400" />
              }
            </button>
          )}
        </div>
        
        {hasChildren && isExpanded && (
          <div className="border-l border-gray-200 ml-6">
            {result.children.map(child => renderScanResult(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`bg-gray-50 border-r border-gray-200 transition-all duration-300 flex flex-col ${
      isCollapsed ? 'w-16' : 'w-80'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-gray-200 bg-white">
        <button 
          onClick={onToggleCollapse}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <Menu className="w-5 h-5 text-gray-600 group-hover:text-gray-800" />
        </button>
        {!isCollapsed && (
          <button 
            onClick={() => onViewChange('dashboard')}
            className="flex items-center gap-2 hover:bg-gray-50 px-2 py-1 rounded-lg transition-colors cursor-pointer"
            title="Go to Dashboard"
          >
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-gray-800">ReStoreX</h1>
          </button>
        )}
      </div>

      {!isCollapsed && (
        <>
          {/* Navigation */}
          <div className="p-4 border-b border-gray-200 bg-white">
            <div className="space-y-1">
              <button 
                onClick={() => onViewChange('dashboard')}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left rounded-lg transition-colors group ${
                  currentView === 'dashboard' 
                    ? 'bg-blue-600 text-white' 
                    : 'hover:bg-blue-600 hover:text-white text-gray-700'
                }`}
              >
                <LayoutDashboard className={`w-4 h-4 ${
                  currentView === 'dashboard' ? 'text-white' : 'text-gray-500 group-hover:text-white'
                }`} />
                <span className="text-sm font-medium">Dashboard</span>
              </button>
              
              <button 
                onClick={onShowInExplorer}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left rounded-lg transition-colors group hover:bg-blue-600 hover:text-white text-gray-700"
              >
                <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-white" />
                <span className="text-sm font-medium">Show in Explorer</span>
              </button>
              
              <button 
                onClick={onOpenSettings}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left rounded-lg transition-colors group hover:bg-blue-600 hover:text-white text-gray-700"
              >
                <Settings className="w-4 h-4 text-gray-500 group-hover:text-white" />
                <span className="text-sm font-medium">Settings</span>
              </button>
              
              <button className="w-full flex items-center gap-3 px-4 py-2.5 text-left rounded-lg transition-colors group hover:bg-blue-600 hover:text-white text-gray-700">
                <Info className="w-4 h-4 text-gray-500 group-hover:text-white" />
                <span className="text-sm font-medium">About</span>
              </button>
            </div>
          </div>

          {/* Scan Results */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <h2 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
                Scan Results
              </h2>
              
              {/* Show Scan Tabs if available */}
              {scanTabs.length > 0 ? (
                <div className="space-y-1 mb-4">
                  {scanTabs.map(tab => (
                    <div key={tab.id} className="flex items-center group">
                      <button
                        onClick={() => onSwitchTab(tab.id)}
                        className={`flex-1 flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-100 transition-all duration-200 rounded-l-lg ${
                          tab.id === activeTabId ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                        }`}
                      >
                        <File className={`w-4 h-4 ${tab.id === activeTabId ? 'text-blue-600' : 'text-gray-500'}`} />
                        <span className="flex-1 text-sm truncate">{tab.name}</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCloseTab(tab.id);
                        }}
                        className={`px-2 py-2.5 hover:bg-red-50 hover:text-red-600 transition-colors rounded-r-lg opacity-0 group-hover:opacity-100 ${
                          tab.id === activeTabId ? 'bg-blue-50' : ''
                        }`}
                        title="Close tab"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
              
              {/* Show hierarchical scan results tree */}
              <div className="space-y-1">
                {scanResults.map(result => renderScanResult(result))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}