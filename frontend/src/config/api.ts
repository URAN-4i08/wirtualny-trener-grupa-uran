function resolveLanHost(): string {
  if (typeof window === 'undefined') return '127.0.0.1';
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') return '127.0.0.1';
  return hostname;
}

const lanHost = resolveLanHost();
const fallbackApiUrl = `http://${lanHost}:8000`;
const fallbackWsUrl = `ws://${lanHost}:8000`;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || fallbackApiUrl;
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || fallbackWsUrl;

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

export function wsUrl(path: string) {
  return `${WS_BASE_URL}${path}`;
}
