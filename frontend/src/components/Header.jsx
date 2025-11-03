import React, { useState } from 'react';
import { Home, CheckCircle, Search, AlertCircle, Clock, Loader2 } from 'lucide-react';

/**
 * @param {Object} props
 * @param {string} props.scanStatus
 * @param {string} props.searchQuery
 * @param {(query: string) => void} props.onSearchChange
 * @param {() => void} props.onNavigateToDashboard
 * @param {boolean} props.showSearch - Whether to show the search bar
 * @param {boolean} props.isBackgroundScan - Whether a scan is running in background
 * @param {Object} props.scanProgress - Current scan progress
 * @param {() => void} props.onReopenScan - Callback to reopen scan dialog
 */
export function Header({ 
  scanStatus, 
  searchQuery, 
  onSearchChange, 
  onNavigateToDashboard, 
  showSearch = true,
  isBackgroundScan = false,
  scanProgress = {},
  onReopenScan
}) {
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const getStatusIcon = () => {
    if (scanStatus && scanStatus.includes('scanning')) {
      return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
    } else if (scanStatus && scanStatus.includes('error')) {
      return <AlertCircle className="w-4 h-4 text-red-600" />;
    } else if (scanStatus && scanStatus.includes('found')) {
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    }
    return <Home className="w-4 h-4 text-gray-600" />;
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
      {/* Left Section - Status */}
      <div className="flex items-center gap-3">
        {getStatusIcon()}
        <div className="text-sm">
          <span className="text-gray-600">{scanStatus || 'Ready'}</span>
        </div>
      </div>

      {/* Center Section - Background Scan Indicator or Search */}
      {isBackgroundScan ? (
        <div 
          onClick={onReopenScan}
          className="flex items-center gap-3 px-4 py-2 bg-blue-50 hover:bg-blue-100 rounded-lg cursor-pointer transition-all duration-200 border border-blue-200 shadow-sm"
          title="Click to view scan progress"
        >
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <div className="flex flex-col">
            <span className="text-sm font-medium text-blue-900">Scanning in Background</span>
            <div className="flex items-center gap-2 text-xs text-blue-700">
              <span>{scanProgress.progress?.toFixed(1) || 0}%</span>
              <span>•</span>
              <span>{scanProgress.filesFound || 0} files found</span>
            </div>
          </div>
        </div>
      ) : showSearch ? (
        <div className="flex-1 max-w-md mx-8">
          <div className={`relative transition-all duration-200 ${isSearchFocused ? 'scale-105' : ''}`}>
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setIsSearchFocused(false)}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-all duration-200"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}