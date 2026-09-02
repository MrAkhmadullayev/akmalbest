'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { suppliersService, purchasesService } from '@/services/suppliers';
import { productsService } from '@/services/products';
import { formatCurrency } from '@/lib/utils';
import { ArrowLeft, Save, Plus, Trash2, Search } from 'lucide-react';
import Link from 'next/link';

interface NewPurchaseItem {
  product_id: string;
  name: string;
  barcode: string;
  quantity: number;
  purchase_price: number;
  payment_method: string;
}

export default function NewPurchasePage() {
  const router = useRouter();
  const [supplier, setSupplier] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');

  // Cart items
  const [items, setItems] = useState<NewPurchaseItem[]>([]);
  const [search, setSearch] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  // Queries
  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers-list'],
    queryFn: () => suppliersService.getAll({ page_size: '100' }),
  });

  const { data: searchResults } = useQuery({
    queryKey: ['purchase-product-search', search],
    queryFn: () => productsService.getAll({ search, page_size: '10' }),
    enabled: search.length > 1,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (payload: any) => purchasesService.create(payload),
    onSuccess: () => {
      router.push('/purchases');
    },
  });

  const addItem = (product: any) => {
    const existing = items.find((i) => i.product_id === product.id);
    if (existing) return;

    setItems([
      ...items,
      {
        product_id: product.id,
        name: product.name,
        barcode: product.barcode,
        quantity: 10,
        purchase_price: parseFloat(product.purchase_price),
        payment_method: 'CASH',
      },
    ]);
    setSearch('');
    setShowSearch(false);
  };

  const updateItemQty = (index: number, val: number) => {
    if (val < 1) return;
    const next = [...items];
    next[index].quantity = val;
    setItems(next);
  };

  const updateItemPrice = (index: number, val: number) => {
    if (val < 0) return;
    const next = [...items];
    next[index].purchase_price = val;
    setItems(next);
  };

  const updateItemPaymentMethod = (index: number, val: string) => {
    const next = [...items];
    next[index].payment_method = val;
    setItems(next);
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplier || items.length === 0) return;

    createMutation.mutate({
      supplier,
      invoice_number: invoiceNumber,
      purchase_date: purchaseDate,
      notes,
      items: items.map((i) => ({
        product_id: i.product_id,
        quantity: i.quantity,
        purchase_price: i.purchase_price,
        payment_method: i.payment_method,
      })),
    });
  };

  const grandTotal = items.reduce((sum, i) => sum + i.quantity * i.purchase_price, 0);

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl">
      <div className="flex items-center gap-4">
        <Link href="/purchases" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Yangi xarid kirimi</h1>
          <p className="text-gray-500 mt-0.5">Omborga mahsulot qabul qilish hujjatini rasmiylashtiring</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Yetkazib beruvchi</label>
            <select
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              className="input"
              required
            >
              <option value="">Tanlang...</option>
              {suppliersData?.data?.results?.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Faktura (Invoice) raqami</label>
            <input
              type="text"
              value={invoiceNumber}
              onChange={(e) => setInvoiceNumber(e.target.value)}
              className="input"
              placeholder="Masalan: INV-2024-001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Kirim sanasi</label>
            <input
              type="date"
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
              className="input"
              required
            />
          </div>
        </div>

        {/* Product selector search */}
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Mahsulotlar ro&apos;yxati</h2>
            <button
              type="button"
              onClick={() => setShowSearch(!showSearch)}
              className="btn-secondary btn-sm"
            >
              <Plus size={16} /> Mahsulot qo&apos;shish
            </button>
          </div>

          {showSearch && (
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Mahsulot nomi yoki shtrix-kodi..."
                className="input"
                autoFocus
              />
              {searchResults?.data?.results && searchResults.data.results.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-white border rounded-lg shadow-xl mt-1 z-50 max-h-48 overflow-y-auto">
                  {searchResults.data.results.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => addItem(p)}
                      className="w-full px-4 py-2.5 text-left hover:bg-gray-50 border-b last:border-0 text-sm flex items-center justify-between cursor-pointer"
                    >
                      <div>
                        <p className="font-medium">{p.name}</p>
                        <p className="text-xs text-gray-400 font-mono">{p.barcode}</p>
                      </div>
                      <span className="font-semibold text-gray-600">{formatCurrency(p.purchase_price)}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Items Table */}
          {items.length === 0 ? (
            <p className="text-center text-gray-400 py-8">Hali mahsulotlar qo&apos;shilmagan</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mahsulot</th>
                    <th className="text-center">Miqdor</th>
                    <th className="text-center">Sotib olish narxi (UZS)</th>
                    <th className="text-center">To'lov turi</th>
                    <th className="text-right">Jami</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => (
                    <tr key={item.product_id}>
                      <td>
                        <p className="font-medium text-gray-900">{item.name}</p>
                        <p className="text-xs text-gray-400 font-mono">{item.barcode}</p>
                      </td>
                      <td>
                        <input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => updateItemQty(idx, parseInt(e.target.value) || 0)}
                          className="w-20 text-center border rounded py-1 mx-auto block"
                          min={1}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          value={item.purchase_price}
                          onChange={(e) => updateItemPrice(idx, parseFloat(e.target.value) || 0)}
                          className="w-32 text-center border rounded py-1 mx-auto block font-semibold"
                          min={0}
                        />
                      </td>
                      <td>
                        <select
                          value={item.payment_method}
                          onChange={(e) => updateItemPaymentMethod(idx, e.target.value)}
                          className="border rounded py-1.5 px-2 text-sm mx-auto block bg-white"
                        >
                          <option value="CASH">Naqd</option>
                          <option value="DEBT">Nasiya</option>
                        </select>
                      </td>
                      <td className="text-right font-bold">
                        {formatCurrency(item.quantity * item.purchase_price)}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => removeItem(idx)}
                          className="text-red-400 hover:text-red-600 cursor-pointer"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Notes & Submit */}
        <div className="card p-6 flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Izohlar / Qo&apos;shimcha ma&apos;lumot</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input min-h-16"
              placeholder="Faktura yoki to&apos;lov shartlari haqida izoh..."
            />
          </div>
          <div className="text-right space-y-3 min-w-64">
            <div>
              <span className="text-sm text-gray-500 font-medium">JAMI XARID SUMMASI:</span>
              <p className="text-2xl font-black text-indigo-600">{formatCurrency(grandTotal)}</p>
            </div>
            <div className="flex gap-2">
              <Link href="/purchases" className="btn-secondary flex-1">Bekor qilish</Link>
              <button
                type="submit"
                disabled={createMutation.isPending || items.length === 0}
                className="btn-primary flex-1"
              >
                <Save size={18} />
                Tasdiqlash
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
