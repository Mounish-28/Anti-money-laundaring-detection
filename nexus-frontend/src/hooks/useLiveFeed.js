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
  const [activeFiatAlert, setActiveFiatAlert] = useState(null);
  const [activeCryptoAlert, setActiveCryptoAlert] = useState(null);
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
  const pingIntervalRef = useRef(null);
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
      // Start 15s keepalive ping interval
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: 'ping' }));
          } catch {
            // Socket error will trigger onclose
          }
        }
      }, 15000);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (!payload) return;

        // Handle keepalive pong and dispatch ack responses
        if (payload.type === 'pong' || payload.type === 'DISPATCH_ACK') return;

        // Catch incoming real-time SAR_DISPATCHED regulatory alert events
        if (payload.event === 'SAR_DISPATCHED') {
          setLastSarDispatched({
            ...payload,
            receivedAt: new Date().toISOString(),
          });
          setDispatchedSarCount((prev) => prev + 1);

          const isCryptoSar =
            payload.engine === 'CRYPTO_FORENSICS' ||
            payload.rail === 'BTC' ||
            payload.currency === 'BTC' ||
            Boolean(payload.exposure_btc);

          const updateAlertWithSar = (prev) => {
            if (!prev) return prev;
            const matchesTxId =
              payload.triggering_tx_id && prev.transaction_id === payload.triggering_tx_id;
            const matchesSuspect =
              payload.suspect &&
              (prev.from_entity === payload.suspect || prev.to_entity === payload.suspect);
            if (matchesTxId || matchesSuspect || !prev.sar_id) {
              return {
                ...prev,
                sar_id: payload.sar_id,
                sar_status: payload.status || 'PENDING_REVIEW',
              };
            }
            return prev;
          };

          // Update general and separate alerts
          setActiveAlert(updateAlertWithSar);
          if (isCryptoSar) {
            setActiveCryptoAlert(updateAlertWithSar);
          } else {
            setActiveFiatAlert(updateAlertWithSar);
          }

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
                  risk_tier: 'CRITICAL_SAR',
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
            Boolean(payload.sar_id) ||
            payload.risk_tier === 'CRITICAL_SAR' ||
            payload.risk_tier === 'CRITICAL' ||
            payload.risk_tier === 'HIGH' ||
            payload.risk_tier === 'HIGH_RISK' ||
            Number(payload.risk_score) >= 0.80 ||
            (Array.isArray(payload.flags) &&
              payload.flags.some((f) =>
                [
                  'PAN_STRUCTURING_EVASION',
                  'HAWALA_WIRE',
                  'MULE_BURST',
                  'AUTO_FLAG_SAR',
                  'CRITICAL_SAR',
                  'ANOMALY',
                  'WHALE_TRANSFER',
                ].includes(String(f).toUpperCase())
              ));
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

        const isCrypto =
          payload.engine === 'CRYPTO_FORENSICS' ||
          payload.currency === 'BTC' ||
          payload.rail === 'BTC';

        // Trigger separate critical alert banners if CRITICAL_SAR or CRITICAL
        if (
          payload.risk_tier === 'CRITICAL_SAR' ||
          payload.risk_tier === 'CRITICAL' ||
          Boolean(payload.sar_id)
        ) {
          const alertData = {
            ...payload,
            alertId: `${payload.transaction_id}-${Date.now()}`,
          };
          setActiveAlert(alertData);
          if (isCrypto) {
            setActiveCryptoAlert(alertData);
          } else {
            setActiveFiatAlert(alertData);
          }
        }

        // Only buffer onto sliding window if not paused (bounded circular buffer: max 100 entries)
        // Deduplicate incoming items by transaction_id
        if (!isPausedRef.current) {
          setTransactions((prev) => {
            if (prev.some((tx) => tx.transaction_id === payload.transaction_id)) {
              return prev;
            }
            return [payload, ...prev.slice(0, 99)];
          });
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
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      // Exponential backoff reconnection with jitter: 2s, 4s, 8s, up to 16s + jitter
      const jitter = Math.floor(Math.random() * 1000);
      const delay = Math.min(16000, 2000 * Math.pow(2, reconnectAttemptRef.current)) + jitter;
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };
  }, [getWsUrl]);

  useEffect(() => {
    connect();

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
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
    setActiveFiatAlert(null);
    setActiveCryptoAlert(null);
  }, []);

  const dismissFiatAlert = useCallback(() => {
    setActiveFiatAlert(null);
  }, []);

  const dismissCryptoAlert = useCallback(() => {
    setActiveCryptoAlert(null);
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

  /**
   * Dispatches a manual transaction or custom AML event over the /ws/live duplex
   * stream with immediate zero-reload optimistic UI update and REST fallback.
   */
  const dispatchTransaction = useCallback(
    async (eventData) => {
      if (!eventData) return null;

      const isCrypto =
        eventData.rail === 'BTC' ||
        eventData.currency === 'BTC' ||
        eventData.engine === 'CRYPTO_FORENSICS';

      const txId =
        eventData.transaction_id ||
        (isCrypto
          ? `btc_live_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`
          : `TX_UPI_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`);

      const payload = {
        transaction_id: txId,
        rail: eventData.rail || (isCrypto ? 'BTC' : 'UPI'),
        currency: eventData.currency || (isCrypto ? 'BTC' : 'INR'),
        amount: Number(eventData.amount || (isCrypto ? 1.5 : 49500)),
        from_entity:
          eventData.from_entity ||
          (isCrypto ? 'bc1q_unhosted_target' : 'remitter_account_901'),
        to_entity:
          eventData.to_entity ||
          (isCrypto ? 'bc1q_mixer_cluster' : 'beneficiary_aggregator_11'),
        risk_tier: eventData.risk_tier || 'CRITICAL_SAR',
        risk_score: Number(eventData.risk_score !== undefined ? eventData.risk_score : 0.985),
        flags: Array.isArray(eventData.flags)
          ? eventData.flags
          : [eventData.flag || 'PAN_STRUCTURING_EVASION'],
        engine: isCrypto ? 'CRYPTO_FORENSICS' : 'FIAT_BANKING',
        latency_ms: 0.8,
        timestamp: new Date().toISOString(),
        auto_trigger_sar: Boolean(eventData.auto_trigger_sar),
        is_manual_dispatch: true,
      };

      // 1. Immediate optimistic UI update (zero-reload)
      setTransactions((prev) => {
        if (prev.some((tx) => tx.transaction_id === payload.transaction_id)) return prev;
        return [payload, ...prev.slice(0, 99)];
      });

      // Update telemetry
      setTelemetry((prev) => ({
        ...prev,
        totalScreened: prev.totalScreened + 1,
        threatFlagsCount:
          payload.risk_tier === 'CRITICAL_SAR' || payload.risk_tier === 'CRITICAL'
            ? prev.threatFlagsCount + 1
            : prev.threatFlagsCount,
        fiatCount: !isCrypto ? prev.fiatCount + 1 : prev.fiatCount,
        cryptoCount: isCrypto ? prev.cryptoCount + 1 : prev.cryptoCount,
      }));

      // Trigger local alert banner immediately if critical
      if (payload.risk_tier === 'CRITICAL_SAR' || payload.risk_tier === 'CRITICAL') {
        const alertData = {
          ...payload,
          alertId: `${payload.transaction_id}-${Date.now()}`,
        };
        setActiveAlert(alertData);
        if (isCrypto) {
          setActiveCryptoAlert(alertData);
        } else {
          setActiveFiatAlert(alertData);
        }
      }

      // 2. Persistent duplex WebSocket transmission over /ws/live
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(
            JSON.stringify({
              type: 'DISPATCH',
              transaction: payload,
            })
          );
          return payload;
        } catch (err) {
          console.warn('Live WebSocket dispatch failed, using REST fallback:', err);
        }
      }

      // 3. Fallback async REST endpoint dispatch
      try {
        const res = await fetch(`${apiUrl}/api/v1/live/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          throw new Error(`REST dispatch failed with HTTP ${res.status}`);
        }
      } catch (err) {
        console.error('Failed to dispatch manual event via REST fallback:', err);
      }

      return payload;
    },
    [apiUrl]
  );

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
    activeFiatAlert,
    activeCryptoAlert,
    dismissAlert,
    dismissFiatAlert,
    dismissCryptoAlert,
    lastSarDispatched,
    dispatchedSarCount,
    updateTransactionSar,
    updateTransactionStatus,
    dispatchTransaction,
  };
}
