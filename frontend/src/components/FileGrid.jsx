import React from 'react';
import { Star, StarHalf, HelpCircle, FileImage, FileText, Video, Music, Archive, File } from 'lucide-react';

/**
 * @param {Object} props
 * @param {import('../types/index.js').RecoveredFile[]} props.files
 * @param {(fileId: string) => void} props.onFileSelect
 * @param {(fileId: string) => void} props.onFileToggle
 * @param {string | null} props.selectedFileId
 * @param {'grid' | 'list'} props.viewMode
 */
export function FileGrid({ files, onFileSelect, onFileToggle, selectedFileId, viewMode }) {
  const getRecoveryIcon = (chance) => {
    switch (chance) {
      case 'High':
        return <Star className="w-4 h-4 text-green-600 fill-current" />;
      case 'Average':
        return <StarHalf className="w-4 h-4 text-yellow-600 fill-current" />;
      case 'Low':
        return <StarHalf className="w-4 h-4 text-orange-600" />;
      default:
        return <HelpCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getFileTypeIcon = (type) => {
    switch (type.toLowerCase()) {
      case 'raw':
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'heic':
        return <FileImage className="w-8 h-8 text-blue-500" />;
      case 'pdf':
      case 'doc':
      case 'docx':
      case 'txt':
        return <FileText className="w-8 h-8 text-red-500" />;
      case 'mp4':
      case 'avi':
      case 'mov':
        return <Video className="w-8 h-8 text-purple-500" />;
      case 'mp3':
      case 'wav':
      case 'flac':
        return <Music className="w-8 h-8 text-green-500" />;
      case 'zip':
      case 'rar':
      case '7z':
        return <Archive className="w-8 h-8 text-orange-500" />;
      default:
        return <File className="w-8 h-8 text-gray-500" />;
    }
  };

  if (viewMode === 'list') {
    return (
      <div className="bg-white">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-gray-50 border-b border-gray-200 text-sm font-medium text-gray-700">
          <div className="col-span-1"></div>
          <div className="col-span-5">Name</div>
          <div className="col-span-2">Size</div>
          <div className="col-span-2">Date Modified</div>
          <div className="col-span-2">Recovery</div>
        </div>

        {/* File Rows */}
        <div className="divide-y divide-gray-100">
          {files.map((file) => (
            <div
              key={file.id}
              onClick={() => onFileSelect(file.id)}
              className={`grid grid-cols-12 gap-4 px-6 py-3 cursor-pointer transition-all duration-200 hover:bg-gray-50 ${
                selectedFileId === file.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
              }`}
            >
              <div className="col-span-1 flex items-center">
                <input
                  type="checkbox"
                  checked={file.isSelected}
                  onChange={(e) => {
                    e.stopPropagation();
                    onFileToggle(file.id);
                  }}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </div>
              
              <div className="col-span-5 flex items-center gap-3">
                {file.thumbnail ? (
                  <img
                    src={file.thumbnail}
                    alt={file.name}
                    className="w-10 h-10 object-cover rounded border border-gray-200"
                  />
                ) : (
                  <div className="w-10 h-10 bg-gray-100 rounded border border-gray-200 flex items-center justify-center">
                    {getFileTypeIcon(file.type)}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate" title={file.name}>
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">{file.type} File</p>
                </div>
              </div>
              
              <div className="col-span-2 flex items-center">
                <span className="text-sm text-gray-700">{file.size}</span>
              </div>
              
              <div className="col-span-2 flex items-center">
                <span className="text-sm text-gray-700">{file.dateModified}</span>
              </div>
              
              <div className="col-span-2 flex items-center gap-2">
                {getRecoveryIcon(file.recoveryChance)}
                <span className="text-sm text-gray-700">{file.recoveryChance}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 p-6">
      {files.map((file) => (
        <div
          key={file.id}
          onClick={() => onFileSelect(file.id)}
          className={`group relative bg-white border-2 rounded-xl overflow-hidden cursor-pointer transition-all duration-200 hover:shadow-lg hover:-translate-y-1 ${
            selectedFileId === file.id ? 'border-blue-500 shadow-lg ring-2 ring-blue-200' : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          {/* Selection Checkbox */}
          <div className="absolute top-3 left-3 z-10">
            <input
              type="checkbox"
              checked={file.isSelected}
              onChange={(e) => {
                e.stopPropagation();
                onFileToggle(file.id);
              }}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 shadow-sm"
            />
          </div>

          {/* Recovery Chance */}
          <div className="absolute top-3 right-3 z-10 bg-white bg-opacity-90 rounded-full p-1">
            {getRecoveryIcon(file.recoveryChance)}
          </div>

          {/* Status Indicator */}
          {file.status !== 'found' && (
            <div className="absolute top-12 right-3 z-10">
              <div className={`w-3 h-3 rounded-full ${
                file.status === 'recovering' ? 'bg-blue-500 animate-pulse' :
                file.status === 'recovered' ? 'bg-green-500' :
                'bg-red-500'
              }`} />
            </div>
          )}

          {/* Thumbnail */}
          <div className="aspect-square bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center overflow-hidden">
            {file.thumbnail ? (
              <img
                src={file.thumbnail}
                alt={file.name}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                {getFileTypeIcon(file.type)}
              </div>
            )}
          </div>

          {/* File Info */}
          <div className="p-3 bg-white">
            <p className="text-xs text-gray-800 font-medium truncate mb-1" title={file.name}>
              {file.name}
            </p>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{file.size}</span>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                file.type === 'RAW' ? 'bg-blue-100 text-blue-700' :
                file.type === 'PNG' ? 'bg-green-100 text-green-700' :
                file.type === 'JPG' ? 'bg-purple-100 text-purple-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {file.type}
              </span>
            </div>
          </div>

          {/* Selection Overlay */}
          {file.isSelected && (
            <div className="absolute inset-0 bg-blue-600 bg-opacity-10 border-2 border-blue-600 rounded-xl pointer-events-none">
              <div className="absolute top-2 left-2 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full" />
              </div>
            </div>
          )}

          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-5 transition-all duration-200 pointer-events-none" />
        </div>
      ))}
    </div>
  );
}