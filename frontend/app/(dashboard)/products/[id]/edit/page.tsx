'use client';

import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as zod from 'zod';
import { productsService, categoriesService, brandsService } from '@/services/products';
import { suppliersService } from '@/services/suppliers';
import apiClient from '@/lib/api-client';
import { useEffect, useState } from 'react';
import { ArrowLeft, Save, Package, X } from 'lucide-react';
import Link from 'next/link';

const productSchema = zod.object({
  name: zod.string().min(1, 'Nomi kiritilishi shart'),
  barcode: zod.string().min(1, 'Shtrix-kod kiritilishi shart'),
  category: zod.string().min(1, 'Kategoriya tanlanishi shart'),
  brand_name: zod.string().optional().nullable(),
  volume: zod.string().min(1, 'Hajmi kiritilishi shart'),
  unit: zod.enum(['bottle', 'L', 'ml', 'pcs', 'box', 'pack']),
  purchase_price: zod.string().min(1, 'Sotib olish narxi kiritilishi shart'),
  selling_price: zod.string().min(1, 'Sotish narxi kiritilishi shart'),
  min_stock: zod.number().min(0),
  warning_stock: zod.number().min(0),
  max_stock: zod.number().min(0),
  supplier: zod.string().optional().nullable(),
  expiration_date: zod.string().optional().nullable(),
  description: zod.string().optional().nullable(),
  // `.default()` ISHLATILMAYDI — input/output tip farqi RHF Resolver'ni buzadi.
  is_active: zod.boolean().optional(),
});

type ProductFormData = zod.infer<typeof productSchema>;

export default function EditProductPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const productId = params?.id as string;

  // Stock adjustment modal state
  const [showStockModal, setShowStockModal] = useState(false);
  const [newStockQty, setNewStockQty] = useState('');
  const [stockNote, setStockNote] = useState("Qo'lda tuzatish");

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
  });

  const { data: product, isLoading: isProductLoading } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsService.getById(productId),
    enabled: !!productId,
  });

  const { data: categoriesData } = useQuery({
    queryKey: ['categories-list'],
    queryFn: () => categoriesService.getAll({ page_size: '100' }),
  });

  const { data: brandsData } = useQuery({
    queryKey: ['brands-list'],
    queryFn: () => brandsService.getAll({ page_size: '100' }),
  });

  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers-list'],
    queryFn: () => suppliersService.getAll({ page_size: '100' }),
  });

  useEffect(() => {
    if (product?.data) {
      const p = product.data;
      reset({
        name: p.name,
        barcode: p.barcode,
        category: p.category,
        brand_name: p.brand_name,
        volume: p.volume,
        unit: p.unit as any,
        purchase_price: p.purchase_price,
        selling_price: p.selling_price,
        min_stock: p.min_stock,
        warning_stock: p.warning_stock,
        max_stock: p.max_stock,
        supplier: p.supplier,
        expiration_date: p.expiration_date,
        description: p.description,
        is_active: p.is_active !== false,
      });
    }
  }, [product, reset]);

  const updateMutation = useMutation({
    mutationFn: (data: FormData) => productsService.update(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
      router.push('/products');
    },
  });

  // Stock adjustment mutation — calls the existing /api/inventory/adjust/ endpoint
  const adjustStockMutation = useMutation({
    mutationFn: (payload: { product_id: string; new_quantity: number; notes: string }) =>
      apiClient.post('/inventory/adjust/', payload),
    onSuccess: (response: any) => {
      const newQty = response?.data?.data?.new_quantity;
      alert(`Zaxira muvaffaqiyatli yangilandi! Yangi miqdor: ${newQty ?? newStockQty} ta`);
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setShowStockModal(false);
      setNewStockQty('');
      setStockNote("Qo'lda tuzatish");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || 'Xatolik yuz berdi';
      alert(`Xatolik: ${msg}`);
    },
  });

  const handleStockAdjust = () => {
    const qty = parseInt(newStockQty);
    if (isNaN(qty) || qty < 0) {
      alert("Iltimos, to'g'ri miqdor kiriting (0 yoki undan katta son)");
      return;
    }
    adjustStockMutation.mutate({
      product_id: productId,
      new_quantity: qty,
      notes: stockNote || "Qo'lda tuzatish",
    });
  };

  const onSubmit = (data: ProductFormData) => {
    const formData = new FormData();
    Object.entries(data).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        formData.append(key, val.toString());
      }
    });
    updateMutation.mutate(formData);
  };

  if (isProductLoading) {
    return <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>;
  }

  const currentStock = product?.data?.current_stock ?? 0;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl">
      <div className="flex items-center gap-4">
        <Link href="/products" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mahsulotni tahrirlash</h1>
          <p className="text-gray-500 mt-0.5">Mahsulot tafsilotlarini yangilang</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="card p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Shtrix-kod</label>
            <input
              {...register('barcode')}
              type="text"
              className={`input font-mono text-lg ${errors.barcode ? 'input-error' : ''}`}
            />
            {errors.barcode && <p className="text-xs text-red-500 mt-1">{errors.barcode.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Mahsulot nomi</label>
            <input
              {...register('name')}
              type="text"
              className={`input ${errors.name ? 'input-error' : ''}`}
            />
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Kategoriya</label>
            <select
              {...register('category')}
              className={`input ${errors.category ? 'input-error' : ''}`}
            >
              <option value="">Tanlang...</option>
              {categoriesData?.data?.results?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {errors.category && <p className="text-xs text-red-500 mt-1">{errors.category.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Brend</label>
            <input
              {...register('brand_name')}
              type="text"
              list="brand-options-edit"
              className={`input ${errors.brand_name ? 'input-error' : ''}`}
              placeholder="Brend nomini kiriting..."
            />
            <datalist id="brand-options-edit">
              {brandsData?.data?.results?.map((b) => (
                <option key={b.id} value={b.name} />
              ))}
            </datalist>
            {errors.brand_name && <p className="text-xs text-red-500 mt-1">{errors.brand_name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Hajmi</label>
              <input {...register('volume')} type="text" className="input" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Birlik</label>
              <select {...register('unit')} className="input">
                <option value="bottle">Shisha</option>
                <option value="L">Litr</option>
                <option value="ml">Millilitr</option>
                <option value="pcs">Dona</option>
                <option value="box">Quti</option>
                <option value="pack">Pachka</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Sotib olish narxi (UZS)</label>
            <input {...register('purchase_price')} type="number" className="input" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Sotish narxi (UZS)</label>
            <input {...register('selling_price')} type="number" className="input" />
          </div>

          {/* Joriy zaxira — read-only display + adjust button */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Joriy zaxira (dona)</label>
            <div className="flex gap-3 items-center">
              <input
                type="number"
                value={currentStock}
                readOnly
                className="input font-semibold text-indigo-700 bg-gray-50 cursor-not-allowed flex-1"
              />
              <button
                type="button"
                onClick={() => {
                  setNewStockQty(String(currentStock));
                  setShowStockModal(true);
                }}
                className="btn-secondary flex items-center gap-2 whitespace-nowrap"
              >
                <Package size={16} />
                Zaxirani o&apos;zgartirish
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Hozirgi ombordagi miqdor. &quot;Zaxirani o&apos;zgartirish&quot; tugmasi orqali yangilang — barcha
              o&apos;zgarishlar ombor tarixi (audit)da saqlanadi.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Minimal zaxira miqdori</label>
            <input
              {...register('min_stock', { valueAsNumber: true })}
              type="number"
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Ogohlantirish miqdori</label>
            <input
              {...register('warning_stock', { valueAsNumber: true })}
              type="number"
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Yetkazib beruvchi</label>
            <select {...register('supplier')} className="input">
              <option value="">Tanlang...</option>
              {suppliersData?.data?.results?.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Yaroqlilik muddati</label>
            <input {...register('expiration_date')} type="date" className="input" />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Tavsif</label>
            <textarea {...register('description')} className="input min-h-24" />
          </div>

          <div className="md:col-span-2 flex items-center gap-3 pt-4 border-t">
            <input
              {...register('is_active')}
              type="checkbox"
              id="is_active"
              className="w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-600 cursor-pointer"
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-900 cursor-pointer select-none">
              Ushbu mahsulot faol (Sotuvda mavjud)
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <Link href="/products" className="btn-secondary">Bekor qilish</Link>
          <button type="submit" disabled={updateMutation.isPending} className="btn-primary">
            <Save size={18} />
            Saqlash
          </button>
        </div>
      </form>

      {/* Stock Adjustment Modal */}
      {showStockModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-gray-100 dark:border-gray-800">
              <div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">Zaxirani o&apos;zgartirish</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  {product?.data?.name} — hozir: <strong>{currentStock} ta</strong>
                </p>
              </div>
              <button
                onClick={() => setShowStockModal(false)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Yangi miqdor (dona)
                </label>
                <input
                  type="number"
                  value={newStockQty}
                  onChange={(e) => setNewStockQty(e.target.value)}
                  className="input text-lg font-semibold"
                  min="0"
                  placeholder="Yangi zaxira miqdorini kiriting..."
                  autoFocus
                />
                {newStockQty !== '' && parseInt(newStockQty) !== currentStock && (
                  <p className="text-xs mt-1">
                    {parseInt(newStockQty) > currentStock
                      ? <span className="text-emerald-600">+{parseInt(newStockQty) - currentStock} ta qo&apos;shiladi</span>
                      : <span className="text-orange-600">-{currentStock - parseInt(newStockQty)} ta kamayadi</span>
                    }
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Sabab / Izoh
                </label>
                <input
                  type="text"
                  value={stockNote}
                  onChange={(e) => setStockNote(e.target.value)}
                  className="input"
                  placeholder="Masalan: inventarizatsiya, hisobni tuzatish..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowStockModal(false)}
                  className="btn-secondary flex-1"
                >
                  Bekor qilish
                </button>
                <button
                  type="button"
                  onClick={handleStockAdjust}
                  disabled={
                    adjustStockMutation.isPending ||
                    newStockQty === '' ||
                    parseInt(newStockQty) === currentStock
                  }
                  className="btn-primary flex-1"
                >
                  {adjustStockMutation.isPending ? 'Saqlanmoqda...' : 'Saqlash'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
