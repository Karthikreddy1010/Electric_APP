/**
 * apiClient — Axios instance for authenticated API calls.
 *
 * Features:
 * - withCredentials: true → sends HTTP-only cookies automatically
 * - Request interceptor: attaches X-CSRF-Token header from cookie
 * - Response interceptor: on 401 → attempts /auth/refresh once, then retries
 *   On second 401 → clears state and redirects to /login
 */
import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Read a cookie value by name (for CSRF double-submit). */
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// ── Axios Instance ────────────────────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: '/',
  withCredentials: true, // Critical: sends HTTP-only cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor: Attach CSRF Token ─────────────────────────────────

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Double-submit CSRF: read CSRF cookie and echo it in the header
  const csrfToken = getCookie('csrf_token');
  if (csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// ── Response Interceptor: Automatic Token Refresh ─────────────────────────

let _isRefreshing = false;
let _refreshQueue: Array<() => void> = [];

function _drainQueue() {
  _refreshQueue.forEach((cb) => cb());
  _refreshQueue = [];
}

apiClient.interceptors.response.use(
  (response) => {
    // Unwrap the StandardResponseMiddleware envelope:
    //   { success: true, data: { ... actual payload ... } }
    // becomes just the actual payload on response.data
    if (response.data && response.data.success === true && response.data.data !== undefined) {
      response.data = response.data.data;
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Only handle 401 errors for non-auth endpoints (avoid infinite loops)
    const isAuthEndpoint = originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh') ||
      originalRequest.url?.includes('/auth/register') ||
      originalRequest.url?.includes('/auth/me') ||
      originalRequest.url?.includes('/auth/verify-email') ||
      originalRequest.url?.includes('/auth/resend-verification') ||
      originalRequest.url?.includes('/auth/forgot-password') ||
      originalRequest.url?.includes('/auth/reset-password');

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (_isRefreshing) {
        // Queue the request until refresh completes
        return new Promise((resolve) => {
          _refreshQueue.push(() => resolve(apiClient(originalRequest)));
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        // Attempt token refresh
        await apiClient.post('/auth/refresh');
        _drainQueue();
        return apiClient(originalRequest);
      } catch {
        // Refresh failed — session is expired, force logout
        _refreshQueue = [];
        // Dispatch a custom event that AuthContext listens to
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
        return Promise.reject(error);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
