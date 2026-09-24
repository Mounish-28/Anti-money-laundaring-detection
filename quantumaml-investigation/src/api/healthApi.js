import axios from 'axios';
import { setIsOfflineMode } from './client';

export const STATUS_CONNECTED = 'CONNECTED';
export const STATUS_OFFLINE = 'OFFLINE - MOCK MODE';

/**
 * Checks backend connectivity via FastAPI health or docs endpoint
 * Uses direct relative path through Vite proxy, or absolute fallback
 */
export async function checkHealth() {
  const t0 = performance.now();
  try {
    // 1. Primary Target: Proxied GET /api/v1/health
    const res = await axios.get('/api/v1/health', {
      timeout: 3000,
      headers: { Accept: 'application/json' },
    });

    const latencyMs = Math.round(performance.now() - t0);
    // Ensure response is from FastAPI backend (JSON object) and not Vite SPA fallback HTML
    const isFastApiResponse =
      res.status >= 200 &&
      res.status < 300 &&
      res.data &&
      typeof res.data === 'object' &&
      !String(res.data).includes('<!DOCTYPE');

    if (isFastApiResponse) {
      setIsOfflineMode(false);
      return {
        status: STATUS_CONNECTED,
        healthy: true,
        latencyMs,
        details: res.data,
      };
    }
  } catch {
    // 2. Secondary Target: Direct GET http://localhost:8000/docs or /api/v1/health
    try {
      const fallbackRes = await axios.get('http://localhost:8000/api/v1/health', {
        timeout: 2500,
        headers: { Accept: 'application/json' },
      });
      const latencyMs = Math.round(performance.now() - t0);
      if (
        fallbackRes.status >= 200 &&
        fallbackRes.status < 300 &&
        fallbackRes.data &&
        typeof fallbackRes.data === 'object'
      ) {
        setIsOfflineMode(false);
        return {
          status: STATUS_CONNECTED,
          healthy: true,
          latencyMs,
          details: fallbackRes.data,
        };
      }
    } catch {
      // Backend is offline / unreachable
    }
  }

  setIsOfflineMode(true);
  return {
    status: STATUS_OFFLINE,
    healthy: false,
    latencyMs: null,
    details: 'FastAPI Offline - Operating in Hermetic Mock Mode',
  };
}

export const healthApi = {
  checkHealth,
  STATUS_CONNECTED,
  STATUS_OFFLINE,
};

export default healthApi;
