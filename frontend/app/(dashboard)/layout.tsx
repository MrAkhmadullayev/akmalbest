'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';
import {
  LayoutDashboard, ShoppingCart, Package,
  Users, CreditCard, Wallet, BarChart3,
  Bell, UserCog, Settings, LogOut, ChevronLeft, Menu, Tags,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { notificationsService } from '@/services/notifications';
import { debtsService } from '@/services/debts';
import type { ModuleKey } from '@/types';

type NavItem = {
  name: string;
  href: string;
  icon: LucideIcon;
  permission: ModuleKey;
};

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, permission: 'dashboard' },
  { name: 'Sotuv', href: '/pos', icon: ShoppingCart, permission: 'pos' },
  { name: 'Mahsulotlar', href: '/products', icon: Package, permission: 'products' },
  { name: 'Kategoriyalar', href: '/categories', icon: Tags, permission: 'categories' },
  { name: 'Mijozlar', href: '/customers', icon: Users, permission: 'customers' },
  { name: 'Qarzlar', href: '/debts', icon: CreditCard, permission: 'debts' },
  { name: 'Xarajatlar', href: '/expenses', icon: Wallet, permission: 'expenses' },
  { name: 'Hisobotlar', href: '/reports', icon: BarChart3, permission: 'reports' },
  { name: 'Bildirishnomalar', href: '/notifications', icon: Bell, permission: 'notifications' },
  { name: 'Foydalanuvchilar', href: '/users', icon: UserCog, permission: 'users' },
  { name: 'Sozlamalar', href: '/settings', icon: Settings, permission: 'settings' },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading, logout, hasPermission } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    // Mobil qurilmalarda yon panelni yopiq holatda boshlash
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: () => notificationsService.getUnreadCount(),
    refetchInterval: 30000,
    enabled: isAuthenticated,
  });

  const { data: debtsNotifyData } = useQuery({
    queryKey: ['debts-notifications'],
    queryFn: () => debtsService.getNotifications(),
    refetchInterval: 60000,
    enabled: isAuthenticated && hasPermission('debts'),
  });

  const allowedNav = useMemo(
    () => navigation.filter((item) => hasPermission(item.permission)),
    [hasPermission],
  );

  // Xavfsizlik: foydalanuvchi o'ziga ruxsat berilmagan sahifaga URL orqali
  // kirmoqchi bo'lsa, ruxsati bor birinchi bo'limga qaytaramiz.
  // Hech qanday ruxsati bo'lmasa REDIRECT QILMAYMIZ — aks holda cheksiz
  // yo'naltirish sikliga tushib qolardi; o'rniga xabar ko'rsatiladi.
  useEffect(() => {
    if (!isAuthenticated || isLoading) return;

    const currentNav = navigation.find((nav) => pathname.startsWith(nav.href));
    if (!currentNav || hasPermission(currentNav.permission)) return;

    const fallback = allowedNav[0];
    if (fallback && fallback.href !== pathname) {
      router.replace(fallback.href);
    }
  }, [pathname, isAuthenticated, isLoading, hasPermission, allowedNav, router]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const filteredNav = allowedNav;

  const handleLogout = async () => {
    await logout();
    router.replace('/login');
  };

  if (filteredNav.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
        <div className="card p-8 max-w-md text-center space-y-4">
          <h1 className="text-lg font-bold text-gray-900">Ruxsat berilmagan</h1>
          <p className="text-sm text-gray-500">
            Hisobingizga hech qanday bo'lim biriktirilmagan. Administratorga
            murojaat qiling.
          </p>
          <button onClick={handleLogout} className="btn-primary w-full">
            Chiqish
          </button>
        </div>
      </div>
    );
  }

  const unreadCount = unreadData?.data?.count || 0;
  const dueDebtsCount = (debtsNotifyData?.data as any)?.due_debts_count || 0;

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 overflow-hidden transition-colors duration-200">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col transition-all duration-300 ease-in-out flex-shrink-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-100 dark:border-gray-800">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <span className="text-xl">🍷</span>
              <span className="font-bold text-lg text-gray-900 dark:text-white">Alkagol</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors cursor-pointer"
          >
            {sidebarOpen ? <ChevronLeft size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {filteredNav.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <Icon size={20} className={isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300'} />
                {sidebarOpen && <span>{item.name}</span>}
                {item.href === '/notifications' && unreadCount > 0 && (
                  <span className={`${sidebarOpen ? 'ml-auto' : 'absolute -top-1 -right-1'} bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center`}>
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
                {item.href === '/debts' && dueDebtsCount > 0 && (
                  <span className={`${sidebarOpen ? 'ml-auto' : 'absolute -top-1 -right-1'} bg-orange-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center`} title="Muddati o'tgan qarzlar">
                    !
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User info */}
        <div className="border-t border-gray-100 dark:border-gray-800 p-3">
          <div className={`flex items-center ${sidebarOpen ? 'gap-3' : 'justify-center'}`}>
            <div className="w-9 h-9 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-indigo-600 dark:text-indigo-400 font-semibold text-sm">
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </span>
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.role}</p>
              </div>
            )}
            {sidebarOpen && (
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors cursor-pointer"
                title="Chiqish"
              >
                <LogOut size={18} />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
