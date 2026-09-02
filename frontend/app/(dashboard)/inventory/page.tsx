'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryService } from '@/services/inventory';
import { formatCurrency, getStockStatus, formatDateTime } from '@/lib/utils';
import { Search, Edit, RefreshCw, History, PackageOpen } from 'lucide-react';

export default function InventoryPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'status' | 'transactions'>('status');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Stock edit state
  const [editingItem, setEditingItem] = useState<any>(null);
  const [newQuantity, setNewQuantity] = useState('');
  const [adjustNotes, setAdjustNotes] = useState('');

  // Stock status query
  const { data: inventoryData, isLoading: isInventoryLoading } = useQuery({
    queryKey: ['inventory', search, page],
    queryFn: () => inventoryService.getAll({ search, page: page.toString() }),
    enabled: activeTab === 'status',
  });

  // Transactions query
  const { data: transactionsData, isLoading: isTxLoading } = useQuery({
    queryKey: ['inventory-transactions', search, page],
    queryFn: () => inventoryService.getTransactions({ search, page: page.toString() }),
    enabled: activeTab === 'transactions',
  });

  // Stock adjust mutation
  const adjustMutation = useMutation({
    mutationFn: (payload: { product_id: string; new_quantity: number; notes?: string }) =>
      inventoryService.adjust(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions'] });
      setEditingItem(null);
      setNewQuantity('');
      setAdjustNotes('');
    },
  });

  const handleAdjustSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || newQuantity === '') return;

    adjustMutation.mutate({
      product_id: editingItem.product,
      new_quantity: parseInt(newQuantity),
      notes: adjustNotes,
    });
  };

  const inventoryItems = inventoryData?.data?.results || [];
  const transactions = transactionsData?.data?.results || [];
  const totalCount = activeTab === 'status' ? inventoryData?.data?.count || 0 : transactionsData?.data?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ombor zaxirasi</h1>
          <p className="text-gray-500 mt-1">Zaxira holati va ombor harakatlari logi</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 flex gap-4">
        <button
          onClick={() => {
            setActiveTab('status');
            setPage(1);
          }}
          className={`pb-3 font-semibold text-sm border-b-2 transition-all cursor-pointer ${
            activeTab === 'status'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <PackageOpen size={16} />
            Zaxira holati
          </span>
        </button>
        <button
          onClick={() => {
            setActiveTab('transactions');
            setPage(1);
          }}
          className={`pb-3 font-semibold text-sm border-b-2 transition-all cursor-pointer ${
            activeTab === 'transactions'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <History size={16} />
            Ombor harakatlari
          </span>
        </button>
      </div>

      {/* Filters */}
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
            placeholder="Mahsulot nomi yoki shtrix-kodi bo&apos;yicha qidirish..."
            className="input !pl-10"
          />
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Table list */}
        <div className="card overflow-hidden lg:col-span-2">
          {activeTab === 'status' ? (
            isInventoryLoading ? (
              <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Shtrix-kod</th>
                    <th>Mahsulot</th>
                    <th className="text-center">Miqdor</th>
                    <th>Holat</th>
                    <th className="text-right">Tuzatish</th>
                  </tr>
                </thead>
                <tbody>
                  {inventoryItems.map((item: any) => {
                    const status = getStockStatus(item.stock_status);
                    return (
                      <tr key={item.id}>
                        <td className="font-mono text-xs">{item.product_barcode}</td>
                        <td className="font-medium text-gray-900">{item.product_name}</td>
                        <td className="text-center font-bold text-lg">{item.quantity}</td>
                        <td>
                          <span className={`badge ${status.color}`}>
                            {status.icon} {status.label}
                          </span>
                        </td>
                        <td>
                          <div className="flex justify-end">
                            <button
                              onClick={() => {
                                setEditingItem(item);
                                setNewQuantity(item.quantity.toString());
                              }}
                              className="p-1.5 rounded-lg bg-gray-50 text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                            >
                              <Edit size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {inventoryItems.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center text-gray-400 py-12">
                        Mahsulot topilmadi
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )
          ) : isTxLoading ? (
            <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Vaqt</th>
                  <th>Mahsulot</th>
                  <th>Tur</th>
                  <th className="text-center">Miqdor</th>
                  <th>Mas&apos;ul</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx: any) => (
                  <tr key={tx.id}>
                    <td className="text-xs text-gray-500">{formatDateTime(tx.created_at)}</td>
                    <td>
                      <p className="font-medium text-gray-900">{tx.product_name}</p>
                      <p className="text-xs text-gray-400 font-mono">{tx.product_barcode}</p>
                    </td>
                    <td>
                      <span className="badge bg-gray-100 text-gray-800">
                        {tx.transaction_type}
                      </span>
                    </td>
                    <td className="text-center font-semibold text-gray-900">{tx.quantity}</td>
                    <td className="text-xs">{tx.created_by_name}</td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center text-gray-400 py-12">
                      Ombor harakatlari topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}

          {/* Pagination */}
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

        {/* Tuzatish form panel */}
        {editingItem && activeTab === 'status' && (
          <div className="card p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Zaxirani tuzatish</h2>
              <p className="text-sm text-gray-500 font-medium">{editingItem.product_name}</p>
            </div>

            <form onSubmit={handleAdjustSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Yangi miqdor (dona)
                </label>
                <input
                  type="number"
                  value={newQuantity}
                  onChange={(e) => setNewQuantity(e.target.value)}
                  className="input text-lg font-bold"
                  min={0}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Sababi / Izoh
                </label>
                <textarea
                  value={adjustNotes}
                  onChange={(e) => setAdjustNotes(e.target.value)}
                  className="input min-h-20 text-sm"
                  placeholder="Masalan: inventarizatsiya natijasi..."
                  required
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="btn-secondary flex-1"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={adjustMutation.isPending}
                  className="btn-primary flex-1"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
