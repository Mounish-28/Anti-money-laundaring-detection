import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useLiveFeed
 * Establishes a persistent, resilient WebSocket connection to QuantumAML Nexus (/ws/live),
 * implements exponential backoff reconnection, maintains a 100-entry bounded circular buffer,
 * and computes real-time session telemetry.
 */
export function useLiveFeed(apiUrl) {
  const [connectionStatus, setConnectionStatus] = useState('CONNECTING'); // 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED'
  const [transactions, setTransactions] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [activeAlert, setActiveAlert] = useState(null);
  const [lastSarDispatched, setLastSarDispatched] = useState(null);
  const [dispatchedSarCount, setDispatchedSarCount] = useState(0);

  // Session telemetry counters
  const [telemetry, setTelemetry] = useState({
    totalScreened: 0,
    rollingLatencies: [],
    threatFlagsCount: 0, // CRITICAL_SAR and HIGH
    fiatCount: 0,
    cryptoCount: 0,
  });

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const isPausedRef = useRef(false);
  isPausedRef.current = isPaused;

  // Convert HTTP/HTTPS apiUrl to WS/WSS
  const getWsUrl = useCallback(() => {
    try {
      const url = new URL(apiUrl || 'http://localhost:8000');
      const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${url.host}/ws/live`;
    } catch {
      return 'ws://localhost:8000/ws/live';
    }
  }, [apiUrl]);

  const connect = useCallback(() => {
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    setConnectionStatus('CONNECTING');
    const wsUrl = getWsUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('CONNECTED');
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (!payload) return;

        // Catch incoming real-time SAR_DISPATCHED regulatory alert events
        if (payload.event === 'SAR_DISPATCHED') {
          setLastSarDispatched({
            ...payload,
            receivedAt: new Date().toISOString(),
          });
          setDispatchedSarCount((prev) => prev + 1);

          // If the triggering transaction already exists in the 100-item circular ledger, update that row's data object with sar_id
          setTransactions((prev) =>
            prev.map((tx) => {
              const matchesTxId =
                payload.triggering_tx_id && tx.transaction_id === payload.triggering_tx_id;
              const matchesSuspect =
                payload.suspect &&
                (tx.from_entity === payload.suspect || tx.to_entity === payload.suspect);
              const matchesAmount =
                payload.exposure_inr &&
                (tx.amount === payload.exposure_inr || tx.amount === payload.exposure_btc);

              if (
                matchesTxId ||
                (matchesSuspect && matchesAmount) ||
                (tx.risk_tier === 'CRITICAL_SAR' && !tx.sar_id)
              ) {
                return {
                  ...tx,
                  sar_id: payload.sar_id,
                  sar_status: payload.status || 'PENDING_REVIEW',
                };
              }
              return tx;
            })
          );
          return;
        }

        if (!payload.transaction_id) return;

        // Telemetry updates (always computed even if feed display is paused)
        setTelemetry((prev) => {
          const lat =
            typeof payload.latency_ms === 'number' ? payload.latency_ms : 12.0;
          const isThreat =
            payload.risk_tier === 'CRITICAL_SAR' || payload.risk_tier === 'HIGH';
          const isCrypto =
            payload.engine === 'CRYPTO_FORENSICS' ||
            payload.currency === 'BTC' ||
            payload.rail === 'BTC';

          // Keep up to latest 50 latency samples for rolling average
          const newLatencies = [lat, ...prev.rollingLatencies.slice(0, 49)];

          return {
            totalScreened: prev.totalScreened + 1,
            rollingLatencies: newLatencies,
            threatFlagsCount: isThreat
              ? prev.threatFlagsCount + 1
              : prev.threatFlagsCount,
            fiatCount: !isCrypto ? prev.fiatCount + 1 : prev.fiatCount,
            cryptoCount: isCrypto ? prev.cryptoCount + 1 : prev.cryptoCount,
          };
        });

        // Trigger critical alert banner if CRITICAL_SAR
        if (payload.risk_tier === 'CRITICAL_SAR') {
          setActiveAlert({
            ...payload,
            alertId: `${payload.transaction_id}-${Date.now()}`,
          });
        }

        // Only buffer onto sliding window if not paused (bounded circular buffer: max 100 entries)
        if (!isPausedRef.current) {
          setTransactions((prev) => [payload, ...prev.slice(0, 99)]);
        }
      } catch (err) {
        console.warn('Error processing WebSocket message:', err);
      }
    };

    ws.onerror = () => {
      setConnectionStatus('DISCONNECTED');
    };

    ws.onclose = () => {
      setConnectionStatus('DISCONNECTED');
      // Exponential backoff reconnection: 2s, 4s, 8s, up to 16s
      const delay = Math.min(16000, 2000 * Math.pow(2, reconnectAttemptRef.current));
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };
  }, [getWsUrl]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on manual unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  const togglePause = useCallback(() => {
    setIsPaused((prev) => !prev);
  }, []);

  const clearFeed = useCallback(() => {
    setTransactions([]);
  }, []);

  const dismissAlert = useCallback(() => {
    setActiveAlert(null);
  }, []);

  const updateTransactionSar = useCallback((sarId, matchKey) => {
    setTransactions((prev) =>
      prev.map((tx) => {
        const matchesKey =
          matchKey &&
          (tx.transaction_id === matchKey ||
            tx.from_entity === matchKey ||
            tx.to_entity === matchKey);
        if (matchesKey || (tx.risk_tier === 'CRITICAL_SAR' && !tx.sar_id && !matchKey)) {
          return { ...tx, sar_id: sarId };
        }
        return tx;
      })
    );
  }, []);

  const updateTransactionStatus = useCallback((sarId, newStatus) => {
    setTransactions((prev) =>
      prev.map((tx) => (tx.sar_id === sarId ? { ...tx, sar_status: newStatus } : tx))
    );
  }, []);

  // Compute rolling average latency
  const avgLatency =
    telemetry.rollingLatencies.length > 0
      ? (
          telemetry.rollingLatencies.reduce((acc, curr) => acc + curr, 0) /
          telemetry.rollingLatencies.length
        ).toFixed(1)
      : '12.4';

  return {
    connectionStatus,
    transactions,
    telemetry: {
      ...telemetry,
      avgLatency,
    },
    isPaused,
    togglePause,
    clearFeed,
    activeAlert,
    dismissAlert,
    lastSarDispatched,
    dispatchedSarCount,
    updateTransactionSar,
    updateTransactionStatus,
  };
}
