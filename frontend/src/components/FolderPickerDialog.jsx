import React, { useState, useEffect, useCallback } from 'react';
import { X, Folder, ChevronRight, HardDrive, Home, Check } from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * Simple folder picker dialog
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {(path: string) => void} props.onSelect
 * @param {string} props.initialPath
 * @param {string} props.title
 */
export function FolderPickerDialog({ isOpen, onClose, onSelect, initialPath = 'C:\\Users', title = 'Select Folder' }) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [folders, setFolders] = useState([]);
  const [drives, setDrives] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [quickPaths] = useState([
    { name: 'Desktop', path: 'C:\\Users\\Public\\Desktop' },
    { name: 'Documents', path: 'C:\\Users\\Public\\Documents' },
    { name: 'Downloads', path: 'C:\\Users\\Public\\Downloads' },
    { name: 'C:\\ Drive', path: 'C:\\' },
  ]);

  const loadDrives = async () => {
    try {
      const response = await apiService.getDrives();
      if (response && response.drives) {
        setDrives(response.drives);
      }
    } catch (err) {
      console.error('Failed to load drives:', err);
    }
  };

  const loadFolders = useCallback(async (path) => {
    console.log('Loading folders from:', path);
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getDirectoryContents(path);
      console.log('API Response:', response);
      
      if (response && response.items) {
        // Filter to show only folders (backend returns type: "folder")
        const folderItems = response.items.filter(item => item.type === 'folder');
        console.log('Filtered folders:', folderItems.length);
        setFolders(folderItems);
      } else {
        console.log('No items in response');
        setFolders([]);
      }
    } catch (err) {
      console.error('Failed to load folders:', err);
      setError('Failed to load folders. You may not have permission to access this directory.');
      setFolders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen && currentPath) {
      loadDrives();
      loadFolders(currentPath);
    }
  }, [isOpen, currentPath, loadFolders]);

  const handleFolderClick = (folderPath) => {
    setCurrentPath(folderPath);
  };

  const handleSelectCurrent = () => {
    onSelect(currentPath);
    onClose();
  };

  const goToParent = () => {
    const parts = currentPath.split('\\').filter(p => p);
    if (parts.length > 1) {
      // Go up one level
      const parentPath = parts.slice(0, -1).join('\\');
      setCurrentPath(parentPath);
    } else if (parts.length === 1) {
      // We're at drive root (e.g., "C"), stay here
      setCurrentPath(parts[0] + ':\\');
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 100000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Current Path Breadcrumb */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <label className="block text-xs font-medium text-gray-600 mb-2">
            Current Path:
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={currentPath}
              onChange={(e) => setCurrentPath(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  loadFolders(currentPath);
                }
              }}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
              placeholder="C:\Users\YourName\Documents"
            />
            <button
              onClick={() => loadFolders(currentPath)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Go
            </button>
          </div>
        </div>

        {/* Quick Access */}
        <div className="px-6 py-3 bg-white border-b border-gray-200">
          <label className="block text-xs font-medium text-gray-600 mb-2">
            Quick Access:
          </label>
          <div className="flex gap-2 flex-wrap">
            {quickPaths.map((quick, index) => (
              <button
                key={index}
                onClick={() => setCurrentPath(quick.path)}
                className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium transition-colors"
              >
                {quick.name}
              </button>
            ))}
          </div>
        </div>

        {/* Drives Selector */}
        {drives.length > 0 && (
          <div className="px-6 py-3 bg-white border-b border-gray-200">
            <label className="block text-xs font-medium text-gray-600 mb-2">
              Available Drives:
            </label>
            <div className="flex gap-2 flex-wrap">
              {drives.map((drive) => (
                <button
                  key={drive.id}
                  onClick={() => {
                    // Extract drive letter (e.g., "C:" from "c--c" or similar)
                    const driveLetter = drive.name.charAt(0).toUpperCase();
                    setCurrentPath(driveLetter + ':\\');
                  }}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    currentPath.startsWith(drive.name.charAt(0).toUpperCase())
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4" />
                    <span>{drive.name}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Folder List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-red-600">
              {error}
            </div>
          )}

          {!loading && !error && folders.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No subfolders in this directory
            </div>
          )}

          {!loading && !error && folders.length > 0 && (
            <div className="space-y-1">
              {/* Parent folder option */}
              {currentPath.split('\\').filter(p => p).length > 1 && (
                <button
                  onClick={goToParent}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 rounded-lg transition-colors text-left"
                >
                  <Folder className="w-5 h-5 text-gray-400" />
                  <span className="text-gray-600">..</span>
                </button>
              )}

              {/* Folder list */}
              {folders.map((folder, index) => (
                <button
                  key={index}
                  onClick={() => handleFolderClick(folder.path)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-blue-50 rounded-lg transition-colors text-left group"
                >
                  <Folder className="w-5 h-5 text-blue-500 group-hover:text-blue-600" />
                  <span className="text-gray-700 group-hover:text-gray-900 truncate">
                    {folder.name}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer with selected path and actions */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Selected Path:
            </label>
            <div className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 font-mono">
              {currentPath}
            </div>
          </div>
          
          <div className="flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSelectCurrent}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
            >
              <Check className="w-4 h-4" />
              Select This Folder
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
