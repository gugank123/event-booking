import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

// Session tokens live in memory only. The short-lived access token is kept
// in React state (+ a ref mirror for stable async access); the long-lived
// refresh token lives in an HttpOnly cookie managed by the backend, so no
// token secret ever touches localStorage.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const tokenRef = useRef(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimer = useRef(null);

  // One-time migration: drop tokens stored by older app versions.
  useEffect(() => {
    localStorage.removeItem('eventflow_access');
    localStorage.removeItem('eventflow_refresh');
  }, []);

  function setAccess(value) {
    tokenRef.current = value;
    setToken(value);
  }

  function clearSession() {
    setAccess(null);
    setUser(null);
    localStorage.removeItem('eventflow_access');
    localStorage.removeItem('eventflow_refresh');
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }

  const refreshAccess = useCallback(async () => {
    try {
      // No body needed: the backend reads the HttpOnly refresh cookie.
      const data = await api.post('/auth/refresh/', {});
      if (!data.access) throw new Error('refresh failed');
      setAccess(data.access);
      scheduleRefresh();
      return data.access;
    } catch {
      clearSession();
      return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function scheduleRefresh() {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    // Access tokens live 60 min — rotate silently at 50 min.
    refreshTimer.current = setTimeout(() => refreshAccess(), 50 * 60 * 1000);
  }

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      const next = await refreshAccess();
      if (cancelled) return;
      if (next) {
        try {
          const data = await api.get('/auth/me/', next);
          if (!cancelled) setUser(data.user);
        } catch {
          if (!cancelled) clearSession();
        }
      }
      if (!cancelled) setLoading(false);
    }
    boot();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persistSession(data) {
    // data.refresh (if present) is intentionally ignored: the refresh
    // token already arrived as an HttpOnly cookie on this response.
    setAccess(data.access);
    setUser(data.user);
    scheduleRefresh();
  }

  const login = useCallback(async (email, password) => {
    const data = await api.post('/auth/login/', { email, password });
    persistSession(data);
    return data.user;
  }, []);

  const register = useCallback(async (name, email, phone, password, role) => {
    const data = await api.post('/auth/register/', { name, email, phone, password, role });
    return data; // {needs_verification: true} — no session until email verified
  }, []);

  const verifyEmail = useCallback(async (email, code) => {
    const data = await api.post('/auth/verify-email/', { email, code });
    persistSession(data);
    return data.user;
  }, []);

  const resendVerification = useCallback(async (email) => {
    return api.post('/auth/resend-verification/', { email });
  }, []);

  const forgotPassword = useCallback(async (email) => {
    return api.post('/auth/forgot-password/', { email });
  }, []);

  const resetPassword = useCallback(async (tokenValue, password, confirmPassword) => {
    return api.post('/auth/reset-password/', {
      token: tokenValue,
      password,
      confirm_password: confirmPassword
    });
  }, []);

  const loginWithGoogle = useCallback(async (idToken, role) => {
    const data = await api.post('/auth/google/', { idToken, role });
    persistSession(data);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      // Server blacklists the cookie refresh token and clears the cookie.
      await api.post('/auth/logout/', {}, tokenRef.current);
    } catch {
      // best-effort — still clear local state
    }
    clearSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        loading,
        login,
        register,
        verifyEmail,
        resendVerification,
        forgotPassword,
        resetPassword,
        loginWithGoogle,
        logout,
        refreshAccess
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
