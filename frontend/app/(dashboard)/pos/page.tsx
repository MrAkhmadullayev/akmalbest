'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsService } from '@/services/products';
import { salesService, type CreateSalePayload } from '@/services/sales';
import { customersService } from '@/services/customers';
import { useCart } from '@/hooks/useCart';
import { useAuth } from '@/hooks/useAuth';
import { formatCurrency } from '@/lib/utils';
import {
  Search, Trash2, Plus, Minus, X,
  Banknote, CreditCard, Clock, Check,
  Printer,
} from 'lucide-react';
import type { Product } from '@/types';

export default function POSPage() {
  const queryClient = useQueryClient();
  const barcodeInputRef = useRef<HTMLInputElement>(null);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<'CASH' | 'CARD' | 'DEBT'>('CASH');
  const [paidAmount, setPaidAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [completedSale, setCompletedSale] = useState<any>(null);
  
  // Nasiya uchun yangi maydonlar
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');

  const cart = useCart();

  // Auto-focus barcode input
  useEffect(() => {
    const timer = setInterval(() => {
      if (!showPayment && !showSearch && barcodeInputRef.current) {
        const activeEl = document.activeElement;
        if (
          activeEl &&
          (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT') &&
          activeEl !== barcodeInputRef.current
        ) {
          return; // Allow user to type in other fields
        }
        barcodeInputRef.current.focus();
      }
    }, 300);
    return () => clearInterval(timer);
  }, [showPayment, showSearch]);

  // Product search
  const { data: searchResults } = useQuery({
    queryKey: ['pos-search', searchQuery],
    queryFn: () => productsService.getAll({ search: searchQuery, page_size: '10' }),
    enabled: searchQuery.length > 1,
  });

  // Barcode lookup
  const barcodeMutation = useMutation({
    mutationFn: (barcode: string) => productsService.getByBarcode(barcode),
    onSuccess: (response) => {
      const data = response.data as any;
      if (data.success && data.data) {
        const result = cart.addItem(data.data as Product);
        if (!result.success) {
          setErrorMsg(result.error || 'Xatolik yuz berdi');
          setTimeout(() => setErrorMsg(''), 3000);
        } else {
          setErrorMsg('');
        }
      }
    },
    onError: () => {
      setErrorMsg('Mahsulot topilmadi.');
      setTimeout(() => setErrorMsg(''), 3000);
    },
  });

  // Create sale mutation
  const saleMutation = useMutation({
    mutationFn: (payload: CreateSalePayload) => salesService.create(payload),
    onSuccess: (response) => {
      const data = response.data;
      setCompletedSale(data);
      setSuccessMsg('Savdo muvaffaqiyatli yakunlandi!');
      cart.clearCart();
      setShowPayment(false);
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => {
        setSuccessMsg('');
        setCompletedSale(null);
      }, 10000);
    },
    onError: (error: any) => {
      setErrorMsg(
        error?.response?.data?.message || 'Savdo yaratishda xatolik yuz berdi.'
      );
      setTimeout(() => setErrorMsg(''), 5000);
    },
  });

  // Global scanner detection based on average typing speed
  useEffect(() => {
    let buffer = '';
    let startTime = 0;

    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return;

      if (e.key === 'Enter') {
        if (buffer.length > 0) {
          const elapsed = Date.now() - startTime;
          // Average time per character < 50ms is a safe threshold for barcode scanners
          if (buffer.length >= 3 && (elapsed / buffer.length) < 50) {
            e.preventDefault();
            e.stopPropagation();
            const scannedCode = buffer.trim();
            barcodeMutation.mutate(scannedCode);
            setBarcodeInput('');
            
            // Clear any stray input that might have caught the scanner text
            const activeEl = document.activeElement;
            if (activeEl instanceof HTMLInputElement || activeEl instanceof HTMLTextAreaElement) {
              activeEl.value = '';
              activeEl.dispatchEvent(new Event('input', { bubbles: true }));
              activeEl.blur();
            }
          }
          buffer = '';
        }
      } else if (e.key.length === 1) {
        if (buffer.length === 0) {
          startTime = Date.now();
        }
        buffer += e.key;

        // If taking too long (human typing), just reset the buffer to current key
        if (Date.now() - startTime > 3000) {
          buffer = e.key;
          startTime = Date.now();
        }
      } else {
        // Non-printable keys like Backspace reset the buffer
        if (e.key !== 'Shift') {
          buffer = '';
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown, true); // use capture phase
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [barcodeMutation]);

  // Handle barcode input (reads from currentTarget.value synchronously to avoid React state batching delays)
  const handleBarcodeSubmit = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        const val = e.currentTarget.value.trim();
        if (val) {
          barcodeMutation.mutate(val);
          setBarcodeInput('');
        }
      }
    },
    [barcodeMutation]
  );

  // Handle payment
  const handleCompleteSale = () => {
    if (cart.items.length === 0) return;

    const payload: CreateSalePayload = {
      items: cart.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
        discount: item.discount,
      })),
      payment_method: paymentMethod,
      customer_name: paymentMethod === 'DEBT' ? customerName : undefined,
      customer_phone: paymentMethod === 'DEBT' ? customerPhone : undefined,
      discount: cart.discount,
      paid_amount: paymentMethod === 'CASH' && paidAmount ? parseFloat(paidAmount) : null,
      due_date: paymentMethod === 'DEBT' ? dueDate || null : null,
    };

    saleMutation.mutate(payload);
  };

  const changeAmount =
    paymentMethod === 'CASH' && paidAmount
      ? parseFloat(paidAmount) - cart.grandTotal
      : 0;

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-screen lg:min-h-0 bg-gray-50 dark:bg-gray-950 transition-colors duration-200">
      {/* Left Panel - Cart */}
      <div className="flex-1 flex flex-col p-3 lg:p-6 min-h-[60vh] lg:min-h-0">
        {/* Barcode Input */}
        <div className="mb-4 space-y-3">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                ref={barcodeInputRef}
                type="text"
                value={barcodeInput}
                onChange={(e) => setBarcodeInput(e.target.value)}
                onKeyDown={handleBarcodeSubmit}
                placeholder="📷 Shtrix-kodni skanerlang yoki kiriting..."
                className="input text-lg py-3.5 pl-4 pr-12 font-mono"
                autoFocus
              />
              {barcodeInput && (
                <button
                  onClick={() => setBarcodeInput('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
                >
                  <X size={18} />
                </button>
              )}
            </div>
            <button
              onClick={() => setShowSearch(!showSearch)}
              className="btn-secondary px-4"
              title="Mahsulot qidirish"
            >
              <Search size={20} />
            </button>
          </div>

          {/* Search Dropdown */}
          {showSearch && (
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Mahsulot nomi yoki shtrix-kodi..."
                className="input"
                autoFocus
              />
              {searchResults?.data?.results && searchResults.data.results.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl mt-1 max-h-64 overflow-y-auto z-50">
                  {searchResults.data.results.map((product) => (
                    <button
                      key={product.id}
                      onClick={() => {
                        const result = cart.addItem(product);
                        if (!result.success) {
                          setErrorMsg(result.error || 'Xatolik yuz berdi');
                          setTimeout(() => setErrorMsg(''), 3000);
                        }
                        setShowSearch(false);
                        setSearchQuery('');
                      }}
                      className="w-full px-4 py-3 text-left hover:bg-indigo-50 dark:hover:bg-indigo-900/30 flex items-center justify-between border-b border-gray-50 dark:border-gray-800 last:border-0 cursor-pointer"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">{product.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{product.barcode}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-indigo-600">{formatCurrency(product.selling_price)}</p>
                        <p className="text-xs text-gray-400">Qoldiq: {product.current_stock}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Error/Success Messages */}
          {errorMsg && (
            <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
              {errorMsg}
            </div>
          )}
          {successMsg && (
            <div className="px-4 py-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-medium">
              ✅ {successMsg}
              {completedSale?.change_amount && parseFloat(completedSale.change_amount) > 0 && (
                <span className="ml-2 font-bold">
                  Qaytim: {formatCurrency(completedSale.change_amount)}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Cart Table */}
        <div className="flex-1 card overflow-hidden flex flex-col">
          <div className="card-header flex items-center justify-between py-3">
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Savat ({cart.itemCount} ta mahsulot)
            </h2>
            {cart.items.length > 0 && (
              <button onClick={cart.clearCart} className="text-sm text-red-500 hover:text-red-700 cursor-pointer">
                Tozalash
              </button>
            )}
          </div>

          <div className="flex-1 overflow-auto">
            {cart.items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                <ShoppingCartEmpty />
                <p className="mt-4 text-lg font-medium">Savat bo&apos;sh</p>
                <p className="text-sm">Mahsulot qo&apos;shish uchun shtrix-kodni skanerlang</p>
              </div>
            ) : (
              <div className="min-w-[600px] pb-4">
                <table className="data-table w-full">
                  <thead>
                  <tr>
                    <th>Mahsulot</th>
                    <th className="text-center">Narx</th>
                    <th className="text-center">Miqdor</th>
                    <th className="text-center">Chegirma</th>
                    <th className="text-right">Jami</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {cart.items.map((item) => (
                    <tr key={item.product_id}>
                      <td>
                        <p className="font-medium text-gray-900 dark:text-gray-100">{item.name}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 font-mono">{item.barcode}</p>
                      </td>
                      <td className="text-center">{formatCurrency(item.price)}</td>
                      <td>
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => cart.updateQuantity(item.product_id, item.quantity - 1)}
                            className="w-7 h-7 rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center cursor-pointer"
                          >
                            <Minus size={14} />
                          </button>
                          <input
                            type="number"
                            value={item.quantity}
                            onChange={(e) => cart.updateQuantity(item.product_id, parseInt(e.target.value) || 1)}
                            className="w-14 text-center border dark:border-gray-700 bg-transparent rounded py-1 text-sm"
                            min={1}
                            max={item.stock}
                          />
                          <button
                            onClick={() => cart.updateQuantity(item.product_id, item.quantity + 1)}
                            className="w-7 h-7 rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center cursor-pointer"
                            disabled={item.quantity >= item.stock}
                          >
                            <Plus size={14} />
                          </button>
                        </div>
                      </td>
                      <td>
                        <input
                          type="number"
                          value={item.discount || ''}
                          onChange={(e) => cart.updateItemDiscount(item.product_id, parseFloat(e.target.value) || 0)}
                          className="w-20 text-center border dark:border-gray-700 bg-transparent rounded py-1 text-sm mx-auto block"
                          placeholder="0"
                          min={0}
                        />
                      </td>
                      <td className="text-right font-semibold">
                        {formatCurrency(item.subtotal)}
                      </td>
                      <td>
                        <button
                          onClick={() => cart.removeItem(item.product_id)}
                          className="text-red-400 hover:text-red-600 cursor-pointer p-1"
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
        </div>
      </div>

      {/* Right Panel - Totals & Payment */}
      <div className="w-full lg:w-96 bg-white dark:bg-gray-900 border-t lg:border-t-0 lg:border-l border-gray-200 dark:border-gray-800 flex flex-col p-4 lg:p-5 shrink-0">
        {/* Totals */}
        <div className="space-y-3 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Jami:</span>
            <span className="font-medium">{formatCurrency(cart.subtotal)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Chegirma:</span>
            <input
              type="number"
              value={cart.discount || ''}
              onChange={(e) => cart.setDiscount(parseFloat(e.target.value) || 0)}
              className="w-28 text-right border dark:border-gray-700 bg-transparent rounded py-1 px-2 text-sm"
              placeholder="0"
            />
          </div>
          <div className="border-t dark:border-gray-800 pt-3">
            <div className="flex justify-between">
              <span className="text-lg font-bold text-gray-900 dark:text-white">JAMI:</span>
              <span className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400">
                {formatCurrency(cart.grandTotal)}
              </span>
            </div>
          </div>
        </div>

        {/* Payment Method */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium text-gray-600 dark:text-gray-400">To&apos;lov usuli</label>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => setPaymentMethod('CASH')}
              className={`pos-btn text-sm ${
                paymentMethod === 'CASH'
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-200 dark:shadow-emerald-900/20'
                  : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/40'
              }`}
            >
              <Banknote size={20} className="mx-auto mb-1" />
              NAQD
            </button>
            <button
              onClick={() => setPaymentMethod('CARD')}
              className={`pos-btn text-sm ${
                paymentMethod === 'CARD'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-200 dark:shadow-blue-900/20'
                  : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40'
              }`}
            >
              <CreditCard size={20} className="mx-auto mb-1" />
              KARTA
            </button>
            <button
              onClick={() => setPaymentMethod('DEBT')}
              className={`pos-btn text-sm ${
                paymentMethod === 'DEBT'
                  ? 'bg-orange-600 text-white shadow-lg shadow-orange-200 dark:shadow-orange-900/20'
                  : 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 hover:bg-orange-100 dark:hover:bg-orange-900/40'
              }`}
            >
              <Clock size={20} className="mx-auto mb-1" />
              NASIYA
            </button>
          </div>
        </div>

        {/* Cash change calculation */}
        {paymentMethod === 'CASH' && (
          <div className="space-y-2 mb-4">
            <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Berilgan summa</label>
            <input
              type="number"
              value={paidAmount}
              onChange={(e) => setPaidAmount(e.target.value)}
              className="input text-lg font-semibold"
              placeholder={cart.grandTotal.toString()}
            />
            {paidAmount && changeAmount >= 0 && (
              <div className="px-3 py-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg text-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Qaytim: </span>
                <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                  {formatCurrency(changeAmount)}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Debt due date */}
        {paymentMethod === 'DEBT' && (
          <div className="space-y-3 mb-4 bg-orange-50/50 dark:bg-orange-900/10 p-4 rounded-xl border border-orange-100 dark:border-orange-900/30">
            <h3 className="font-semibold text-orange-800 dark:text-orange-400 text-sm mb-2">Mijoz ma'lumotlari</h3>
            
            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Ism-familiyasi *</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className="input text-sm"
                placeholder="Mijoz ismini kiriting..."
              />
            </div>
            
            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Telefon raqami (ixtiyoriy)</label>
              <input
                type="tel"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                className="input text-sm"
                placeholder="+998 90 123 45 67"
              />
            </div>
            
            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">To'lov muddati *</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="input text-sm"
              />
            </div>
          </div>
        )}

        {/* Complete Sale Button */}
        <button
          onClick={handleCompleteSale}
          disabled={
            cart.items.length === 0 ||
            saleMutation.isPending ||
            (paymentMethod === 'DEBT' && (!customerName.trim() || !dueDate))
          }
          className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-lg rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-200 active:scale-[0.98] cursor-pointer mt-auto"
        >
          {saleMutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
              Yakunlanmoqda...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Check size={22} />
              SAVDONI YAKUNLASH
            </span>
          )}
        </button>

        {/* Receipt for completed sale */}
        {completedSale?.data && (
          <button
            onClick={() => window.print()}
            className="w-full mt-3 py-2.5 btn-secondary cursor-pointer"
          >
            <Printer size={18} />
            Chek chop etish
          </button>
        )}
      </div>
    </div>
  );
}

function ShoppingCartEmpty() {
  return (
    <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="21" r="1" />
      <circle cx="19" cy="21" r="1" />
      <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12" />
    </svg>
  );
}
