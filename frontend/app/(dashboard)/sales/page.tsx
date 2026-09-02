'use client';

import { useQuery } from '@tanstack/react-query';
import { salesService } from '@/services/sales';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Search, Eye } from 'lucide-react';
import { useState } from 'react';
import Link from 'next/link';

export default function SalesPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['sales', search, page],
    queryFn: () => salesService.getAll({ search, page: page.toString() }),
  });

  const sales = data?.data?.results || [];
  const summary = (data?.data as any)?.summary || {
    total_sales: '0',
    cash_sales: '0',
    card_sales: '0',
    debt_sales: '0',
  };
  const totalCount = data?.data?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Savdolar tarixi</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Barcha sotilgan tovarlar va to&apos;lovlar ro&apos;yxati</p>
      </div>

      <div className="card p-4 flex gap-4">
        <div className="flex-1 relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            <Search size={18} />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Savdo raqami yoki mijoz nomi bo&apos;yicha qidirish..."
            className="input !pl-10"
          />
        </div>
      </div>

      {!isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-4 bg-indigo-50 dark:bg-indigo-900/20 border-indigo-100 dark:border-indigo-800/30">
            <p className="text-sm text-indigo-600 dark:text-indigo-400 font-medium mb-1">Umumiy savdo</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(summary.total_sales)}</p>
          </div>
          <div className="card p-4 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-800/30">
            <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium mb-1">Naqd</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(summary.cash_sales)}</p>
          </div>
          <div className="card p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/30">
            <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">Karta</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(summary.card_sales)}</p>
          </div>
          <div className="card p-4 bg-orange-50 dark:bg-orange-900/20 border-orange-100 dark:border-orange-800/30">
            <p className="text-sm text-orange-600 dark:text-orange-400 font-medium mb-1">Nasiya</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(summary.debt_sales)}</p>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Raqam</th>
                <th>Sana</th>
                <th>Kassir</th>
                <th>Mijoz</th>
                <th>Jami summa</th>
                <th>To&apos;lov usuli</th>
                <th>Holat</th>
                <th className="text-right">Ko&apos;rish</th>
              </tr>
            </thead>
            <tbody>
              {sales.map((sale) => (
                <tr key={sale.id}>
                  <td className="font-semibold text-indigo-600">
                    <Link href={`/sales/${sale.id}`}>{sale.sale_number}</Link>
                  </td>
                  <td>{formatDate(sale.created_at)}</td>
                  <td>{sale.cashier_name}</td>
                  <td>{sale.customer_name || '-'}</td>
                  <td className="font-bold">{formatCurrency(sale.total)}</td>
                  <td>
                    <span className="badge bg-gray-100 text-gray-800">{sale.payment_method}</span>
                  </td>
                  <td>
                    <span className={`badge ${
                      sale.status === 'COMPLETED' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                    }`}>
                      {sale.status}
                    </span>
                  </td>
                  <td>
                    <div className="flex justify-end">
                      <Link href={`/sales/${sale.id}`} className="p-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded">
                        <Eye size={18} />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
              {sales.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-gray-400 py-12">
                    Savdolar topilmadi
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-sm text-gray-500">Jami {totalCount} ta savdo</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="btn-secondary btn-sm"
              >
                Oldingi
              </button>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page === totalPages}
                className="btn-secondary btn-sm"
              >
                Keyingi
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
