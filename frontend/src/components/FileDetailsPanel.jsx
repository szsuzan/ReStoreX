import React from 'react';
import { Star, StarHalf, HelpCircle, X, Copy, Download, Eye, Info, HardDrive, Calendar, Ruler } from 'lucide-react';
import { HexViewer } from './HexViewer';

/**
 * @param {Object} props
 * @param {import('../types/index.js').RecoveredFile | null} props.file
 * @param {() => void} props.onClose
 * @param {(fileId: string) => void} props.onRecover
 */
export function FileDetailsPanel({ file, onClose, onRecover }) {
  const [activeTab, setActiveTab] = React.useState('details');

  if (!file) return null;

  const getRecoveryIcon = (chance) => {
    switch (chance) {
      case 'High':
        return <Star className="w-5 h-5 text-green-600 fill-current" />;
      case 'Average':
        return <StarHalf className="w-5 h-5 text-yellow-600 fill-current" />;
      case 'Low':
        return <StarHalf className="w-5 h-5 text-orange-600" />;
      default:
        return <HelpCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getRecoveryColor = (chance) => {
    switch (chance) {
      case 'High':
        return 'text-green-600 bg-green-50';
      case 'Average':
        return 'text-yellow-600 bg-yellow-50';
      case 'Low':
        return 'text-orange-600 bg-orange-50';
      default:
        return 'text-gray-500 bg-gray-50';
    }
  };

  const getRecoveryDescription = (chance) => {
    switch (chance) {
      case 'High':
        return 'This file has excellent chances of being recovered completely without corruption.';
      case 'Average':
        return 'This file has good chances of being recovered with minimal or no corruption.';
      case 'Low':
        return 'This file may be partially corrupted but recovery is still possible.';
      default:
        return 'Recovery chances could not be determined. Manual inspection may be required.';
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="w-96 bg-white border-l border-gray-200 flex flex-col shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-gray-800">File Analysis</h3>
          <div className="flex bg-white rounded-lg p-1 border border-gray-200">
            <button
              onClick={() => setActiveTab('details')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                activeTab === 'details' 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Details
            </button>
            <button
              onClick={() => setActiveTab('hex')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                activeTab === 'hex' 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Hex View
            </button>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'hex' ? (
        <HexViewer 
          fileId={file.id}
          fileName={file.name}
          fileType={file.type}
        />
      ) : (
        <>
      {/* File Preview */}
      <div className="p-6 border-b border-gray-200">
        <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 rounded-xl overflow-hidden mb-4 shadow-inner">
          {file.thumbnail ? (
            <img
              src={file.thumbnail}
              alt={file.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <span className="text-4xl font-bold text-gray-400">{file.type}</span>
            </div>
          )}
        </div>

        <h4 className="text-base font-semibold text-gray-800 mb-2 break-words leading-tight">
          {file.name}
        </h4>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="space-y-3">
            <div>
              <span className="text-gray-500 block text-xs uppercase tracking-wide mb-1">Type</span>
              <span className="text-gray-800 font-medium">{file.type} File</span>
            </div>
            <div>
              <span className="text-gray-500 block text-xs uppercase tracking-wide mb-1">Size</span>
              <span className="text-gray-800 font-medium">{file.size}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-gray-500 block text-xs uppercase tracking-wide mb-1">Modified</span>
              <span className="text-gray-800 font-medium">{file.dateModified}</span>
            </div>
            <div>
              <span className="text-gray-500 block text-xs uppercase tracking-wide mb-1">Status</span>
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                file.status === 'found' ? 'bg-blue-100 text-blue-800' :
                file.status === 'recovering' ? 'bg-yellow-100 text-yellow-800' :
                file.status === 'recovered' ? 'bg-green-100 text-green-800' :
                'bg-red-100 text-red-800'
              }`}>
                {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Technical Details */}
      <div className="p-6 border-b border-gray-200 bg-gray-50">
        <h5 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Info className="w-4 h-4" />
          Technical Information
        </h5>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 flex items-center gap-2">
              <HardDrive className="w-4 h-4" />
              Sector
            </span>
            <span className="text-gray-800 font-mono">{file.sector?.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600 flex items-center gap-2">
              <Ruler className="w-4 h-4" />
              Cluster
            </span>
            <span className="text-gray-800 font-mono">{file.cluster?.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Inode
            </span>
            <span className="text-gray-800 font-mono">{file.inode?.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Path */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h5 className="text-sm font-semibold text-gray-800">File Path</h5>
          <button
            onClick={() => copyToClipboard(file.path)}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            title="Copy path"
          >
            <Copy className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        <p className="text-xs text-gray-600 break-all bg-gray-50 p-3 rounded-lg font-mono border">
          {file.path}
        </p>
      </div>

      {/* Recovery Chances */}
      <div className="p-6 border-b border-gray-200">
        <h5 className="text-sm font-semibold text-gray-800 mb-4">Recovery Assessment</h5>
        <div className={`flex items-center gap-3 p-4 rounded-lg ${getRecoveryColor(file.recoveryChance)}`}>
          {getRecoveryIcon(file.recoveryChance)}
          <div>
            <span className="text-sm font-semibold">{file.recoveryChance} Chance</span>
            <p className="text-xs mt-1 opacity-80">
              {getRecoveryDescription(file.recoveryChance)}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-6 mt-auto space-y-3">
        <button
          onClick={() => onRecover(file.id)}
          disabled={file.status === 'recovering' || file.status === 'recovered'}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
            file.status === 'recovering' ? 
              'bg-yellow-100 text-yellow-700 cursor-not-allowed' :
            file.status === 'recovered' ?
              'bg-green-100 text-green-700 cursor-not-allowed' :
              'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md'
          }`}
        >
          <Download className="w-4 h-4" />
          {file.status === 'recovering' ? 'Recovering...' :
           file.status === 'recovered' ? 'Recovered' :
           'Recover File'}
        </button>
        
        <button 
          disabled={!file.thumbnail}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
            file.thumbnail 
              ? 'bg-gray-100 hover:bg-gray-200 text-gray-700' 
              : 'bg-gray-50 text-gray-400 cursor-not-allowed'
          }`}
        >
          <Eye className="w-4 h-4" />
          {file.thumbnail ? 'Preview' : 'Preview Not Available'}
        </button>
      </div>
        </>
      )}
    </div>
  );
}