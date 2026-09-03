'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsService } from '@/services/reports';
import { salesService } from '@/services/sales';
import { formatCurrency, formatDateTime, getStockStatus, getPaymentMethodLabel } from '@/lib/utils';
import {
  TrendingUp, ShoppingCart, Wallet, AlertTriangle,
  CreditCard, Package, PackageX, ArrowUpRight,
  Clock, Eye, XCircle
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => reportsService.getDashboard(),
    refetchInterval: 60000,
    retry: (failureCount, err: any) => {
      if (err?.response?.status === 403) return false;
      return failureCount < 1;
    },
  });

  const dashboard = data?.data;
  const queryClient = useQueryClient();

  const cancelMutation = useMutation({
    mutationFn: (saleId: string) => salesService.cancel(saleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      alert(err?.response?.data?.message || "Savdoni bekor qilishda xatolik yuz berdi.");
    },
  });

  const handleCancel = (saleId: string, saleNumber: string) => {
    if (confirm(`"${saleNumber}" raqamli savdoni bekor qilmoqchimisiz? Barcha mahsulotlar omborga qaytariladi.`)) {
      cancelMutation.mutate(saleId);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <div className="card p-8 text-center">
          <p className="text-red-500 font-semibold text-lg">Ma&apos;lumotlarni yuklashda xatolik!</p>
          <p className="text-gray-400 mt-2">
            {(error as any)?.response?.status === 403
              ? "Sizda Dashboard bo'limiga ruxsat yo'q. Administrator bilan bog'laning."
              : "Server bilan aloqa uzildi. Sahifani qayta yuklang."}
          </p>
        </div>
      </div>
    );
  }

  const stats = [
    {
      label: "Bugungi savdo (Umumiy)",
      value: formatCurrency(dashboard?.today_sales_total || '0'),
      sub: `${dashboard?.today_sales_count || 0} ta savdo`,
      icon: ShoppingCart,
      color: 'bg-indigo-50 text-indigo-600',
      iconBg: 'bg-indigo-100',
    },
    {
      label: "Savdo (Naqd)",
      value: formatCurrency(dashboard?.today_cash_sales || '0'),
      icon: Wallet,
      color: 'bg-emerald-50 text-emerald-600',
      iconBg: 'bg-emerald-100',
    },
    {
      label: "Savdo (Karta)",
      value: formatCurrency(dashboard?.today_card_sales || '0'),
      icon: CreditCard,
      color: 'bg-blue-50 text-blue-600',
      iconBg: 'bg-blue-100',
    },
    {
      label: "Savdo (Nasiya)",
      value: formatCurrency(dashboard?.today_debt_sales || '0'),
      icon: Clock,
      color: 'bg-orange-50 text-orange-600',
      iconBg: 'bg-orange-100',
    },
    {
      label: "Bugungi foyda",
      value: formatCurrency(dashboard?.today_profit || '0'),
      icon: TrendingUp,
      color: 'bg-emerald-50 text-emerald-600',
      iconBg: 'bg-emerald-100',
    },
    {
      label: "Bugungi xarajat",
      value: formatCurrency(dashboard?.today_expenses || '0'),
      icon: Wallet,
      color: 'bg-orange-50 text-orange-600',
      iconBg: 'bg-orange-100',
    },
    {
      label: "Jami qarz",
      value: formatCurrency(dashboard?.total_debt || '0'),
      sub: `${dashboard?.overdue_count || 0} ta muddati o'tgan`,
      icon: CreditCard,
      color: 'bg-red-50 text-red-600',
      iconBg: 'bg-red-100',
    },
    {
      label: "Muddati o'tgan qarz",
      value: formatCurrency(dashboard?.overdue_debt || '0'),
      icon: AlertTriangle,
      color: 'bg-red-50 text-red-600',
      iconBg: 'bg-red-100',
    },
    {
      label: "Kam qolgan",
      value: `${dashboard?.low_stock_count || 0} ta`,
      icon: Package,
      color: 'bg-amber-50 text-amber-600',
      iconBg: 'bg-amber-100',
    },
    {
      label: "Jami mahsulotlar",
      value: `${dashboard?.total_products || 0} ta`,
      icon: Package,
      color: 'bg-blue-50 text-blue-600',
      iconBg: 'bg-blue-100',
    },
    {
      label: "Ombordagi Nasiya (Qarz)",
      value: formatCurrency(dashboard?.inventory_debt_value || '0'),
      icon: Package,
      color: 'bg-purple-50 text-purple-600',
      iconBg: 'bg-purple-100',
    },
    {
      label: "Ombordagi Naqd",
      value: formatCurrency(dashboard?.inventory_cash_value || '0'),
      icon: Package,
      color: 'bg-teal-50 text-teal-600',
      iconBg: 'bg-teal-100',
    },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Bugungi umumiy ko&apos;rsatkichlar</p>
        </div>
        <Link href="/pos" className="btn-primary">
          <ShoppingCart size={18} />
          Yangi sotuv
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{stat.value}</p>
                  {stat.sub && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{stat.sub}</p>}
                </div>
                <div className={`p-2.5 rounded-xl ${stat.iconBg}`}>
                  <Icon size={20} className={stat.color.split(' ')[1]} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Sales */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">So&apos;nggi savdolar</h2>
            <Link href="/sales" className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1">
              Barchasi <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Raqam</th>
                  <th>Kassir</th>
                  <th>Summa</th>
                  <th>Usul</th>
                  <th className="text-right">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {dashboard?.recent_sales?.map((sale) => (
                  <tr key={sale.id}>
                    <td className="font-medium text-indigo-600">
                      <Link href={`/sales/${sale.id}`}>{sale.sale_number}</Link>
                    </td>
                    <td>{sale.cashier}</td>
                    <td className="font-semibold">{formatCurrency(sale.total)}</td>
                    <td>
                      <span className="badge bg-gray-100 text-gray-700">
                        {getPaymentMethodLabel(sale.payment_method)}
                      </span>
                    </td>
                    <td>
                      <div className="flex justify-end gap-2">
                        <Link href={`/sales/${sale.id}`} className="p-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded text-blue-500" title="Ko'rish">
                          <Eye size={18} />
                        </Link>
                        {sale.status !== 'CANCELLED' && (
                          <button
                            onClick={() => handleCancel(sale.id, sale.sale_number)}
                            disabled={cancelMutation.isPending}
                            className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-red-400 hover:text-red-600 cursor-pointer"
                            title="Bekor qilish"
                          >
                            <XCircle size={18} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {(!dashboard?.recent_sales || dashboard.recent_sales.length === 0) && (
                  <tr><td colSpan={5} className="text-center text-gray-400 py-8">Savdolar mavjud emas</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Low Stock */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">Kam qolgan mahsulotlar</h2>
            <Link href="/inventory" className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1">
              Barchasi <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mahsulot</th>
                  <th>Shtrix-kod</th>
                  <th>Qoldiq</th>
                  <th>Holat</th>
                </tr>
              </thead>
              <tbody>
                {dashboard?.low_stock_products?.map((p) => {
                  const status = getStockStatus(p.stock_status);
                  return (
                    <tr key={p.id}>
                      <td className="font-medium">{p.name}</td>
                      <td className="text-gray-500 text-xs font-mono">{p.barcode}</td>
                      <td className="font-semibold">{p.current_stock}</td>
                      <td>
                        <span className={`badge ${status.color}`}>
                          {status.icon} {status.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
                {(!dashboard?.low_stock_products || dashboard.low_stock_products.length === 0) && (
                  <tr><td colSpan={4} className="text-center text-gray-400 py-8">Barcha mahsulotlar yetarli</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Overdue Debts */}
        <div className="card lg:col-span-2">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">Muddati o&apos;tgan qarzlar</h2>
            <Link href="/debts" className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1">
              Barchasi <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mijoz</th>
                  <th>Telefon</th>
                  <th>Qoldiq</th>
                  <th>Muddat</th>
                </tr>
              </thead>
              <tbody>
                {dashboard?.overdue_debts?.map((d) => (
                  <tr key={d.id}>
                    <td className="font-medium">{d.customer}</td>
                    <td className="text-gray-500">{d.phone}</td>
                    <td className="font-semibold text-red-600">{formatCurrency(d.remaining_amount)}</td>
                    <td className="text-red-500">{d.due_date}</td>
                  </tr>
                ))}
                {(!dashboard?.overdue_debts || dashboard.overdue_debts.length === 0) && (
                  <tr><td colSpan={4} className="text-center text-gray-400 py-8">Muddati o&apos;tgan qarzlar yo&apos;q</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
