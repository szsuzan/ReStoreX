import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

/**
 * @param {string | null} recoveryId
 * @returns {import('../types/index.js').RecoveryProgress}
 */
export function useRecoveryProgress(recoveryId) {
  const [progress, setProgress] = useState({
    isRecovering: false,
    progress: 0,
    currentFile: '',
    filesRecovered: 0,
    totalFiles: 0,
    estimatedTimeRemaining: '0 minutes',
  });

  const { subscribe } = useWebSocket();

  useEffect(() => {
    if (!recoveryId) return;

    const unsubscribeProgress = subscribe('recovery_progress', (data) => {
      if (data.recoveryId === recoveryId) {
        setProgress(prev => ({
          ...prev,
          isRecovering: true,
          progress: data.progress,
          currentFile: data.currentFile,
          filesRecovered: data.filesRecovered,
          totalFiles: data.totalFiles || prev.totalFiles,
          estimatedTimeRemaining: data.estimatedTimeRemaining
        }));
      }
    });

    const unsubscribeCompleted = subscribe('recovery_completed', (data) => {
      if (data.recoveryId === recoveryId) {
        setProgress(prev => ({
          ...prev,
          isRecovering: false,
          progress: 100,
          filesRecovered: prev.totalFiles,
          estimatedTimeRemaining: '0 minutes'
        }));
      }
    });

    const unsubscribeFailed = subscribe('recovery_failed', (data) => {
      if (data.recoveryId === recoveryId) {
        setProgress(prev => ({
          ...prev,
          isRecovering: false,
          estimatedTimeRemaining: 'Failed'
        }));
      }
    });

    return () => {
      unsubscribeProgress();
      unsubscribeCompleted();
      unsubscribeFailed();
    };
  }, [recoveryId, subscribe]);

  return progress;
}