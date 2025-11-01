import React, { useState, useEffect } from 'react';
import { X, HardDrive, AlertTriangle, CheckCircle, Clock, RefreshCw, Image, FileText, Video, Music, Package, Database } from 'lucide-react';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {(driveId: string, scanType: 'quick' | 'deep', options?: Object) => void} props.onStartScan
 * @param {import('../types/index.js').DriveInfo[]} props.drives
 * @param {string} props.initialScanType
 */
export function DriveSelectionDialog({ isOpen, onClose, onStartScan, drives, initialScanType = 'normal' }) {
  const [selectedDrive, setSelectedDrive] = useState('');
  const [scanType, setScanType] = useState(initialScanType);
  const [selectedFileTypes, setSelectedFileTypes] = useState({
    images: true,
    documents: true,
    videos: true,
    audio: true,
    archives: true,
    email: true
  });

  // Update scan type when dialog opens with new initialScanType
  useEffect(() => {
    if (isOpen) {
      setScanType(initialScanType);
      // Reset file type selection when opening with carving scan
      if (initialScanType === 'carving') {
        setSelectedFileTypes({
          images: true,
          documents: true,
          videos: true,
          audio: true,
          archives: true,
          email: true
        });
      }
      console.log('Drive selection dialog opened with scan type:', initialScanType);
    }
  }, [isOpen, initialScanType]);

  const toggleFileType = (type) => {
    setSelectedFileTypes(prev => ({
      ...prev,
      [type]: !prev[type]
    }));
  };

  const selectAllFileTypes = () => {
    setSelectedFileTypes({
      images: true,
      documents: true,
      videos: true,
      audio: true,
      archives: true,
      email: true
    });
  };

  const deselectAllFileTypes = () => {
    setSelectedFileTypes({
      images: false,
      documents: false,
      videos: false,
      audio: false,
      archives: false,
      email: false
    });
  };

  const hasAnyFileTypeSelected = Object.values(selectedFileTypes).some(v => v);

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
      // Pass file type options for carving scan
      const options = scanType === 'carving' ? { fileTypes: selectedFileTypes } : {};
      onStartScan(selectedDrive, scanType, options);
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

        {/* Scan Type Selection - Only show for normal/deep scans, NOT for carving */}
        {!['cluster', 'health', 'signature', 'forensic', 'carving'].includes(scanType) && (
          <>
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
          </>
        )}

        {/* File Type Selection - Only show for carving scan */}
        {scanType === 'carving' && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-gray-800">File Types to Recover</h4>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectAllFileTypes}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  Select All
                </button>
                <span className="text-gray-400">|</span>
                <button
                  type="button"
                  onClick={deselectAllFileTypes}
                  className="text-xs text-gray-600 hover:text-gray-700 font-medium"
                >
                  Deselect All
                </button>
              </div>
            </div>
            
            {/* Important Note */}
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-800">
                  <p className="font-semibold mb-1">Note: Recovered size may exceed drive capacity</p>
                  <p>File carving recovers old deleted files, multiple versions, and file fragments. Manually select only the files you need after scanning.</p>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.images ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.images}
                  onChange={() => toggleFileType('images')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <Image className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Images</div>
                  <div className="text-xs text-gray-600">JPG, PNG</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.documents ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.documents}
                  onChange={() => toggleFileType('documents')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <FileText className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Documents</div>
                  <div className="text-xs text-gray-600">PDF, DOCX, XLSX, PPTX, TXT</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.videos ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.videos}
                  onChange={() => toggleFileType('videos')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <Video className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Videos</div>
                  <div className="text-xs text-gray-600">MP4, AVI, MOV</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.audio ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.audio}
                  onChange={() => toggleFileType('audio')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <Music className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Audio</div>
                  <div className="text-xs text-gray-600">MP3, WAV</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.archives ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.archives}
                  onChange={() => toggleFileType('archives')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <Package className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Archives</div>
                  <div className="text-xs text-gray-600">ZIP, RAR</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                selectedFileTypes.email ? 'border-cyan-500 bg-cyan-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="checkbox"
                  checked={selectedFileTypes.email}
                  onChange={() => toggleFileType('email')}
                  className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                />
                <Database className="w-5 h-5 text-cyan-600" />
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-900">Databases</div>
                  <div className="text-xs text-gray-600">SQLite, CSV</div>
                </div>
              </label>
            </div>
            
            {!hasAnyFileTypeSelected && (
              <div className="mt-3 text-xs text-orange-600 bg-orange-50 p-2 rounded-lg">
                ⚠️ Please select at least one file type to scan
              </div>
            )}
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
            disabled={!selectedDrive || (scanType === 'carving' && !hasAnyFileTypeSelected)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg transition-colors font-medium ${
              selectedDrive && (scanType !== 'carving' || hasAnyFileTypeSelected)
                ? 'text-white bg-blue-600 hover:bg-blue-700 shadow-sm'
                : 'text-gray-400 bg-gray-200 cursor-not-allowed'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            Start {scanType === 'cluster' ? 'Cluster' :
                   scanType === 'health' ? 'Health' :
                   scanType === 'signature' ? 'Signature' :
                   scanType === 'forensic' ? 'Forensic' :
                   scanType === 'carving' ? 'File Carving' :
                   scanType.charAt(0).toUpperCase() + scanType.slice(1)} Scan
          </button>
        </div>
      </div>
    </div>
  );
}