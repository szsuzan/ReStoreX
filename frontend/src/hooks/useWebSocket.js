import { useEffect, useRef } from 'react';
import { apiService } from '../services/apiService';

export function useWebSocket() {
  const isConnected = useRef(false);

  useEffect(() => {
    if (!isConnected.current) {
      apiService.connectWebSocket();
      isConnected.current = true;
    }

    return () => {
      // Cleanup on unmount
      isConnected.current = false;
    };
  }, []);

  const subscribe = (eventType, callback) => {
    apiService.addEventListener(eventType, callback);
    
    return () => {
      apiService.removeEventListener(eventType, callback);
    };
  };

  return { subscribe };
}