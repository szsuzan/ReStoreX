import React from 'react';
import { X, HardDrive, Clock, FileSearch } from 'lucide-react';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {() => void} props.onCancel
 * @param {import('../types/index.js').ScanProgress} props.progress
 */
export function ScanProgressDialog({ isOpen, onClose, onCancel, progress }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl p-8 w-96 max-w-[90vw]">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-gray-900">Scanning Drive</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Progress Circle */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative w-32 h-32 mb-4">
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="45"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                className="text-gray-200"
              />
              <circle
                cx="50"
                cy="50"
                r="45"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 45}`}
                strokeDashoffset={`${2 * Math.PI * 45 * (1 - progress.progress / 100)}`}
                className="text-blue-600 transition-all duration-500 ease-in-out"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 transition-all duration-300">{Number(progress.progress).toFixed(1)}%</div>
                <div className="text-xs text-gray-500">Complete</div>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Details */}
        <div className="space-y-4 mb-6">
          {progress.currentPass > 0 && (
            <div className="flex items-center gap-3 text-sm bg-blue-50 p-3 rounded-lg transition-opacity duration-300">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              <span className="text-blue-700 font-medium">Pass {progress.currentPass}</span>
              <span className="text-blue-600 text-xs ml-auto">{progress.expectedTime || 'Calculating...'}</span>
            </div>
          )}
          
          <div className="flex items-center gap-3 text-sm">
            <HardDrive className="w-4 h-4 text-blue-600" />
            <span className="text-gray-600">Sectors scanned:</span>
            <span className="font-mono text-gray-800 ml-auto">
              {progress.currentSector.toLocaleString()} / {progress.totalSectors.toLocaleString()}
            </span>
          </div>
          
          <div className="flex items-center gap-3 text-sm">
            <FileSearch className="w-4 h-4 text-green-600" />
            <span className="text-gray-600">Files found:</span>
            <span className="font-semibold text-gray-800 ml-auto">{progress.filesFound.toLocaleString()}</span>
          </div>
          
          <div className="flex items-center gap-3 text-sm">
            <Clock className="w-4 h-4 text-orange-600" />
            <span className="text-gray-600">Expected time:</span>
            <span className="font-medium text-gray-800 ml-auto">{progress.expectedTime || progress.estimatedTimeRemaining || 'Calculating...'}</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs text-gray-600 mb-2">
            <span>Scanning sectors...</span>
            <span>{Number(progress.progress).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.min(progress.progress, 100)}%` }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
          >
            Cancel Scan
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
          >
            Run in Background
          </button>
        </div>
      </div>
    </div>
  );
}