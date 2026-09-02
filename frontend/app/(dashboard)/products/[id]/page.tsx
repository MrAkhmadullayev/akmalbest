'use client';

import { useQuery } from '@tanstack/react-query';
import { productsService } from '@/services/products';
import { useParams } from 'next/navigation';
import { formatCurrency, formatDate } from '@/lib/utils';
import { ArrowLeft, Edit } from 'lucide-react';
import Link from 'next/link';

export default function ProductDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const { data: product, isLoading } = useQuery({
    queryKey: ['product-detail', id],
    queryFn: () => productsService.getById(id),
    enabled: !!id,
  });

  const p = product?.data as any;

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>;
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/products" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Mahsulot tafsilotlari</h1>
        </div>
        <Link href={`/products/${p?.id}/edit`} className="btn-primary">
          <Edit size={18} />
          Tahrirlash
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Details */}
        <div className="card p-6 md:col-span-2 space-y-6">
          <div className="border-b pb-4">
            <h2 className="text-xl font-bold text-gray-900">{p?.name}</h2>
            <p className="text-sm font-mono text-gray-500 mt-1">Shtrix-kod: {p?.barcode}</p>
          </div>

          <div className="grid grid-cols-2 gap-6 text-sm">
            <div>
              <span className="text-gray-400 block">Kategoriya</span>
              <span className="font-semibold text-gray-900">{p?.category_name}</span>
            </div>
            <div>
              <span className="text-gray-400 block">Brend</span>
              <span className="font-semibold text-gray-900">{p?.brand_name || '-'}</span>
            </div>
            <div>
              <span className="text-gray-400 block">Hajmi</span>
              <span className="font-semibold text-gray-900">{p?.volume} {p?.unit}</span>
            </div>
            <div>
              <span className="text-gray-400 block">Yaroqlilik muddati</span>
              <span className="font-semibold text-gray-900">{p?.expiration_date ? formatDate(p.expiration_date) : '-'}</span>
            </div>
          </div>

          <div className="border-t pt-4">
            <span className="text-gray-400 block text-xs mb-1">TAVSIF</span>
            <p className="text-sm text-gray-700">{p?.description || 'Tavsif kiritilmagan.'}</p>
          </div>
        </div>

        {/* Stock & Prices */}
        <div className="card p-6 space-y-6">
          <div>
            <span className="text-xs text-gray-400 font-bold block">OMBOR QOLDIQ</span>
            <span className="text-3xl font-extrabold text-indigo-600 mt-1 inline-block">
              {p?.current_stock} dona
            </span>
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Sotib olish narxi:</span>
              <span className="font-semibold text-gray-900">{formatCurrency(p?.purchase_price)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Sotish narxi:</span>
              <span className="font-semibold text-indigo-600">{formatCurrency(p?.selling_price)}</span>
            </div>
            <div className="flex justify-between text-sm border-t pt-2">
              <span className="text-gray-500 font-medium">Foyda marjasi:</span>
              <span className="font-bold text-emerald-600">{formatCurrency(p?.profit_margin)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
