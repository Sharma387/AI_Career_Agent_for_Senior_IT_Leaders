import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User } from '../types';
import { api } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  profileId: number | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  setProfileId: (id: number) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [profileId, setProfileId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    try {
      const response = await api.auth.me();
      setUser(response.data as User);
      try {
        const profileRes = await api.profile.getMyProfile();
        if (profileRes.data.profile) {
          setProfileId(profileRes.data.profile.id);
        }
      } catch {
        // Profile may not exist yet
      }
    } catch {
      setToken(null);
      setUser(null);
      setProfileId(null);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadUser();
    } else {
      setLoading(false);
    }
  }, [token, loadUser]);

  const login = async (email: string, password: string) => {
    const response = await api.auth.login({ email, password });
    const newToken = response.data.access_token;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    await loadUser();
  };

  const register = async (email: string, password: string, fullName: string) => {
    const response = await api.auth.register({ email, password, full_name: fullName });
    const newToken = response.data.access_token;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setProfileId(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, profileId, setProfileId, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
