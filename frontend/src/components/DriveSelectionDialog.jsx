import React, { useState, useEffect } from 'react';
import { X, HardDrive, AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {(driveId: string, scanType: 'quick' | 'deep') => void} props.onStartScan
 * @param {import('../types/index.js').DriveInfo[]} props.drives
 * @param {string} props.initialScanType
 */
export function DriveSelectionDialog({ isOpen, onClose, onStartScan, drives, initialScanType = 'normal' }) {
  const [selectedDrive, setSelectedDrive] = useState('');
  const [scanType, setScanType] = useState(initialScanType);

  // Update scan type when dialog opens with new initialScanType
  useEffect(() => {
    if (isOpen) {
      setScanType(initialScanType);
      console.log('Drive selection dialog opened with scan type:', initialScanType);
    }
  }, [isOpen, initialScanType]);

  if (!isOpen) return null;

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'damaged':
        return <AlertTriangle className="w-5 h-5 text-orange-600" />;
      case 'scanning':
        return <Clock className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-red-600" />;
      default:
        return <HardDrive className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'border-green-200 bg-green-50';
      case 'damaged':
        return 'border-orange-200 bg-orange-50';
      case 'scanning':
        return 'border-blue-200 bg-blue-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const handleStartScan = () => {
    if (selectedDrive) {
      onStartScan(selectedDrive, scanType);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl p-8 w-[500px] max-w-[90vw]">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-gray-900">Select Drive to Scan</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Drive Selection */}
        <div className="space-y-3 mb-6">
          {drives.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <HardDrive className="w-8 h-8 text-gray-400" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">No Drives Found</h4>
              <p className="text-sm text-gray-600 mb-4 max-w-sm">
                No storage drives were detected. Please make sure your drives are properly connected
                and the backend server is running.
              </p>
            </div>
          ) : (
            drives.map(drive => (
              <label
                key={drive.id}
                className={`flex items-center gap-4 p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-md ${
                  selectedDrive === drive.id ? 'border-blue-500 bg-blue-50' : `${getStatusColor(drive.status)} hover:border-gray-300`
                }`}
              >
                <input
                  type="radio"
                  name="drive"
                  value={drive.id}
                  checked={selectedDrive === drive.id}
                  onChange={(e) => setSelectedDrive(e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                
                <div className="flex items-center gap-3 flex-1">
                  {getStatusIcon(drive.status)}
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900">{drive.name}</div>
                    <div className="text-sm text-gray-600">
                      {drive.size} • {drive.fileSystem} • {drive.status}
                    </div>
                  </div>
                </div>
              </label>
            ))
          )}
        </div>

        {/* Scan Type Selection - Only show for normal/deep scans */}
        {!['cluster', 'health', 'signature', 'forensic'].includes(scanType) && (
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-800 mb-3">Scan Type</h4>
            <div className="space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="scanType"
                  value="normal"
                  checked={scanType === 'normal'}
                  onChange={(e) => setScanType(e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500 mt-0.5"
                />
                <div>
                  <div className="font-medium text-gray-900">Normal Scan</div>
                  <div className="text-sm text-gray-600">
                    Fast scan for recently deleted files (5-15 minutes)
                  </div>
                </div>
              </label>
              
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="scanType"
                  value="deep"
                  checked={scanType === 'deep'}
                  onChange={(e) => setScanType(e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500 mt-0.5"
                />
                <div>
                  <div className="font-medium text-gray-900">Deep Scan</div>
                  <div className="text-sm text-gray-600">
                    Comprehensive scan for all recoverable files (30+ minutes)
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleStartScan}
            disabled={!selectedDrive}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg transition-colors font-medium ${
              selectedDrive
                ? 'text-white bg-blue-600 hover:bg-blue-700 shadow-sm'
                : 'text-gray-400 bg-gray-200 cursor-not-allowed'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            Start {scanType === 'cluster' ? 'Cluster' :
                   scanType === 'health' ? 'Health' :
                   scanType === 'signature' ? 'Signature' :
                   scanType === 'forensic' ? 'Forensic' :
                   scanType.charAt(0).toUpperCase() + scanType.slice(1)} Scan
          </button>
        </div>
      </div>
    </div>
  );
}