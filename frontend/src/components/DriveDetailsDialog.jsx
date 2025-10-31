import React, { useEffect, useState } from 'react';
import { X, HardDrive, Info, Database, Settings, Clock } from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {Object} props.drive
 */
export function DriveDetailsDialog({ isOpen, onClose, drive }) {
  const [detailsData, setDetailsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && drive) {
      fetchDetailsData();
    }
  }, [isOpen, drive]);

  const fetchDetailsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getDriveDetails(drive.id);
      if (response.status === 'success') {
        setDetailsData(response.data);
      } else {
        setError('Failed to load drive details');
      }
    } catch (err) {
      console.error('Error fetching drive details:', err);
      setError('Failed to load drive details');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const InfoRow = ({ label, value, highlight = false }) => (
    <div className="flex justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`text-sm font-medium ${highlight ? 'text-blue-600' : 'text-gray-900'}`}>
        {value}
      </span>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Info className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Drive Details</h2>
              <p className="text-sm text-gray-600">{drive?.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-sm text-gray-600">Loading drive details...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <X className="w-12 h-12 text-red-600 mb-4" />
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={fetchDetailsData}
                className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Retry
              </button>
            </div>
          ) : detailsData ? (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <HardDrive className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>
                </div>
                <div className="space-y-1">
                  <InfoRow label="Drive Name" value={detailsData.basic_info.name} highlight />
                  <InfoRow label="Device" value={detailsData.basic_info.device} />
                  <InfoRow label="Mount Point" value={detailsData.basic_info.mountpoint} />
                  <InfoRow label="File System" value={detailsData.basic_info.file_system} />
                  <InfoRow 
                    label="Status" 
                    value={detailsData.basic_info.status.charAt(0).toUpperCase() + detailsData.basic_info.status.slice(1)} 
                  />
                </div>
              </div>

              {/* Capacity Information */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Capacity</h3>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Total Capacity</p>
                    <p className="text-2xl font-bold text-gray-900">{detailsData.capacity.total}</p>
                    <p className="text-xs text-gray-500">{detailsData.capacity.total_bytes.toLocaleString()} bytes</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Used Space</p>
                    <p className="text-2xl font-bold text-blue-600">{detailsData.capacity.used}</p>
                    <p className="text-xs text-gray-500">{detailsData.capacity.percent_used}% used</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Free Space</p>
                    <p className="text-2xl font-bold text-green-600">{detailsData.capacity.free}</p>
                    <p className="text-xs text-gray-500">{detailsData.capacity.free_bytes.toLocaleString()} bytes</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Usage</p>
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full ${
                            detailsData.capacity.percent_used > 90 ? 'bg-red-600' :
                            detailsData.capacity.percent_used > 75 ? 'bg-orange-600' :
                            'bg-green-600'
                          }`}
                          style={{ width: `${detailsData.capacity.percent_used}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{detailsData.capacity.percent_used}%</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Partition Information */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Settings className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Partition Information</h3>
                </div>
                <div className="space-y-1">
                  <InfoRow label="Mount Options" value={detailsData.partition_info.mount_options} />
                  <InfoRow label="Max File Size" value={detailsData.partition_info.max_file_size} />
                  <InfoRow label="Max Volume Size" value={detailsData.partition_info.max_volume_size} />
                </div>
              </div>

              {/* System Information */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Info className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">System Information</h3>
                </div>
                <div className="space-y-1">
                  <InfoRow label="Platform" value={detailsData.system_info.platform} />
                  <InfoRow 
                    label="Accessible" 
                    value={detailsData.system_info.accessible ? "Yes" : "No"} 
                    highlight={detailsData.system_info.accessible}
                  />
                  <InfoRow 
                    label="Readable" 
                    value={detailsData.system_info.readable ? "Yes" : "No"} 
                    highlight={detailsData.system_info.readable}
                  />
                  <InfoRow 
                    label="Writable" 
                    value={detailsData.system_info.writable ? "Yes" : "No"} 
                    highlight={detailsData.system_info.writable}
                  />
                </div>
              </div>

              {/* Recovery Information */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Recovery Information</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Scannable</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      detailsData.recovery_info.scannable 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {detailsData.recovery_info.scannable ? "Yes" : "No"}
                    </span>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Recommended Scan Type</p>
                    <p className="text-sm font-semibold text-gray-900">{detailsData.recovery_info.recommended_scan_type}</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-xs text-gray-600 mb-1">Estimated Scan Time</p>
                    <p className="text-sm font-semibold text-gray-900">{detailsData.recovery_info.estimated_scan_time}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          {detailsData && (
            <button
              onClick={fetchDetailsData}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              Refresh
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
