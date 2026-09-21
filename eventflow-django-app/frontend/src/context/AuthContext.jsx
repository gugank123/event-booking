import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('eventflow_access'));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadUser() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const data = await api.get('/auth/me/', token);
        if (!cancelled) setUser(data.user);
      } catch (err) {
        if (!cancelled) {
          setToken(null);
          localStorage.removeItem('eventflow_access');
          localStorage.removeItem('eventflow_refresh');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  function persistSession(data) {
    localStorage.setItem('eventflow_access', data.access);
    localStorage.setItem('eventflow_refresh', data.refresh);
    setToken(data.access);
    setUser(data.user);
  }

  const login = useCallback(async (email, password) => {
    const data = await api.post('/auth/login/', { email, password });
    persistSession(data);
    return data.user;
  }, []);

  const register = useCallback(async (name, email, password, role) => {
    const data = await api.post('/auth/register/', { name, email, password, role });
    persistSession(data);
    return data.user;
  }, []);

  const loginWithGoogle = useCallback(async (idToken, role) => {
    const data = await api.post('/auth/google/', { idToken, role });
    persistSession(data);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('eventflow_access');
    localStorage.removeItem('eventflow_refresh');
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
