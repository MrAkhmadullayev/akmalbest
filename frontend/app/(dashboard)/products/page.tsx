'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsService, categoriesService } from '@/services/products';
import { formatCurrency, getStockStatus } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { Search, Plus, Edit, Trash2, Eye } from 'lucide-react';
import Link from 'next/link';

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const [showInactive, setShowInactive] = useState(false);
  const { user } = useAuth();
  const isAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'ADMIN';

  const [stockModal, setStockModal] = useState<{ isOpen: boolean; product: any }>({ isOpen: false, product: null });
  const [stockData, setStockData] = useState({ quantity: 0, purchase_price: 0, payment_method: 'CASH', notes: '' });

  const { data: categoriesData } = useQuery({
    queryKey: ['categories-list'],
    queryFn: () => categoriesService.getAll({ page_size: '100' }),
  });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['products', search, category, page, showInactive],
    queryFn: () => {
      const params: any = {
        search,
        category,
        page: page.toString(),
      };
      if (!showInactive) {
        params.is_active = 'true';
      }
      return productsService.getAll(params);
    },
    retry: (failureCount, err: any) => {
      // 403 (ruxsat yo'q) xatosini qayta urinmaymiz
      if (err?.response?.status === 403) return false;
      return failureCount < 1;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => productsService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || "Mahsulotni o'chirishda xatolik yuz berdi.";
      alert(msg);
    }
  });

  const addStockMutation = useMutation({
    mutationFn: (data: any) => productsService.addStock(stockModal.product.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setStockModal({ isOpen: false, product: null });
    },
  });

  const handleDelete = (id: string) => {
    if (confirm('Haqiqatan ham ushbu mahsulotni o\'chirmoqchimisiz?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleOpenStockModal = (product: any) => {
    setStockModal({ isOpen: true, product });
    setStockData({ quantity: 0, purchase_price: product.purchase_price, payment_method: 'CASH', notes: 'Zaxira to\'ldirildi' });
  };

  const handleStockSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (stockData.quantity <= 0) return;
    addStockMutation.mutate(stockData);
  };

  const products = data?.data?.results || [];
  const totalCount = data?.data?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mahsulotlar</h1>
          <p className="text-gray-500 mt-1">Barcha mahsulotlar ro&apos;yxati va boshqaruvi</p>
        </div>
        <Link href="/products/new" className="btn-primary">
          <Plus size={18} />
          Yangi mahsulot
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-col md:flex-row gap-4">
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
            placeholder="Nomi yoki shtrix-kodi bo&apos;yicha qidirish..."
            className="input !pl-10"
          />
        </div>
        <div className="w-full md:w-64 flex-shrink-0">
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
            className="input"
          >
            <option value="">Barcha kategoriyalar</option>
            {categoriesData?.data?.results?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 px-2">
          <input
            type="checkbox"
            id="showInactive"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-600 cursor-pointer"
          />
          <label htmlFor="showInactive" className="text-sm text-gray-700 cursor-pointer select-none">
            O'chirilganlarni ham ko'rsatish
          </label>
        </div>
      </div>

      {/* Products Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
        ) : isError ? (
          <div className="p-8 text-center text-red-500">
            <p className="font-semibold">Ma&apos;lumotlarni yuklashda xatolik!</p>
            <p className="text-sm text-gray-400 mt-1">
              {(error as any)?.response?.status === 403
                ? "Sizda bu bo'limga ruxsat yo'q. Administrator bilan bog'laning."
                : "Server bilan aloqa uzildi. Sahifani qayta yuklang."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Shtrix-kod</th>
                  <th>Mahsulot nomi</th>
                  <th>Kategoriya</th>
                  <th>Brend</th>
                  <th>Hajmi</th>
                  <th>Sotib olish</th>
                  <th>Sotish</th>
                  <th>Zaxira</th>
                  <th>Holat</th>
                  <th className="text-right">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const status = getStockStatus(p.stock_status);
                  return (
                    <tr key={p.id} className={!p.is_active ? 'opacity-50 bg-gray-50' : ''}>
                      <td className="font-mono text-xs font-semibold text-gray-600">
                        {p.barcode}
                      </td>
                      <td className="font-medium text-gray-900">
                        {p.name}
                        {!p.is_active && (
                          <span className="ml-2 inline-flex items-center rounded-md bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
                            Faol emas
                          </span>
                        )}
                      </td>
                      <td>{p.category_name}</td>
                      <td>{p.brand_name || '-'}</td>
                      <td>
                        {p.volume} {p.unit}
                      </td>
                      <td className="font-semibold text-gray-700">
                        {formatCurrency(p.purchase_price)}
                      </td>
                      <td className="font-semibold text-indigo-600">
                        {formatCurrency(p.selling_price)}
                      </td>
                      <td className="font-bold">{p.current_stock}</td>
                      <td>
                        <span className={`badge ${status.color}`}>
                          {status.icon} {status.label}
                        </span>
                      </td>
                      <td>
                        <div className="flex justify-end gap-2">
                          <Link
                            href={`/products/${p.id}`}
                            className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer"
                          >
                            <Eye size={18} />
                          </Link>
                          <button
                            onClick={() => handleOpenStockModal(p)}
                            className="p-1 text-green-500 hover:text-green-700 cursor-pointer bg-green-50 rounded"
                            title="Kirim qilish (Zaxira qo'shish)"
                          >
                            <Plus size={18} />
                          </button>
                          <Link
                            href={`/products/${p.id}/edit`}
                            className="p-1 text-blue-400 hover:text-blue-600 cursor-pointer"
                          >
                            <Edit size={18} />
                          </Link>
                          {isAdmin && (
                            <button
                              onClick={() => handleDelete(p.id)}
                              className="p-1 text-red-400 hover:text-red-600 cursor-pointer"
                            >
                              <Trash2 size={18} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {products.length === 0 && (
                  <tr>
                    <td colSpan={10} className="text-center text-gray-400 py-12">
                      Mahsulotlar topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Jami {totalCount} tadan {(page - 1) * pageSize + 1}-
              {Math.min(page * pageSize, totalCount)} gacha ko&apos;rsatilmoqda
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

      {/* Add Stock Modal */}
      {stockModal.isOpen && stockModal.product && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b">
              <h2 className="text-lg font-bold">Kirim qilish</h2>
              <p className="text-sm text-gray-500">{stockModal.product.name} ({stockModal.product.barcode})</p>
            </div>
            <form onSubmit={handleStockSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Miqdor (Soni)</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={stockData.quantity || ''}
                  onChange={(e) => setStockData({ ...stockData, quantity: parseInt(e.target.value) || 0 })}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Kelish narxi (UZS)</label>
                <input
                  type="number"
                  min="0"
                  required
                  value={stockData.purchase_price || ''}
                  onChange={(e) => setStockData({ ...stockData, purchase_price: parseFloat(e.target.value) || 0 })}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">To'lov turi</label>
                <select
                  value={stockData.payment_method}
                  onChange={(e) => setStockData({ ...stockData, payment_method: e.target.value })}
                  className="input"
                >
                  <option value="CASH">Naqd (To'langan)</option>
                  <option value="DEBT">Nasiya (Qarz)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Izoh</label>
                <input
                  type="text"
                  value={stockData.notes}
                  onChange={(e) => setStockData({ ...stockData, notes: e.target.value })}
                  className="input"
                />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setStockModal({ isOpen: false, product: null })}
                  className="btn-secondary"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={addStockMutation.isPending || stockData.quantity <= 0}
                  className="btn-primary"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
