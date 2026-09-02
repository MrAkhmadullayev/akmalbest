'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { salesService } from '@/services/sales';
import { formatCurrency, formatDateTime } from '@/lib/utils';
import { ArrowLeft, Printer } from 'lucide-react';
import Link from 'next/link';

export default function SaleDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const { data: sale, isLoading } = useQuery({
    queryKey: ['sale', id],
    queryFn: () => salesService.getById(id),
    enabled: !!id,
  });

  const saleData = sale?.data as any;

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>;
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between no-print">
        <div className="flex items-center gap-4">
          <Link href="/sales" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Savdo tafsilotlari</h1>
        </div>
        <button onClick={() => window.print()} className="btn-secondary">
          <Printer size={18} />
          Chek chop etish
        </button>
      </div>

      {/* Printable Receipt and details wrapper */}
      <div className="receipt-container card p-6 space-y-6 bg-white border border-gray-200">
        <div className="text-center space-y-1">
          <h2 className="text-xl font-bold">ALCOHOL STORE RECEIPT</h2>
          <p className="text-xs text-gray-500">Toshkent sh., Chilonzor tumani</p>
          <p className="text-xs text-gray-500">Tel: +998 90 123 45 67</p>
        </div>

        <div className="border-t border-b border-gray-100 py-3 grid grid-cols-2 gap-y-2 text-xs">
          <div>
            <span className="text-gray-400 block">Savdo raqami</span>
            <span className="font-semibold">{saleData?.sale_number}</span>
          </div>
          <div>
            <span className="text-gray-400 block">Sana</span>
            <span className="font-semibold">{formatDateTime(saleData?.created_at)}</span>
          </div>
          <div>
            <span className="text-gray-400 block">Kassir</span>
            <span className="font-semibold">{saleData?.cashier_name}</span>
          </div>
          <div>
            <span className="text-gray-400 block">Mijoz</span>
            <span className="font-semibold">{saleData?.customer_name || 'Oddiy mijoz'}</span>
          </div>
        </div>

        <table className="w-full text-xs">
          <thead>
            <tr className="border-b">
              <th className="text-left pb-2">Mahsulot</th>
              <th className="text-center pb-2">Soni</th>
              <th className="text-right pb-2">Narx</th>
              <th className="text-right pb-2">Jami</th>
            </tr>
          </thead>
          <tbody>
            {saleData?.items?.map((item: any) => (
              <tr key={item.id} className="border-b border-gray-50">
                <td className="py-2">{item.product_name_snapshot}</td>
                <td className="text-center py-2">{item.quantity}</td>
                <td className="text-right py-2">{formatCurrency(item.selling_price_snapshot)}</td>
                <td className="text-right py-2 font-semibold">{formatCurrency(item.subtotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="space-y-1.5 text-xs text-right border-t pt-4">
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

        <div className="text-center border-t pt-4">
          <p className="text-[10px] text-gray-400">Haridingiz uchun rahmat!</p>
        </div>
      </div>
    </div>
  );
}
