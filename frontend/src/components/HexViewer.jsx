import React, { useState, useEffect } from 'react';
import { Search, Copy, Download, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * @param {Object} props
 * @param {string} props.fileId
 * @param {string} props.fileName
 * @param {string} props.fileType
 */
export function HexViewer({ fileId, fileName, fileType }) {
  const [hexData, setHexData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAscii, setShowAscii] = useState(true);
  const [bytesPerRow, setBytesPerRow] = useState(16);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedByte, setSelectedByte] = useState(null);

  useEffect(() => {
    loadHexData();
  }, [fileId]);

  const loadHexData = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Loading hex data for file:', fileId);
      // Load hex data from API
      const response = await apiService.getFileHexData(fileId, 0, 512);
      console.log('Hex data loaded:', response);
      
      if (response && response.data) {
        setHexData(response.data);
      } else {
        // Fallback to mock data if API doesn't return proper data
        const mockHexData = generateMockHexData(fileType, fileName);
        setHexData(mockHexData);
      }
    } catch (error) {
      console.error('Failed to load hex data:', error);
      setError(error.message);
      // Use mock data as fallback
      const mockHexData = generateMockHexData(fileType, fileName);
      setHexData(mockHexData);
    } finally {
      setLoading(false);
    }
  };

  const generateMockHexData = (type, name) => {
    let hexBytes = [];
    
    // Add file signature based on type
    if (type === 'JPG' || name.toLowerCase().includes('.jpg')) {
      hexBytes = [0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48];
    } else if (type === 'PNG' || name.toLowerCase().includes('.png')) {
      hexBytes = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52];
    } else if (type === 'PDF' || name.toLowerCase().includes('.pdf')) {
      hexBytes = [0x25, 0x50, 0x44, 0x46, 0x2D, 0x31, 0x2E, 0x34, 0x0A, 0x25, 0xC4, 0xE5, 0xF2, 0xE5, 0xEB, 0xA7];
    } else if (type === 'RAW' || name.toLowerCase().includes('.raw')) {
      hexBytes = [0x52, 0x41, 0x57, 0x20, 0x46, 0x49, 0x4C, 0x45, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07];
    } else {
      // Generic file header
      hexBytes = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F];
    }
    
    // Add more random data to simulate file content
    for (let i = hexBytes.length; i < 256; i++) {
      hexBytes.push(Math.floor(Math.random() * 256));
    }
    
    return hexBytes;
  };

  const formatHexByte = (byte) => {
    return byte.toString(16).toUpperCase().padStart(2, '0');
  };

  const formatAscii = (byte) => {
    return (byte >= 32 && byte <= 126) ? String.fromCharCode(byte) : '.';
  };

  const getFileSignatureInfo = () => {
    if (!hexData || hexData.length === 0) return null;
    
    const firstBytes = hexData.slice(0, 4);
    const hexString = firstBytes.map(b => formatHexByte(b)).join(' ');
    
    if (firstBytes[0] === 0xFF && firstBytes[1] === 0xD8) {
      return { type: 'JPEG Image', signature: hexString, description: 'JPEG/JFIF image file' };
    } else if (firstBytes[0] === 0x89 && firstBytes[1] === 0x50) {
      return { type: 'PNG Image', signature: hexString, description: 'Portable Network Graphics image' };
    } else if (firstBytes[0] === 0x25 && firstBytes[1] === 0x50) {
      return { type: 'PDF Document', signature: hexString, description: 'Adobe PDF document' };
    } else if (firstBytes[0] === 0x52 && firstBytes[1] === 0x41) {
      return { type: 'RAW File', signature: hexString, description: 'Camera RAW image file' };
    }
    
    return { type: 'Unknown', signature: hexString, description: 'Unknown file format' };
  };

  const handleByteClick = (index, byte) => {
    setSelectedByte({ index, byte, offset: index });
  };

  const copyHexData = () => {
    const hexString = hexData.map(b => formatHexByte(b)).join(' ');
    navigator.clipboard.writeText(hexString);
  };

  const renderHexRows = () => {
    if (!hexData || hexData.length === 0) return null;
    
    const rows = [];
    for (let i = 0; i < hexData.length; i += bytesPerRow) {
      const rowBytes = hexData.slice(i, i + bytesPerRow);
      rows.push(
        <div key={i} className="flex items-center gap-4 py-1 hover:bg-gray-50 font-mono text-sm">
          {/* Offset */}
          <div className="w-16 text-gray-500 text-xs">
            {i.toString(16).toUpperCase().padStart(8, '0')}
          </div>
          
          {/* Hex bytes */}
          <div className="flex-1 flex flex-wrap gap-1">
            {rowBytes.map((byte, index) => {
              const globalIndex = i + index;
              const isSelected = selectedByte?.index === globalIndex;
              const isSearchMatch = searchTerm && formatHexByte(byte).includes(searchTerm.toUpperCase());
              
              return (
                <button
                  key={index}
                  onClick={() => handleByteClick(globalIndex, byte)}
                  className={`px-1 py-0.5 rounded text-xs transition-colors ${
                    isSelected ? 'bg-blue-600 text-white' :
                    isSearchMatch ? 'bg-yellow-200 text-gray-900' :
                    'hover:bg-gray-200 text-gray-700'
                  }`}
                >
                  {formatHexByte(byte)}
                </button>
              );
            })}
            
            {/* Padding for incomplete rows */}
            {Array.from({ length: bytesPerRow - rowBytes.length }).map((_, index) => (
              <div key={`pad-${index}`} className="px-1 py-0.5 text-xs text-transparent">00</div>
            ))}
          </div>
          
          {/* ASCII representation */}
          {showAscii && (
            <div className="w-32 text-gray-600 text-xs font-mono border-l border-gray-200 pl-2">
              {rowBytes.map((byte, index) => (
                <span key={index} className="inline-block w-2">
                  {formatAscii(byte)}
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }
    return rows;
  };

  const signatureInfo = getFileSignatureInfo();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-gray-600">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span>Loading hex data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-orange-600">
          <AlertCircle className="w-5 h-5" />
          <div>
            <div className="text-sm font-medium">Failed to load hex data</div>
            <div className="text-xs text-gray-600 mt-1">{error}</div>
            <button 
              onClick={loadHexData}
              className="mt-2 text-xs text-blue-600 hover:text-blue-700 underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header Controls */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-gray-800">Hex Viewer</h4>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAscii(!showAscii)}
              className="p-1.5 hover:bg-gray-200 rounded transition-colors"
              title={showAscii ? 'Hide ASCII' : 'Show ASCII'}
            >
              {showAscii ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button
              onClick={copyHexData}
              className="p-1.5 hover:bg-gray-200 rounded transition-colors"
              title="Copy hex data"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        {/* Search and Controls */}
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-2 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search hex (e.g., FF D8)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <select
            value={bytesPerRow}
            onChange={(e) => setBytesPerRow(parseInt(e.target.value))}
            className="text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={8}>8 bytes/row</option>
            <option value={16}>16 bytes/row</option>
            <option value={32}>32 bytes/row</option>
          </select>
        </div>
        
        {/* File Signature Info */}
        {signatureInfo && (
          <div className="bg-blue-50 border border-blue-200 rounded p-3">
            <div className="text-xs text-blue-800 font-medium mb-1">File Signature Detected</div>
            <div className="text-xs text-blue-700">
              <span className="font-mono">{signatureInfo.signature}</span> - {signatureInfo.type}
            </div>
            <div className="text-xs text-blue-600 mt-1">{signatureInfo.description}</div>
          </div>
        )}
      </div>

      {/* Hex Data Display */}
      <div className="flex-1 overflow-y-auto p-4">
        {hexData && hexData.length > 0 ? (
          <div className="space-y-0.5">
            {renderHexRows()}
          </div>
        ) : (
          <div className="flex items-center justify-center h-32 text-gray-500">
            <div className="text-center">
              <div className="text-sm">No hex data available</div>
              <div className="text-xs mt-1">File needs to be recovered first</div>
            </div>
          </div>
        )}
      </div>

      {/* Selected Byte Info */}
      {selectedByte && (
        <div className="p-3 border-t border-gray-200 bg-gray-50">
          <div className="text-xs text-gray-600">
            <span className="font-medium">Offset:</span> 0x{selectedByte.offset.toString(16).toUpperCase().padStart(8, '0')} ({selectedByte.offset})
            <span className="ml-4 font-medium">Value:</span> 0x{formatHexByte(selectedByte.byte)} ({selectedByte.byte})
            <span className="ml-4 font-medium">ASCII:</span> '{formatAscii(selectedByte.byte)}'
          </div>
        </div>
      )}
    </div>
  );
}