import React, { useEffect, useState } from 'react';
import { X, Activity, AlertTriangle, CheckCircle, HardDrive, TrendingUp, Database } from 'lucide-react';
import { apiService } from '../services/apiService';

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {() => void} props.onClose
 * @param {Object} props.drive
 */
export function DriveHealthDialog({ isOpen, onClose, drive }) {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && drive) {
      fetchHealthData();
    }
  }, [isOpen, drive]);

  const fetchHealthData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getDriveHealth(drive.id);
      if (response.status === 'success') {
        setHealthData(response.data);
      } else {
        setError('Failed to load health data');
      }
    } catch (err) {
      console.error('Error fetching health data:', err);
      setError('Failed to load health data');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getHealthColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getHealthBgColor = (score) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-blue-100';
    if (score >= 40) return 'bg-orange-100';
    return 'bg-red-100';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Drive Health Check</h2>
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
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-sm text-gray-600">Analyzing drive health...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <AlertTriangle className="w-12 h-12 text-red-600 mb-4" />
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={fetchHealthData}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : healthData ? (
            <div className="space-y-6">
              {/* Health Score */}
              <div className={`${getHealthBgColor(healthData.health_score)} rounded-xl p-6`}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Overall Health</h3>
                    <p className={`text-3xl font-bold ${getHealthColor(healthData.health_score)}`}>
                      {healthData.health_status}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">Health Score</p>
                    <p className={`text-4xl font-bold ${getHealthColor(healthData.health_score)}`}>
                      {healthData.health_score}
                    </p>
                  </div>
                </div>
                <div className="w-full bg-white bg-opacity-50 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      healthData.health_score >= 80 ? 'bg-green-600' :
                      healthData.health_score >= 60 ? 'bg-blue-600' :
                      healthData.health_score >= 40 ? 'bg-orange-600' :
                      'bg-red-600'
                    }`}
                    style={{ width: `${healthData.health_score}%` }}
                  />
                </div>
              </div>

              {/* Disk Usage */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Disk Usage</h3>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">Total Capacity</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.disk_usage.total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Used Space</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.disk_usage.used}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Free Space</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.disk_usage.free}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Usage</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.disk_usage.percent}%</p>
                  </div>
                </div>
                <div className="w-full bg-gray-300 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      healthData.disk_usage.percent > 90 ? 'bg-red-600' :
                      healthData.disk_usage.percent > 75 ? 'bg-orange-600' :
                      'bg-green-600'
                    }`}
                    style={{ width: `${healthData.disk_usage.percent}%` }}
                  />
                </div>
              </div>

              {/* Issues */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  {healthData.issues[0] === "No issues detected" ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-orange-600" />
                  )}
                  <h3 className="text-lg font-semibold text-gray-900">Detected Issues</h3>
                </div>
                <ul className="space-y-2">
                  {healthData.issues.map((issue, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-1">
                        {issue === "No issues detected" ? "✅" : "⚠️"}
                      </span>
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* I/O Statistics */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">I/O Statistics</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Read Operations</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.io_stats.read_count.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">{healthData.io_stats.read_bytes}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Write Operations</p>
                    <p className="text-lg font-semibold text-gray-900">{healthData.io_stats.write_count.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">{healthData.io_stats.write_bytes}</p>
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
                <div className="flex items-center gap-2 mb-4">
                  <HardDrive className="w-5 h-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Recommendations</h3>
                </div>
                <ul className="space-y-2">
                  {healthData.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
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
          {healthData && (
            <button
              onClick={fetchHealthData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
