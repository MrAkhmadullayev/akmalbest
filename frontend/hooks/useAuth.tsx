'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService } from '@/services/auth';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: string[]) => boolean;
  hasPermission: (module: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setIsLoading(false);
        return;
      }
      const response = await authService.me();
      setUser(response.data);
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (username: string, password: string) => {
    const response = await authService.login({ username, password });
    const { access, refresh, user: userData } = response.data;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setUser(userData as User);
  };

  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch {
      // Ignore
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    }
  };

  const hasRole = (...roles: string[]) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const hasPermission = (module: string) => {
    if (!user) return false;
    // SUPER_ADMIN has access to everything
    if (user.role === 'SUPER_ADMIN') return true;
    
    // Check specific permission if it exists
    if (user.permissions && Object.keys(user.permissions).length > 0) {
      return !!user.permissions[module];
    }

    // Fallback based on roles if permissions are empty (legacy mode)
    const adminModules = ['dashboard', 'products', 'categories', 'customers', 'debts', 'expenses', 'reports', 'notifications', 'pos'];
    const cashierModules = ['dashboard', 'pos', 'products', 'categories', 'customers', 'debts', 'notifications'];
    const warehouseModules = ['dashboard', 'products', 'categories', 'notifications'];

    if (user.role === 'ADMIN') return adminModules.includes(module);
    if (user.role === 'CASHIER') return cashierModules.includes(module);
    if (user.role === 'WAREHOUSE_MANAGER') return warehouseModules.includes(module);

    return false;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        hasRole,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
