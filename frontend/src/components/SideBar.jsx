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
  ExternalLink
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
  onOpenSettings
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
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-gray-800">ReStoreX</h1>
          </div>
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
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <LayoutDashboard className={`w-4 h-4 ${
                  currentView === 'dashboard' ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'
                }`} />
                <span className="text-sm font-medium">Dashboard</span>
              </button>
              
              <button 
                onClick={onStartNewScan}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-white group"
              >
                <HardDrive className="w-4 h-4" />
                <span className="text-sm font-medium">New Scan</span>
              </button>
            </div>
          </div>

          {/* Scan Results */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <h2 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
                Scan Results
              </h2>
              <div className="space-y-1">
                {scanResults.map(result => renderScanResult(result))}
              </div>
            </div>
          </div>

          {/* Bottom Actions */}
          <div className="p-4 border-t border-gray-200 bg-white space-y-2">
            <button 
              onClick={onShowInExplorer}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-100 rounded-lg transition-colors text-gray-700 group">
              <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-gray-700" />
              <span className="text-sm">Show in Explorer</span>
            </button>
            
            <button 
              onClick={onOpenSettings}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-100 rounded-lg transition-colors text-gray-700 group">
              <Settings className="w-4 h-4 text-gray-500 group-hover:text-gray-700" />
              <span className="text-sm">Settings</span>
            </button>
            
            <button className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-100 rounded-lg transition-colors text-gray-700 group">
              <Info className="w-4 h-4 text-gray-500 group-hover:text-gray-700" />
              <span className="text-sm">About</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}