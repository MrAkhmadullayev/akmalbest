'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';
import {
  LayoutDashboard, ShoppingCart, Package, Warehouse,
  Users, CreditCard, Wallet, BarChart3,
  Bell, UserCog, Settings, LogOut, ChevronLeft, Menu,
} from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { notificationsService } from '@/services/notifications';
import { debtsService } from '@/services/debts';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Sotuv', href: '/pos', icon: ShoppingCart },
  { name: 'Mahsulotlar', href: '/products', icon: Package },
  { name: 'Mijozlar', href: '/customers', icon: Users },
  { name: 'Qarzlar', href: '/debts', icon: CreditCard },
  { name: 'Xarajatlar', href: '/expenses', icon: Wallet },
  { name: 'Hisobotlar', href: '/reports', icon: BarChart3 },
  { name: 'Bildirishnomalar', href: '/notifications', icon: Bell },
  { name: 'Foydalanuvchilar', href: '/users', icon: UserCog },
  { name: 'Sozlamalar', href: '/settings', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading, logout, hasRole } = useAuth();
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
    enabled: isAuthenticated && hasRole('SUPER_ADMIN', 'ADMIN', 'CASHIER'),
  });

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

  const filteredNav = navigation.filter((item) => {
    // Role-based navigation filtering
    if (item.href === '/users' || item.href === '/settings') {
      return hasRole('SUPER_ADMIN');
    }
    if (item.href === '/expenses' || item.href === '/reports') {
      return hasRole('SUPER_ADMIN', 'ADMIN');
    }
    if (item.href === '/inventory') {
      return hasRole('SUPER_ADMIN', 'ADMIN', 'WAREHOUSE_MANAGER');
    }
    if (item.href === '/pos') {
      return hasRole('SUPER_ADMIN', 'ADMIN', 'CASHIER');
    }
    return true;
  });

  const handleLogout = async () => {
    await logout();
    router.replace('/login');
  };

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
