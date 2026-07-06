// Subscribes to the live threat-event WebSocket and keeps a rolling buffer.
import { useEffect, useRef, useState, useCallback } from 'react';
import type { LiveThreat } from '@/types';

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}`;
const MAX_BUFFER = 100;

export function useThreatSocket() {
  const [threats, setThreats] = useState<LiveThreat[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/events`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Keep-alive ping.
      ws.send('ping');
    };
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data) as LiveThreat;
        if (data.type === 'threat') {
          setThreats((prev) => [data, ...prev].slice(0, MAX_BUFFER));
        }
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect after a short delay.
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { threats, connected };
}
