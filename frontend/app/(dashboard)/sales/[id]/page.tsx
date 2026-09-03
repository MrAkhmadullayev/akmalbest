'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { salesService } from '@/services/sales';
import { formatCurrency, formatDateTime, getPaymentMethodLabel } from '@/lib/utils';
import { ArrowLeft, Printer, RotateCcw, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function SaleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params?.id as string;
  const [returnItemId, setReturnItemId] = useState<string | null>(null);
  const [returnQty, setReturnQty] = useState(1);

  const { data: sale, isLoading } = useQuery({
    queryKey: ['sale', id],
    queryFn: () => salesService.getById(id),
    enabled: !!id,
  });

  const returnMutation = useMutation({
    mutationFn: (data: { sale_item_id: string; return_quantity: number }) =>
      salesService.returnItem(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sale', id] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setReturnItemId(null);
      setReturnQty(1);
    },
    onError: (err: any) => {
      alert(err?.response?.data?.message || "Qaytarishda xatolik yuz berdi.");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => salesService.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sale', id] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      alert(err?.response?.data?.message || "Bekor qilishda xatolik yuz berdi.");
    },
  });

  const handleReturn = (itemId: string, qty: number) => {
    if (qty < 1) return;
    returnMutation.mutate({ sale_item_id: itemId, return_quantity: qty });
  };

  const handleCancelSale = () => {
    if (confirm("Bu savdoni butunlay bekor qilmoqchimisiz? Barcha mahsulotlar omborga qaytariladi.")) {
      cancelMutation.mutate();
    }
  };

  const saleData = sale?.data as any;

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>;
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'Bajarildi';
      case 'CANCELLED': return 'Bekor qilindi';
      case 'RETURNED': return 'Qaytarildi';
      case 'PARTIALLY_RETURNED': return 'Qisman qaytarildi';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700';
      case 'CANCELLED': return 'bg-red-50 text-red-700';
      default: return 'bg-orange-50 text-orange-700';
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between no-print">
        <div className="flex items-center gap-4">
          <Link href="/sales" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Savdo tafsilotlari</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-gray-500">{saleData?.sale_number}</span>
              <span className={`badge text-xs ${getStatusColor(saleData?.status)}`}>
                {getStatusLabel(saleData?.status)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {saleData?.status === 'COMPLETED' && (
            <button
              onClick={handleCancelSale}
              disabled={cancelMutation.isPending}
              className="btn-secondary text-red-600 hover:bg-red-50 border-red-200"
            >
              <XCircle size={18} />
              Savdoni bekor qilish
            </button>
          )}
          <button onClick={() => window.print()} className="btn-secondary">
            <Printer size={18} />
            Chek chop etish
          </button>
        </div>
      </div>

      {/* Sale Info */}
      <div className="card p-6 space-y-6 bg-white border border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400 block text-xs">Savdo raqami</span>
            <span className="font-semibold">{saleData?.sale_number}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-xs">Sana</span>
            <span className="font-semibold">{formatDateTime(saleData?.created_at)}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-xs">Kassir</span>
            <span className="font-semibold">{saleData?.cashier_name}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-xs">Mijoz</span>
            <span className="font-semibold">{saleData?.customer_name || 'Oddiy mijoz'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-xs">To&apos;lov usuli</span>
            <span className="font-semibold">{getPaymentMethodLabel(saleData?.payment_method)}</span>
          </div>
        </div>

        {/* Items table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left pb-3 font-semibold text-gray-500">Mahsulot</th>
                <th className="text-center pb-3 font-semibold text-gray-500">Soni</th>
                <th className="text-center pb-3 font-semibold text-gray-500">Qaytarilgan</th>
                <th className="text-right pb-3 font-semibold text-gray-500">Narx</th>
                <th className="text-right pb-3 font-semibold text-gray-500">Jami</th>
                {saleData?.status === 'COMPLETED' && (
                  <th className="text-right pb-3 font-semibold text-gray-500 no-print">Amal</th>
                )}
              </tr>
            </thead>
            <tbody>
              {saleData?.items?.map((item: any) => {
                const returnable = item.quantity - item.returned_quantity;
                return (
                  <tr key={item.id} className="border-b border-gray-50">
                    <td className="py-3">
                      <p className="font-medium">{item.product_name_snapshot}</p>
                      <p className="text-xs text-gray-400 font-mono">{item.barcode_snapshot}</p>
                    </td>
                    <td className="text-center py-3">{item.quantity}</td>
                    <td className="text-center py-3">
                      {item.returned_quantity > 0 ? (
                        <span className="text-orange-600 font-medium">{item.returned_quantity}</span>
                      ) : (
                        <span className="text-gray-300">0</span>
                      )}
                    </td>
                    <td className="text-right py-3">{formatCurrency(item.selling_price_snapshot)}</td>
                    <td className="text-right py-3 font-semibold">{formatCurrency(item.subtotal)}</td>
                    {saleData?.status === 'COMPLETED' && (
                      <td className="text-right py-3 no-print">
                        {returnable > 0 && (
                          <>
                            {returnItemId === item.id ? (
                              <div className="flex items-center justify-end gap-2">
                                <input
                                  type="number"
                                  min={1}
                                  max={returnable}
                                  value={returnQty}
                                  onChange={(e) => setReturnQty(parseInt(e.target.value) || 1)}
                                  className="w-16 text-center border rounded py-1 text-sm"
                                />
                                <button
                                  onClick={() => handleReturn(item.id, returnQty)}
                                  disabled={returnMutation.isPending}
                                  className="text-xs bg-orange-500 text-white px-2 py-1 rounded hover:bg-orange-600 cursor-pointer"
                                >
                                  Qaytarish
                                </button>
                                <button
                                  onClick={() => setReturnItemId(null)}
                                  className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer"
                                >
                                  ✕
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => {
                                  setReturnItemId(item.id);
                                  setReturnQty(1);
                                }}
                                className="p-1 hover:bg-orange-50 rounded text-orange-400 hover:text-orange-600 cursor-pointer"
                                title={`Qaytarish (qoldiq: ${returnable} ta)`}
                              >
                                <RotateCcw size={16} />
                              </button>
                            )}
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div className="space-y-1.5 text-sm text-right border-t pt-4">
          <p>
            <span className="text-gray-500">Subtotal:</span>{' '}
            <span className="font-semibold">{formatCurrency(saleData?.subtotal)}</span>
          </p>
          <p>
            <span className="text-gray-500 font-medium">Chegirma:</span>{' '}
            <span className="text-red-500 font-semibold">-{formatCurrency(saleData?.discount)}</span>
          </p>
          <p className="text-lg font-bold">
            <span className="text-gray-900">JAMI:</span>{' '}
            <span className="text-indigo-600">{formatCurrency(saleData?.total)}</span>
          </p>
        </div>

        <div className="text-center border-t pt-4 print-only">
          <p className="text-[10px] text-gray-400">Haridingiz uchun rahmat!</p>
        </div>
      </div>
    </div>
  );
}
