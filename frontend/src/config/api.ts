const fallbackApiUrl = 'http://127.0.0.1:8000';
const fallbackWsUrl = 'ws://127.0.0.1:8000';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || fallbackApiUrl;
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || fallbackWsUrl;

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

export function wsUrl(path: string) {
  return `${WS_BASE_URL}${path}`;
}
