import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  demoLogin: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('mindtrace_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      if (token) {
        try {
          const me = await api.auth.getMe();
          setUser(me);
        } catch (err) {
          console.warn('[AuthContext] Session expired, logging out:', err);
          logout();
        }
      }
      setLoading(false);
    }
    loadUser();
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.auth.login({ email, password });
    localStorage.setItem('mindtrace_token', res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  };

  const signup = async (email: string, password: string, fullName: string) => {
    const res = await api.auth.signup({ email, password, full_name: fullName });
    localStorage.setItem('mindtrace_token', res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  };

  const demoLogin = async () => {
    const res = await api.auth.demoLogin();
    localStorage.setItem('mindtrace_token', res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = () => {
    localStorage.removeItem('mindtrace_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, demoLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
