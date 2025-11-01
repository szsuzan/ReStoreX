import React, { useState, useEffect } from 'react';
import { X, HardDrive, Activity, AlertCircle, CheckCircle, XCircle, Download } from 'lucide-react';

/**
 * Dialog to display Cluster Map or Health Report
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {string} props.scanId
 * @param {string} props.scanType - 'cluster' or 'health'
 * @param {boolean} props.embedded - If true, render without dialog wrapper
 */
export function ScanReportDialog({ isOpen, onClose, scanId, scanType, embedded = false }) {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Helper function to extract value from SMART attribute (handles both old dict format and new string format)
  const getSmartValue = (value) => {
    if (!value) return null;
    
    // If it's a string that looks like JSON, try to parse it
    if (typeof value === 'string' && value.startsWith('{')) {
      try {
        const parsed = JSON.parse(value);
        if (parsed.value !== undefined) {
          return parsed.value;
        }
        return value;
      } catch (e) {
        // Not valid JSON, return as-is
        return value;
      }
    }
    
    // If it's an object with 'value' property (old format), extract it
    if (typeof value === 'object' && value.value !== undefined) {
      return value.value;
    }
    
    // Otherwise return as-is (new string format)
    return value;
  };

  useEffect(() => {
    if ((isOpen || embedded) && scanId) {
      loadReport();
    }
  }, [isOpen, embedded, scanId]);

  const loadReport = () => {
    setLoading(true);
    // Try to load from localStorage first
    const cached = localStorage.getItem(`scan_report_${scanId}`);
    if (cached) {
      try {
        const data = JSON.parse(cached);
        setReportData(data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to parse cached report:', error);
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  };

  if (!isOpen && !embedded) return null;

  const renderClusterReport = () => {
    if (!reportData || !reportData.data) return <p className="text-gray-500">No cluster data available</p>;

    const { statistics, cluster_map } = reportData.data;

    return (
      <div className="space-y-6">
        {/* Statistics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-blue-600 font-medium">Total Clusters</div>
            <div className="text-2xl font-bold text-blue-900">{statistics?.total_clusters?.toLocaleString() || 'N/A'}</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-sm text-green-600 font-medium">Sampled</div>
            <div className="text-2xl font-bold text-green-900">{statistics?.sampled_clusters?.toLocaleString() || 'N/A'}</div>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 font-medium">Empty Clusters</div>
            <div className="text-2xl font-bold text-gray-900">{statistics?.empty_clusters?.toLocaleString() || 'N/A'}</div>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-sm text-purple-600 font-medium">Used Clusters</div>
            <div className="text-2xl font-bold text-purple-900">{statistics?.used_clusters?.toLocaleString() || 'N/A'}</div>
          </div>
        </div>

        {/* Cluster Map Preview */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">Cluster Map (First 10 samples)</h4>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {cluster_map && cluster_map.slice(0, 10).map((cluster, idx) => (
              <div key={idx} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-sm font-medium">Cluster #{cluster.cluster_id}</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${cluster.is_empty ? 'bg-gray-200 text-gray-700' : 'bg-blue-100 text-blue-700'}`}>
                    {cluster.is_empty ? 'Empty' : 'Used'}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mb-2">Offset: 0x{cluster.offset?.toString(16).toUpperCase() || '0'}</div>
                
                {/* Hex Preview */}
                <div className="bg-gray-900 text-green-400 p-3 rounded font-mono text-xs overflow-x-auto mb-2">
                  <div className="whitespace-pre">{cluster.hex_preview?.match(/.{1,32}/g)?.slice(0, 4).join('\n') || 'No data'}</div>
                </div>
                
                {/* ASCII Preview */}
                <div className="bg-gray-100 p-3 rounded font-mono text-xs overflow-x-auto">
                  <div className="whitespace-pre text-gray-700">{cluster.ascii_preview?.substring(0, 128) || 'No ASCII data'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderHealthReport = () => {
    if (!reportData || !reportData.data) return <p className="text-gray-500">No health data available</p>;

    const { health_score, status, drive_path, smart_data, surface_map, recommendations, bad_sectors, total_sectors_tested } = reportData.data;

    const getStatusColor = () => {
      if (health_score >= 90) return 'bg-green-500';
      if (health_score >= 70) return 'bg-blue-500';
      if (health_score >= 50) return 'bg-yellow-500';
      return 'bg-red-500';
    };

    const getStatusIcon = () => {
      if (health_score >= 70) return <CheckCircle className="w-12 h-12 text-green-500" />;
      if (health_score >= 50) return <AlertCircle className="w-12 h-12 text-yellow-500" />;
      return <XCircle className="w-12 h-12 text-red-500" />;
    };

    return (
      <div className="space-y-6">
        {/* Health Score */}
        <div className="flex items-center justify-center mb-6">
          <div className="text-center">
            <div className="mb-4">{getStatusIcon()}</div>
            <div className="text-4xl font-bold text-gray-900 mb-2">{health_score}/100</div>
            <div className={`inline-block px-4 py-2 rounded-full text-white font-medium ${getStatusColor()}`}>
              {status || 'Unknown'}
            </div>
          </div>
        </div>

        {/* Drive Info */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <HardDrive className="w-5 h-5 text-gray-600" />
            <span className="font-medium text-gray-900">Drive: {drive_path}</span>
          </div>
        </div>

        {/* Surface Scan Results */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-blue-600 font-medium">Sectors Tested</div>
            <div className="text-2xl font-bold text-blue-900">{total_sectors_tested?.toLocaleString() || 'N/A'}</div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg">
            <div className="text-sm text-red-600 font-medium">Bad Sectors</div>
            <div className="text-2xl font-bold text-red-900">{bad_sectors || 0}</div>
          </div>
        </div>

        {/* SMART Data - Only show if available (not null and has data) */}
        {smart_data && smart_data !== null && Object.keys(smart_data).length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3">SMART Data</h4>
            
            {/* Check if SMART data has error/note fields */}
            {smart_data.error || smart_data.note ? (
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg space-y-3">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-yellow-900 mb-1">{smart_data.error || 'SMART Data Limited'}</p>
                    {smart_data.note && <p className="text-sm text-yellow-700 mb-2">{smart_data.note}</p>}
                    {smart_data.reason && <p className="text-sm text-yellow-700 mb-2">{smart_data.reason}</p>}
                    
                    {/* Info list */}
                    {smart_data.info && Array.isArray(smart_data.info) && (
                      <div className="mt-3 space-y-1">
                        {smart_data.info.map((line, idx) => (
                          <p key={idx} className="text-xs text-yellow-800 font-mono">
                            {line}
                          </p>
                        ))}
                      </div>
                    )}
                    
                    {smart_data.alternative && (
                      <div className="mt-3 bg-green-100 border border-green-300 rounded p-3">
                        <p className="text-sm text-green-800 font-medium">
                          ✓ {smart_data.alternative}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* Normal SMART data display with enhanced formatting */
              <div className="space-y-4">
                {/* Key Health Indicators */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {smart_data.Health_Status && (
                    <div className={`p-3 rounded-lg border ${getSmartValue(smart_data.Health_Status) === 'PASS' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                      <div className="text-xs text-gray-600 mb-1">Health Status</div>
                      <div className={`text-lg font-bold ${getSmartValue(smart_data.Health_Status) === 'PASS' ? 'text-green-700' : 'text-red-700'}`}>
                        {getSmartValue(smart_data.Health_Status)}
                      </div>
                    </div>
                  )}
                  
                  {smart_data.Temperature_Celsius && (
                    <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                      <div className="text-xs text-gray-600 mb-1">Temperature</div>
                      <div className="text-lg font-bold text-blue-700">
                        {getSmartValue(smart_data.Temperature_Celsius)}
                      </div>
                    </div>
                  )}
                  
                  {smart_data.Power_On_Hours && (
                    <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                      <div className="text-xs text-gray-600 mb-1">Power On Time</div>
                      <div className="text-lg font-bold text-purple-700">
                        {getSmartValue(smart_data.Power_On_Hours)}
                      </div>
                    </div>
                  )}
                  
                  {smart_data.Percentage_Used && (
                    <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                      <div className="text-xs text-gray-600 mb-1">Drive Usage</div>
                      <div className="text-lg font-bold text-orange-700">
                        {getSmartValue(smart_data.Percentage_Used)}
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Device Information */}
                {(smart_data.Model || smart_data.Serial_Number || smart_data.Firmware_Version) && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h5 className="font-semibold text-gray-900 mb-3 text-sm">Device Information</h5>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                      {smart_data.Model && (
                        <div>
                          <span className="text-gray-600">Model:</span>
                          <span className="ml-2 font-medium text-gray-900">
                            {getSmartValue(smart_data.Model)}
                          </span>
                        </div>
                      )}
                      {smart_data.Serial_Number && (
                        <div>
                          <span className="text-gray-600">Serial:</span>
                          <span className="ml-2 font-medium text-gray-900">
                            {getSmartValue(smart_data.Serial_Number)}
                          </span>
                        </div>
                      )}
                      {smart_data.Firmware_Version && (
                        <div>
                          <span className="text-gray-600">Firmware:</span>
                          <span className="ml-2 font-medium text-gray-900">
                            {getSmartValue(smart_data.Firmware_Version)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* All SMART Attributes */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h5 className="font-semibold text-gray-900 mb-3 text-sm">Detailed SMART Attributes</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                    {Object.entries(smart_data)
                      .filter(([key]) => !['error', 'note', 'reason', 'alternative', 'info', 'troubleshooting', 'method', 'Health_Status', 'Model', 'Serial_Number', 'Firmware_Version'].includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm py-2 px-3 bg-white rounded border border-gray-200">
                          <span className="text-gray-600 font-medium">{key.replace(/_/g, ' ')}:</span>
                          <span className="text-gray-900 font-semibold ml-2">
                            {getSmartValue(value)}
                          </span>
                        </div>
                      ))}
                  </div>
                  
                  {smart_data.method && (
                    <div className="mt-3 text-xs text-gray-500 text-center">
                      Data source: {getSmartValue(smart_data.method)}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recommendations */}
        {recommendations && recommendations.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Recommendations</h4>
            <div className="space-y-2">
              {recommendations.map((rec, idx) => (
                <div key={idx} className={`p-3 rounded-lg flex items-start gap-3 ${
                  rec.includes('✅') ? 'bg-green-50' : rec.includes('⚠️') ? 'bg-yellow-50' : 'bg-red-50'
                }`}>
                  <span className="text-sm">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Surface Map Preview (first 20 sectors) */}
        {surface_map && surface_map.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Surface Map (Sample)</h4>
            <div className="flex flex-wrap gap-1">
              {surface_map.slice(0, 100).map((sector, idx) => (
                <div
                  key={idx}
                  className={`w-4 h-4 rounded-sm ${
                    sector.status === 'good' ? 'bg-green-500' : 
                    sector.status === 'bad' ? 'bg-red-500' : 'bg-yellow-500'
                  }`}
                  title={`Sector ${sector.sector}: ${sector.status}`}
                />
              ))}
            </div>
            <div className="flex gap-4 mt-3 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-500 rounded-sm"></div>
                <span>Good</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded-sm"></div>
                <span>Bad</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-yellow-500 rounded-sm"></div>
                <span>Error</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-blue-600" />
            <h3 className="text-xl font-bold text-gray-900">
              {scanType === 'cluster' ? 'Cluster Map Report' : 'Drive Health Report'}
            </h3>
          </div>
          {!embedded && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : reportData ? (
            scanType === 'cluster' ? renderClusterReport() : renderHealthReport()
          ) : (
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No report data available</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {!embedded && (
          <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
