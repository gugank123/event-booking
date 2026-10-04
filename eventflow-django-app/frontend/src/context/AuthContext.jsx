import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('eventflow_access'));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimer = useRef(null);

  function clearSession() {
    localStorage.removeItem('eventflow_access');
    localStorage.removeItem('eventflow_refresh');
    setToken(null);
    setUser(null);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }

  const refreshAccess = useCallback(async () => {
    const refresh = localStorage.getItem('eventflow_refresh');
    if (!refresh) return null;
    try {
      const data = await api.post('/auth/token/refresh/', { refresh });
      localStorage.setItem('eventflow_access', data.access);
      if (data.refresh) localStorage.setItem('eventflow_refresh', data.refresh);
      setToken(data.access);
      scheduleRefresh();
      return data.access;
    } catch {
      clearSession();
      return null;
    }
  }, []);

  function scheduleRefresh() {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    // Access tokens live 60 min — refresh silently at 50 min.
    refreshTimer.current = setTimeout(() => refreshAccess(), 50 * 60 * 1000);
  }

  useEffect(() => {
    let cancelled = false;
    async function loadUser(activeToken) {
      if (!activeToken) {
        setLoading(false);
        return;
      }
      try {
        const data = await api.get('/auth/me/', activeToken);
        if (!cancelled) {
          setUser(data.user);
          scheduleRefresh();
        }
      } catch (err) {
        // Access may have expired — try the refresh token once before giving up.
        if (!cancelled) {
          const next = await refreshAccess();
          if (next) {
            try {
              const data = await api.get('/auth/me/', next);
              if (!cancelled) setUser(data.user);
            } catch {
              if (!cancelled) clearSession();
            }
          } else if (!cancelled) {
            clearSession();
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadUser(token);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function persistSession(data) {
    localStorage.setItem('eventflow_access', data.access);
    localStorage.setItem('eventflow_refresh', data.refresh);
    setToken(data.access);
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
    const refresh = localStorage.getItem('eventflow_refresh');
    try {
      if (token) await api.post('/auth/logout/', { refresh }, token);
    } catch {
      // best-effort — still clear local state
    }
    clearSession();
  }, [token]);

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
