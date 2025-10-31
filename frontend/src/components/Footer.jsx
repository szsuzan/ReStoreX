import React from 'react';
import { Download, Folder, Settings } from 'lucide-react';

/**
 * @param {Object} props
 * @param {number} props.selectedCount
 * @param {string} props.totalSize
 * @param {number} props.totalFiles
 * @param {() => void} props.onRecover
 * @param {() => void} props.onSelectOutputFolder
 */
export function Footer({ selectedCount, totalSize, totalFiles, onRecover, onSelectOutputFolder }) {
  return (
    <div className="bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-between shadow-lg">
      <div className="flex items-center gap-6">
        <div className="text-sm text-gray-600">
          <span className="font-semibold text-gray-800">{selectedCount}</span> files selected
          <span className="mx-2">•</span>
          <span className="font-semibold text-gray-800">{totalSize}</span>
          <span className="mx-2">•</span>
          <span>{totalFiles.toLocaleString()} total files</span>
        </div>
        
        <button
          onClick={onSelectOutputFolder}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          <Folder className="w-4 h-4" />
          Output: C:\\RecoveredFiles
        </button>
      </div>
      
      <div className="flex items-center gap-3">
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Recovery Settings">
          <Settings className="w-4 h-4 text-gray-600" />
        </button>
        
        <button
          onClick={() => {
            console.log('Recover button clicked! Selected count:', selectedCount);
            onRecover();
          }}
          disabled={selectedCount === 0}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-all duration-200 ${
            selectedCount > 0
              ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg hover:-translate-y-0.5'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          <Download className="w-4 h-4" />
          Recover {selectedCount > 0 ? `${selectedCount} Files` : 'Files'}
        </button>
      </div>
    </div>
  );
}