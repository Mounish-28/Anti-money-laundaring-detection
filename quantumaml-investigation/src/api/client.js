import axios from 'axios';

let isOfflineMode = false;
const offlineListeners = new Set();

export function getIsOfflineMode() {
  return isOfflineMode;
}

export function setIsOfflineMode(status) {
  const next = Boolean(status);
  if (isOfflineMode !== next) {
    isOfflineMode = next;
    offlineListeners.forEach((listener) => {
      try {
        listener(isOfflineMode);
      } catch (err) {
        console.error('[API] Error in offline mode listener:', err);
      }
    });
  }
}

export function subscribeOfflineMode(callback) {
  offlineListeners.add(callback);
  return () => {
    offlineListeners.delete(callback);
  };
}

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => config,
  (error) => {
    console.warn(`[API ERROR] Request setup -> ${error?.message || 'Unknown request error'}`);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    // A successful response confirms the backend is reachable
    setIsOfflineMode(false);
    return response;
  },
  (error) => {
    const method = error?.config?.method ? error.config.method.toUpperCase() : 'GET';
    const url = error?.config?.url || 'unknown';
    const message = error?.message || 'Network Error';

    console.warn(`[API ERROR] ${method} ${url} -> ${message}`);

    // Flag offline if connection failed, timed out, or encountered a 5xx gateway/server error
    const isNetworkOrTimeout =
      !error.response ||
      error.code === 'ECONNABORTED' ||
      error.code === 'ERR_NETWORK' ||
      message.includes('Network Error');

    const isServerError = error.response && error.response.status >= 500 && error.response.status <= 599;

    if (isNetworkOrTimeout || isServerError) {
      setIsOfflineMode(true);
    }

    // Pass the rejection along so services can invoke their specific mock fallback
    return Promise.reject(error);
  }
);

export default apiClient;
