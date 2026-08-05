/**
 * AuthContext — Production authentication state management.
 *
 * Replaces the mock AuthContext from Phase C1.
 *
 * State is maintained via HTTP-only cookies (set server-side).
 * On mount, calls GET /auth/me to restore session from cookie.
 * On session expiry, listens to the `auth:session-expired` event from apiClient.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../lib/apiClient.ts';

// ── Types ────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  zip_code: string;
  utility_provider: string;
  country: string;
  role: 'user' | 'admin' | 'developer';
  email_verified: boolean;
  account_status: string;
  created_at: string | null;
  last_login: string | null;
  preferences: Record<string, unknown>;
}

export type AuthStatus =
  | 'loading'       // Initial session check in progress
  | 'authenticated' // Logged in, email verified
  | 'unverified'    // Logged in but email not verified
  | 'unauthenticated'; // Not logged in

interface RegisterParams {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  zip_code?: string;
  utility_provider?: string;
}

interface AuthContextType {
  user: User | null;
  status: AuthStatus;
  isOnboarded: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  signup: (params: RegisterParams) => Promise<{ needsVerification: boolean }>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateProfile: (fields: Partial<Pick<User, 'first_name' | 'last_name' | 'zip_code' | 'utility_provider' | 'country'>> & { preferences?: Record<string, unknown> }) => Promise<void>;
  completeOnboarding: (zipCode: string, utility: string) => void; // kept for WelcomeWizard compat
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

export const AuthContextProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [isOnboarded, setIsOnboarded] = useState(true);
  const navigate = useNavigate();
  const sessionCheckDone = useRef(false);

  // ── Session Restoration ──────────────────────────────────────────────────

  const restoreSession = useCallback(async () => {
    try {
      const res = await apiClient.get('/auth/me');
      const u: User = res.data.user;
      setUser(u);
      setStatus(u.email_verified ? 'authenticated' : 'unverified');
      // Onboarding: treat as needing wizard if zip/utility not set
      const needsWizard = !u.zip_code || !u.utility_provider;
      setIsOnboarded(!needsWizard);
    } catch {
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  useEffect(() => {
    if (!sessionCheckDone.current) {
      sessionCheckDone.current = true;
      restoreSession();
    }
  }, [restoreSession]);

  // ── Listen for session expiry from apiClient interceptor ────────────────

  useEffect(() => {
    const handleExpired = () => {
      setUser(null);
      setStatus('unauthenticated');
      if (sessionStorage.getItem('is_demo_mode') !== 'true') {
        navigate('/login');
      }
    };
    window.addEventListener('auth:session-expired', handleExpired);
    return () => window.removeEventListener('auth:session-expired', handleExpired);
  }, [navigate]);

  // ── Auth Actions ─────────────────────────────────────────────────────────

  const login = useCallback(async (email: string, password: string, rememberMe = false) => {
    const res = await apiClient.post('/auth/login', {
      email,
      password,
      remember_me: rememberMe,
    });
    const u: User = res.data.user;
    setUser(u);
    setStatus(u.email_verified ? 'authenticated' : 'unverified');
    const needsWizard = !u.zip_code || !u.utility_provider;
    setIsOnboarded(!needsWizard);
  }, []);

  const signup = useCallback(async (params: RegisterParams) => {
    await apiClient.post('/auth/register', params);
    // After signup, user needs to verify email — do not log them in
    return { needsVerification: true };
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore logout errors — clear state anyway
    }
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const res = await apiClient.post('/auth/refresh');
      const u: User = res.data.user;
      setUser(u);
      setStatus(u.email_verified ? 'authenticated' : 'unverified');
    } catch {
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  const updateProfile = useCallback(async (fields: Parameters<AuthContextType['updateProfile']>[0]) => {
    const res = await apiClient.put('/auth/profile', fields);
    setUser(res.data.user);
  }, []);

  // Backward compat for WelcomeWizard
  const completeOnboarding = useCallback((zipCode: string, utility: string) => {
    if (user) {
      const updated = { ...user, zip_code: zipCode, utility_provider: utility };
      setUser(updated as User);
      setIsOnboarded(true);
      // Fire and forget — persist to API
      updateProfile({ zip_code: zipCode, utility_provider: utility }).catch(console.warn);
    }
  }, [user, updateProfile]);

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isOnboarded,
        login,
        signup,
        logout,
        refreshSession,
        updateProfile,
        completeOnboarding,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// ── Hook ──────────────────────────────────────────────────────────────────────

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthContextProvider');
  return ctx;
};
