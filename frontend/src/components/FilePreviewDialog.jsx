import React, { useState, useEffect } from 'react';
import { X, Download, FileImage, FileText, Film, Music, Archive, AlertCircle, Loader2 } from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {string} props.fileId
 * @param {string} props.fileName
 * @param {string} props.fileType
 */
export function FilePreviewDialog({ isOpen, onClose, fileId, fileName, fileType }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && fileId) {
      loadPreview();
    }
  }, [isOpen, fileId]);

  const loadPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getFilePreview(fileId);
      setPreview(data);
    } catch (err) {
      console.error('Failed to load preview:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getFileIcon = () => {
    const type = fileType?.toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'raw'].includes(type)) {
      return <FileImage className="w-12 h-12 text-blue-500" />;
    } else if (['txt', 'log', 'csv', 'json', 'xml'].includes(type)) {
      return <FileText className="w-12 h-12 text-gray-500" />;
    } else if (['mp4', 'avi', 'mov'].includes(type)) {
      return <Film className="w-12 h-12 text-purple-500" />;
    } else if (['mp3', 'wav', 'flac'].includes(type)) {
      return <Music className="w-12 h-12 text-green-500" />;
    }
    return <Archive className="w-12 h-12 text-orange-500" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            {getFileIcon()}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{fileName}</h3>
              <p className="text-sm text-gray-600">{fileType} File Preview</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px]">
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
              <p className="text-gray-600">Loading preview...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px]">
              <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
              <p className="text-red-600 font-medium mb-2">Failed to load preview</p>
              <p className="text-gray-600 text-sm">{error}</p>
              <button
                onClick={loadPreview}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : preview ? (
            <>
              {/* Image Preview */}
              {preview.previewType === 'image' && preview.preview && (
                <div className="flex items-center justify-center bg-gray-50 rounded-lg p-4">
                  <img
                    src={preview.preview}
                    alt={fileName}
                    className="max-w-full max-h-[600px] object-contain rounded-lg shadow-lg"
                  />
                </div>
              )}

              {/* Text Preview */}
              {preview.previewType === 'text' && (
                <div className="bg-gray-900 text-gray-100 rounded-lg p-6 font-mono text-sm overflow-auto max-h-[600px]">
                  <pre className="whitespace-pre-wrap">{preview.preview}</pre>
                </div>
              )}

              {/* Not Previewable */}
              {!preview.canPreview && (
                <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                  {getFileIcon()}
                  <h4 className="text-lg font-semibold text-gray-900 mt-4 mb-2">
                    Preview Not Available
                  </h4>
                  <p className="text-gray-600 max-w-md mb-4">
                    {preview.message || 'This file type cannot be previewed. Please recover the file to view its contents.'}
                  </p>
                  {preview.fileSize && (
                    <p className="text-sm text-gray-500">
                      File size: {(preview.fileSize / 1024).toFixed(2)} KB
                    </p>
                  )}
                </div>
              )}

              {/* PDF Info */}
              {preview.previewType === 'pdf' && (
                <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                  <FileText className="w-16 h-16 text-red-500 mb-4" />
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">PDF Document</h4>
                  <p className="text-gray-600 max-w-md mb-4">
                    {preview.message}
                  </p>
                  {preview.fileSize && (
                    <p className="text-sm text-gray-500">
                      File size: {(preview.fileSize / 1024).toFixed(2)} KB
                    </p>
                  )}
                </div>
              )}

              {/* Media Info */}
              {preview.previewType === 'media' && (
                <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                  {getFileIcon()}
                  <h4 className="text-lg font-semibold text-gray-900 mt-4 mb-2">
                    Media File
                  </h4>
                  <p className="text-gray-600 max-w-md mb-4">
                    {preview.message}
                  </p>
                  {preview.fileSize && (
                    <p className="text-sm text-gray-500">
                      File size: {(preview.fileSize / 1024 / 1024).toFixed(2)} MB
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full min-h-[400px]">
              <p className="text-gray-500">No preview available</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            {preview?.fileSize && (
              <span>Size: {(preview.fileSize / 1024).toFixed(2)} KB</span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
