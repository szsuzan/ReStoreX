import React, { useState } from 'react';
import { Home, CheckCircle, Search, Minimize2, Square, X, AlertCircle, Clock } from 'lucide-react';

/**
 * @param {Object} props
 * @param {string} props.scanStatus
 * @param {() => void} props.onMinimize
 * @param {() => void} props.onMaximize
 * @param {() => void} props.onClose
 * @param {string} props.searchQuery
 * @param {(query: string) => void} props.onSearchChange
 */
export function Header({ scanStatus, onMinimize, onMaximize, onClose, searchQuery, onSearchChange }) {
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const getStatusIcon = () => {
    if (scanStatus && scanStatus.includes('completed')) {
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    } else if (scanStatus && scanStatus.includes('scanning')) {
      return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
    } else if (scanStatus && scanStatus.includes('error')) {
      return <AlertCircle className="w-4 h-4 text-red-600" />;
    }
    return <CheckCircle className="w-4 h-4 text-green-600" />;
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors group">
          <Home className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
        </button>
        
        <div className="flex items-center gap-3 text-sm">
          {getStatusIcon()}
          <div>
            <span className="font-semibold text-gray-800">
              {scanStatus && scanStatus.includes('SD card') ? 'SD card (S:)' : 'ReStoreX'}
            </span>
            <span className="text-gray-600 ml-2">{scanStatus || 'Ready'}</span>
          </div>
        </div>
      </div>

      {/* Center Section - Search */}
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

      {/* Right Section - Window Controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={onMinimize}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
          title="Minimize"
        >
          <Minimize2 className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
        </button>
        <button
          onClick={onMaximize}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
          title="Maximize"
        >
          <Square className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
        </button>
        <button
          onClick={onClose}
          className="p-2 hover:bg-red-100 rounded-lg transition-colors group"
          title="Close"
        >
          <X className="w-4 h-4 text-red-600 group-hover:text-red-700" />
        </button>
      </div>
    </div>
  );
}