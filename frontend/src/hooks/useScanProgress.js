import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

/**
 * @param {string | null} scanId
 * @returns {import('../types/index.js').ScanProgress}
 */
export function useScanProgress(scanId) {
  const [progress, setProgress] = useState({
    isScanning: false,
    progress: 0,
    currentSector: 0,
    totalSectors: 0,
    filesFound: 0,
    estimatedTimeRemaining: '0 minutes',
    currentPass: 0,
    expectedTime: 'Calculating...',
  });

  const { subscribe } = useWebSocket();

  useEffect(() => {
    if (!scanId) return;

    const unsubscribeProgress = subscribe('scan_progress', (data) => {
      if (data.scanId === scanId) {
        // Extract scan statistics if available
        const scanStats = data.scan_stats || {};
        
        setProgress(prev => ({
          ...prev,
          isScanning: true,
          progress: data.progress,
          currentSector: scanStats.scanned_sectors || data.currentSector || 0,
          totalSectors: scanStats.total_sectors || data.totalSectors || prev.totalSectors,
          filesFound: data.filesFound || data.files_found || 0,
          estimatedTimeRemaining: scanStats.estimated_time || data.estimatedTimeRemaining || 'Calculating...',
          currentPass: scanStats.current_pass || 0,
          expectedTime: scanStats.expected_time || 'Calculating...',
        }));
      }
    });

    const unsubscribeCompleted = subscribe('scan_completed', (data) => {
      if (data.scanId === scanId) {
        setProgress(prev => ({
          ...prev,
          isScanning: false,
          progress: 100,
          estimatedTimeRemaining: '0 minutes'
        }));
      }
    });

    const unsubscribeFailed = subscribe('scan_failed', (data) => {
      if (data.scanId === scanId) {
        setProgress(prev => ({
          ...prev,
          isScanning: false,
          estimatedTimeRemaining: 'Failed'
        }));
      }
    });

    return () => {
      unsubscribeProgress();
      unsubscribeCompleted();
      unsubscribeFailed();
    };
  }, [scanId, subscribe]);

  return progress;
}