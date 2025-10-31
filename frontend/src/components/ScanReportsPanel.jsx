import React, { useState } from 'react';
import { FileText, Activity, Database, Search, Shield, CheckCircle, AlertTriangle, Info, ChevronDown, ChevronRight } from 'lucide-react';

/**
 * Component to display scan reports and analysis
 * @param {Object} props
 * @param {Object} props.scanMetadata - Metadata from the scan (health report, cluster analysis, etc.)
 * @param {string} props.scanType - Type of scan performed
 */
export function ScanReportsPanel({ scanMetadata, scanType }) {
  const [expandedSections, setExpandedSections] = useState({
    health: true,
    cluster: true,
    forensic: true
  });

  if (!scanMetadata || Object.keys(scanMetadata).length === 0) {
    return null;
  }

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const renderHealthReport = (healthReport) => {
    if (!healthReport) return null;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-4">
        <div 
          className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
          onClick={() => toggleSection('health')}
        >
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Health Scan Report</h3>
              <p className="text-sm text-gray-600">{healthReport.drive_name}</p>
            </div>
          </div>
          {expandedSections.health ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>

        {expandedSections.health && (
          <div className="p-6 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Scan Time</p>
                <p className="text-lg font-semibold text-gray-900">
                  {new Date(healthReport.scan_time).toLocaleString()}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Checks Performed</p>
                <p className="text-lg font-semibold text-gray-900">
                  {healthReport.checks?.length || 0}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 mb-3">Health Checks</h4>
              {healthReport.checks?.map((check, index) => (
                <div key={index} className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 mt-1">
                    {check.status === 'pass' && <CheckCircle className="w-5 h-5 text-green-600" />}
                    {check.status === 'warning' && <AlertTriangle className="w-5 h-5 text-orange-600" />}
                    {check.status === 'fail' && <AlertTriangle className="w-5 h-5 text-red-600" />}
                    {check.status === 'skip' && <Info className="w-5 h-5 text-gray-400" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h5 className="font-semibold text-gray-900">{check.name}</h5>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        check.status === 'pass' ? 'bg-green-100 text-green-700' :
                        check.status === 'warning' ? 'bg-orange-100 text-orange-700' :
                        check.status === 'fail' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {check.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{check.details}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderClusterAnalysis = (clusterAnalysis) => {
    if (!clusterAnalysis) return null;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-4">
        <div 
          className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
          onClick={() => toggleSection('cluster')}
        >
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-purple-600" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Cluster Analysis</h3>
              <p className="text-sm text-gray-600">File system cluster information</p>
            </div>
          </div>
          {expandedSections.cluster ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>

        {expandedSections.cluster && (
          <div className="p-6 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <p className="text-sm text-blue-600 mb-1">Total Clusters</p>
                <p className="text-2xl font-bold text-blue-900">
                  {clusterAnalysis.total_clusters?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <p className="text-sm text-green-600 mb-1">Used Clusters</p>
                <p className="text-2xl font-bold text-green-900">
                  {clusterAnalysis.used_clusters?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600 mb-1">Free Clusters</p>
                <p className="text-2xl font-bold text-gray-900">
                  {clusterAnalysis.free_clusters?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                <p className="text-sm text-orange-600 mb-1">Fragmented Files</p>
                <p className="text-2xl font-bold text-orange-900">
                  {clusterAnalysis.fragmented_files?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                <p className="text-sm text-red-600 mb-1">Orphaned Clusters</p>
                <p className="text-2xl font-bold text-red-900">
                  {clusterAnalysis.orphaned_clusters?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <p className="text-sm text-purple-600 mb-1">Usage</p>
                <p className="text-2xl font-bold text-purple-900">
                  {clusterAnalysis.used_clusters && clusterAnalysis.total_clusters 
                    ? ((clusterAnalysis.used_clusters / clusterAnalysis.total_clusters) * 100).toFixed(1)
                    : 0}%
                </p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h4 className="font-semibold text-blue-900 mb-2">Analysis Summary</h4>
              <ul className="space-y-1 text-sm text-blue-800">
                <li>• Cluster size: 4 KB (typical NTFS)</li>
                <li>• Fragmentation rate: {clusterAnalysis.fragmented_files && clusterAnalysis.used_clusters
                  ? ((clusterAnalysis.fragmented_files / clusterAnalysis.used_clusters) * 100).toFixed(2)
                  : 0}%</li>
                <li>• Orphaned data detected in {clusterAnalysis.orphaned_clusters?.toLocaleString() || 0} clusters</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderForensicData = (forensicData) => {
    if (!forensicData) return null;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-4">
        <div 
          className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
          onClick={() => toggleSection('forensic')}
        >
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-red-600" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Forensic Analysis Report</h3>
              <p className="text-sm text-gray-600">Chain of custody and evidence logging</p>
            </div>
          </div>
          {expandedSections.forensic ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>

        {expandedSections.forensic && (
          <div className="p-6 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <p className="text-sm text-blue-600 mb-1">Files Analyzed</p>
                <p className="text-2xl font-bold text-blue-900">
                  {forensicData.files_analyzed?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <p className="text-sm text-green-600 mb-1">Hashes Calculated</p>
                <p className="text-2xl font-bold text-green-900">
                  {forensicData.hashes_calculated?.toLocaleString() || 0}
                </p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <p className="text-sm text-purple-600 mb-1">Evidence Entries</p>
                <p className="text-2xl font-bold text-purple-900">
                  {forensicData.evidence_log?.length || 0}
                </p>
              </div>
              <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                <p className="text-sm text-orange-600 mb-1">Custody Events</p>
                <p className="text-2xl font-bold text-orange-900">
                  {forensicData.chain_of_custody?.length || 0}
                </p>
              </div>
            </div>

            {/* Evidence Log */}
            <div className="mb-6">
              <h4 className="font-semibold text-gray-900 mb-3">Evidence Log</h4>
              <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                {forensicData.evidence_log?.map((entry, index) => (
                  <div key={index} className="mb-3 pb-3 border-b border-gray-200 last:border-0 last:mb-0 last:pb-0">
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 text-gray-400 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-gray-900">{entry.action}</p>
                        <p className="text-xs text-gray-600">{entry.details}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(entry.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Chain of Custody */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Chain of Custody</h4>
              <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                {forensicData.chain_of_custody?.map((event, index) => (
                  <div key={index} className="mb-3 last:mb-0">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-red-600 rounded-full"></div>
                      <p className="text-sm font-semibold text-red-900">{event.action}</p>
                    </div>
                    <p className="text-xs text-red-700 ml-4 mt-1">
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-gray-50 border-t border-gray-200">
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-center gap-2 mb-6">
          <Search className="w-6 h-6 text-gray-700" />
          <h2 className="text-2xl font-bold text-gray-900">Scan Reports</h2>
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            {scanType?.toUpperCase() || 'SCAN'}
          </span>
        </div>

        <div className="space-y-4">
          {scanMetadata.health_report && renderHealthReport(scanMetadata.health_report)}
          {scanMetadata.cluster_analysis && renderClusterAnalysis(scanMetadata.cluster_analysis)}
          {scanMetadata.forensic_data && renderForensicData(scanMetadata.forensic_data)}
        </div>
      </div>
    </div>
  );
}
