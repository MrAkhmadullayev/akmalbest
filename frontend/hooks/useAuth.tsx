'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService } from '@/services/auth';
import type { ModuleKey, User } from '@/types';
import { DEFAULT_ROLE_MODULES } from '@/lib/permissions';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: string[]) => boolean;
  hasPermission: (module: ModuleKey) => boolean;
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
    } catch (err: any) {
      // Faqat autentifikatsiya xatosida (401) tokenlarni tozalaymiz.
      // Tarmoq xatosi yoki boshqa server xatosi (500, 403) bo'lsa,
      // tokenlar saqlanib qoladi — foydalanuvchi sahifani qayta
      // yuklashi mumkin va keyingi urinishda ishlashi mumkin.
      const status = err?.response?.status;
      if (status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
      } else {
        // Token hali amal qilishi mumkin — keshlanmiš user'ni sinab ko'ramiz
        // yoki shunchaki null qilib qo'yamiz (login'ga yo'naltiradi)
        // Lekin tokenlarni O'CHIRMAYMIZ
        setUser(null);
      }
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

  const hasRole = useCallback(
    (...roles: string[]) => (user ? roles.includes(user.role) : false),
    [user],
  );

  // DIQQAT: bu faqat MENYUNI yashiradi. Haqiqiy to'siq backend'da
  // (apps/accounts/permissions.py -> HasModulePermission).
  const hasPermission = useCallback(
    (module: ModuleKey) => {
      if (!user) return false;
      if (user.role === 'SUPER_ADMIN') return true;

      // Backend rol standartlari va bekor qilishlarni allaqachon birlashtirib
      // yuborgan — shuni to'g'ridan to'g'ri o'qiymiz.
      const effective = user.effective_permissions;
      if (effective && Object.keys(effective).length > 0) {
        return effective[module] === true;
      }

      // Zaxira: eski backend javobi.
      const overrides = user.permissions;
      if (overrides && module in overrides) {
        return overrides[module] === true;
      }
      return (DEFAULT_ROLE_MODULES[user.role] ?? []).includes(module);
    },
    [user],
  );

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
