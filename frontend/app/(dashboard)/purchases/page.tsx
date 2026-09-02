'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { purchasesService } from '@/services/suppliers';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Search, Plus } from 'lucide-react';
import Link from 'next/link';

export default function PurchasesPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['purchases', search, page],
    queryFn: () => purchasesService.getAll({ search, page: page.toString() }),
  });

  const purchases = (data?.data as any)?.results || [];
  const totalCount = (data?.data as any)?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Xaridlar (Omborga kirim)</h1>
          <p className="text-gray-500 mt-1">Yetkazib beruvchilardan xarid qilingan mahsulotlar tarixi</p>
        </div>
        <Link href="/purchases/new" className="btn-primary">
          <Plus size={18} />
          Yangi kirim xaridi
        </Link>
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
            placeholder="Faktura raqami yoki yetkazib beruvchi bo&apos;yicha qidirish..."
            className="input !pl-10"
          />
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sana</th>
                  <th>Faktura (Invoice)</th>
                  <th>Yetkazib beruvchi</th>
                  <th>Jami summa</th>
                  <th>Mas&apos;ul</th>
                  <th>Izoh</th>
                </tr>
              </thead>
              <tbody>
                {purchases.map((p: any) => (
                  <tr key={p.id}>
                    <td>{formatDate(p.purchase_date)}</td>
                    <td className="font-semibold text-gray-700">{p.invoice_number || '-'}</td>
                    <td className="font-medium text-gray-900">{p.supplier_name}</td>
                    <td className="font-bold text-indigo-600">{formatCurrency(p.total)}</td>
                    <td>{p.created_by_name}</td>
                    <td className="text-gray-500 max-w-xs truncate">{p.notes || '-'}</td>
                  </tr>
                ))}
                {purchases.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center text-gray-400 py-12">
                      Xaridlar topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Jami {totalCount} tadan {(page - 1) * pageSize + 1}-
              {Math.min(page * pageSize, totalCount)} gacha
            </span>
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
