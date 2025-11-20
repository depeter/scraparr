import { useEffect, useState, useCallback, useRef } from 'react';

interface ProgressUpdate {
  execution_id: number;
  status: string;
  items_scraped: number;
  elapsed_seconds: number;
  message: string;
  timestamp: string;
}

interface UseExecutionProgressOptions {
  executionId: number | null;
  enabled?: boolean;
}

export function useExecutionProgress({ executionId, enabled = true }: UseExecutionProgressOptions) {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!executionId || !enabled) return;

    // Get WebSocket URL from environment or default
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_WS_URL || window.location.host.replace(':3001', ':8000').replace(':3000', ':8000');
    const wsUrl = `${protocol}//${host}/ws/execution/${executionId}`;

    console.log('[WebSocket] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected to execution', executionId);
      setIsConnected(true);
      setError(null);

      // Send periodic pings to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000); // Ping every 30 seconds

      // Store interval ID on the WebSocket object for cleanup
      (ws as any).pingInterval = pingInterval;
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return; // Ignore pong responses

      try {
        const update: ProgressUpdate = JSON.parse(event.data);
        console.log('[WebSocket] Progress update:', update);
        setProgress(update);
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err);
      }
    };

    ws.onerror = (event) => {
      console.error('[WebSocket] Error:', event);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected from execution', executionId);
      setIsConnected(false);

      // Clear ping interval
      if ((ws as any).pingInterval) {
        clearInterval((ws as any).pingInterval);
      }
    };
  }, [executionId, enabled]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      console.log('[WebSocket] Manually disconnecting');
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    progress,
    isConnected,
    error,
    reconnect: connect,
  };
}
