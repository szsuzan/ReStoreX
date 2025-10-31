import React, { useState, useEffect } from 'react';
import { 
  X, 
  Folder, 
  FolderOpen, 
  File, 
  ExternalLink, 
  Copy, 
  Trash2,
  RefreshCw,
  Home,
  ChevronRight,
  HardDrive,
  Image,
  FileText,
  Video,
  Music,
  Archive,
  AlertCircle
} from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {string} props.initialPath
 */
export function ExplorerDialog({ isOpen, onClose, initialPath = 'C:\\RecoveredFiles' }) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [files, setFiles] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadDirectory(currentPath);
    }
  }, [isOpen, currentPath]);

  const loadDirectory = async (path) => {
    setLoading(true);
    setError(null);
    try {
      console.log('Loading directory:', path);
      const response = await apiService.getDirectoryContents(path);
      console.log('Directory contents:', response);
      
      if (response && response.items) {
        setFiles(response.items);
      } else {
        setFiles([]);
      }
    } catch (err) {
      console.error('Failed to load directory:', err);
      setError(err.message || 'Failed to load directory contents');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const getFileIcon = (item) => {
    if (item.type === 'folder') {
      return <Folder className="w-5 h-5 text-blue-600" />;
    }
    
    switch (item.extension?.toLowerCase()) {
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'raw':
      case 'heic':
        return <Image className="w-5 h-5 text-green-600" />;
      case 'pdf':
      case 'doc':
      case 'docx':
      case 'txt':
        return <FileText className="w-5 h-5 text-red-600" />;
      case 'mp4':
      case 'avi':
      case 'mov':
        return <Video className="w-5 h-5 text-purple-600" />;
      case 'mp3':
      case 'wav':
      case 'flac':
        return <Music className="w-5 h-5 text-orange-600" />;
      case 'zip':
      case 'rar':
      case '7z':
        return <Archive className="w-5 h-5 text-yellow-600" />;
      default:
        return <File className="w-5 h-5 text-gray-600" />;
    }
  };

  const navigateToPath = (path) => {
    setCurrentPath(path);
    setSelectedItems(new Set());
  };

  const navigateUp = () => {
    const parentPath = currentPath.split('\\').slice(0, -1).join('\\');
    if (parentPath && parentPath !== currentPath) {
      navigateToPath(parentPath);
    }
  };

  const handleItemClick = (item) => {
    if (item.type === 'folder') {
      navigateToPath(item.path);
    }
  };

  const handleItemSelect = (itemId) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const openInSystemExplorer = async () => {
    try {
      console.log(`Opening ${currentPath} in Windows Explorer`);
      await apiService.openInSystemExplorer(currentPath);
    } catch (error) {
      console.error('Failed to open in system explorer:', error);
    }
  };

  const copyPath = () => {
    navigator.clipboard.writeText(currentPath);
  };

  const refreshDirectory = () => {
    loadDirectory(currentPath);
  };

  const getPathSegments = () => {
    return currentPath.split('\\').filter(segment => segment);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[900px] h-[700px] max-w-[90vw] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <FolderOpen className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900">File Explorer</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-3 p-4 border-b border-gray-200 bg-gray-50">
          <button
            onClick={navigateUp}
            disabled={currentPath === 'C:' || !currentPath.includes('\\')}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Go up one level"
          >
            <ChevronRight className="w-4 h-4 rotate-180" />
          </button>
          
          <button
            onClick={() => navigateToPath('C:\\')}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            title="Go to root"
          >
            <Home className="w-4 h-4" />
          </button>
          
          <button
            onClick={refreshDirectory}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <div className="flex-1 mx-4">
            <div className="flex items-center gap-1 text-sm text-gray-600 bg-white border border-gray-300 rounded-lg px-3 py-2">
              <HardDrive className="w-4 h-4" />
              {getPathSegments().map((segment, index) => (
                <React.Fragment key={index}>
                  <button
                    onClick={() => navigateToPath(getPathSegments().slice(0, index + 1).join('\\'))}
                    className="hover:text-blue-600 transition-colors"
                  >
                    {segment}
                  </button>
                  {index < getPathSegments().length - 1 && (
                    <ChevronRight className="w-3 h-3 text-gray-400" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
          
          <button
            onClick={openInSystemExplorer}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
          >
            <ExternalLink className="w-4 h-4" />
            Open in Explorer
          </button>
        </div>

        {/* File List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-3 text-gray-600">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Loading directory...</span>
              </div>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Directory</h3>
              <p className="text-sm text-gray-600 mb-4">{error}</p>
              <button
                onClick={() => loadDirectory(currentPath)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : files.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <Folder className="w-16 h-16 text-gray-300 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Empty Directory</h3>
              <p className="text-sm text-gray-600">
                No files have been recovered to this location yet.
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Recover some files to see them here!
              </p>
            </div>
          ) : (
            <div className="p-4">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-4 px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm font-medium text-gray-700 rounded-t-lg">
                <div className="col-span-1"></div>
                <div className="col-span-6">Name</div>
                <div className="col-span-2">Size</div>
                <div className="col-span-3">Date Modified</div>
              </div>

              {/* File Rows */}
              <div className="bg-white border border-gray-200 rounded-b-lg divide-y divide-gray-100">
                {files.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleItemClick(item)}
                    className={`grid grid-cols-12 gap-4 px-4 py-3 cursor-pointer transition-all duration-200 hover:bg-gray-50 ${
                      selectedItems.has(item.id) ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="col-span-1 flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedItems.has(item.id)}
                        onChange={(e) => {
                          e.stopPropagation();
                          handleItemSelect(item.id);
                        }}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="col-span-6 flex items-center gap-3">
                      {getFileIcon(item)}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate" title={item.name}>
                          {item.name}
                        </p>
                        {item.type === 'folder' && item.itemCount && (
                          <p className="text-xs text-gray-500">{item.itemCount} items</p>
                        )}
                      </div>
                    </div>
                    
                    <div className="col-span-2 flex items-center">
                      <span className="text-sm text-gray-700">
                        {item.type === 'folder' ? '--' : item.size}
                      </span>
                    </div>
                    
                    <div className="col-span-3 flex items-center">
                      <span className="text-sm text-gray-700">{item.dateModified}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Status Bar */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50 text-sm text-gray-600">
          <div className="flex items-center gap-4">
            <span>{files.length} items</span>
            {selectedItems.size > 0 && (
              <span>{selectedItems.size} selected</span>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={copyPath}
              className="flex items-center gap-1 hover:text-gray-800 transition-colors"
              title="Copy path"
            >
              <Copy className="w-3 h-3" />
              Copy path
            </button>
            
            {selectedItems.size > 0 && (
              <button
                onClick={() => setSelectedItems(new Set())}
                className="flex items-center gap-1 text-red-600 hover:text-red-700 transition-colors"
                title="Delete selected"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}