import { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/apiService';

/**
 * Custom hook for real-time system performance monitoring
 * @returns {Object} System performance data and loading state
 */
export function useSystemPerformance() {
  const [performance, setPerformance] = useState({
    cpu: { percent: 0, count: 0, frequency: null },
    memory: { percent: 0, used_gb: 0, total_gb: 0, available_gb: 0 },
    disk: { percent: 0, used_gb: 0, total_gb: 0, read_mb: 0, write_mb: 0 },
    network: { sent_mb: 0, recv_mb: 0 },
    temperature: null,
    processes: 0,
    platform: 'Unknown'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    // Initial fetch
    const fetchInitialData = async () => {
      try {
        const response = await apiService.getSystemPerformance();
        if (isMounted && response?.data) {
          setPerformance(response.data);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch initial performance data:', err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchInitialData();

    // Connect to WebSocket stream for real-time updates
    try {
      wsRef.current = apiService.connectSystemPerformanceStream((data) => {
        if (isMounted) {
          setPerformance(data);
          setIsLoading(false);
          setError(null);
        }
      });
    } catch (err) {
      console.error('Failed to connect to performance stream:', err);
      setError(err.message);
    }

    // Cleanup
    return () => {
      isMounted = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { performance, isLoading, error };
}
