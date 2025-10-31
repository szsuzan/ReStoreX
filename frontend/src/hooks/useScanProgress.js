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
  });

  const { subscribe } = useWebSocket();

  useEffect(() => {
    if (!scanId) return;

    const unsubscribeProgress = subscribe('scan_progress', (data) => {
      if (data.scanId === scanId) {
        setProgress(prev => ({
          ...prev,
          isScanning: true,
          progress: data.progress,
          currentSector: data.currentSector,
          totalSectors: data.totalSectors || prev.totalSectors,
          filesFound: data.filesFound,
          estimatedTimeRemaining: data.estimatedTimeRemaining
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