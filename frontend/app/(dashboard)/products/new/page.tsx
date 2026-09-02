'use client';

import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as zod from 'zod';
import { productsService, categoriesService, brandsService } from '@/services/products';
import { useEffect, useRef } from 'react';
import { ArrowLeft, Save } from 'lucide-react';
import Link from 'next/link';

const productSchema = zod.object({
  name: zod.string().min(1, 'Nomi kiritilishi shart'),
  barcode: zod.string().min(1, 'Shtrix-kod kiritilishi shart'),
  category: zod.string().min(1, 'Kategoriya tanlanishi shart'),
  brand_name: zod.string().optional(),
  volume: zod.string().min(1, 'Hajmi kiritilishi shart'),
  unit: zod.enum(['bottle', 'L', 'ml', 'pcs', 'box', 'pack']),
  purchase_price: zod.string().min(1, 'Sotib olish narxi kiritilishi shart'),
  selling_price: zod.string().min(1, 'Sotish narxi kiritilishi shart'),
  min_stock: zod.number().min(0),
  warning_stock: zod.number().min(0),
  max_stock: zod.number().min(0),
  initial_stock: zod.number().min(0).optional(),
  payment_method: zod.enum(['CASH', 'DEBT']).optional(),
  expiration_date: zod.string().optional(),
  description: zod.string().optional(),
  // `.default()` ISHLATILMAYDI: Zod'da default input tipini optional, output
  // tipini required qiladi -> react-hook-form Resolver tipi mos kelmay qoladi.
  // Boshlang'ich qiymat quyidagi defaultValues orqali beriladi.
  is_active: zod.boolean().optional(),
});

type ProductFormData = zod.infer<typeof productSchema>;

export default function NewProductPage() {
  const router = useRouter();
  const barcodeInputRef = useRef<HTMLInputElement>(null);

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      unit: 'bottle',
      min_stock: 5,
      warning_stock: 10,
      max_stock: 100,
      initial_stock: 0,
      payment_method: 'CASH',
      is_active: true,
    },
  });

  // Fetch categories, brands, suppliers
  const { data: categoriesData } = useQuery({
    queryKey: ['categories-list'],
    queryFn: () => categoriesService.getAll({ page_size: '100' }),
  });

  const { data: brandsData } = useQuery({
    queryKey: ['brands-list'],
    queryFn: () => brandsService.getAll({ page_size: '100' }),
  });

  const createMutation = useMutation({
    mutationFn: (data: FormData) => productsService.create(data),
    onSuccess: () => {
      router.push('/products');
    },
    onError: (error: any) => {
      const data = error.response?.data;
      if (data) {
        if (typeof data === 'string') {
          alert(data);
        } else if (data.message || data.detail) {
          alert(data.message || data.detail);
        } else {
          const firstError = Object.values(data).flat()[0] as string;
          if (firstError) alert(`Xatolik: ${firstError}`);
          else alert("Xatolik yuz berdi.");
        }
      } else {
        alert("Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.");
      }
    }
  });

  const onSubmit = (data: ProductFormData) => {
    const formData = new FormData();
    Object.entries(data).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        formData.append(key, val.toString());
      }
    });
    createMutation.mutate(formData);
  };

  const onInvalid = (errors: any) => {
    const firstError = Object.values(errors)[0] as any;
    if (firstError?.message) {
      alert(`Iltimos, maydonni to'g'ri to'ldiring: ${firstError.message}`);
    } else {
      alert("Iltimos, barcha majburiy maydonlarni to'ldiring.");
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl">
      <div className="flex items-center gap-4">
        <Link href="/products" className="p-2 bg-white rounded-lg border hover:bg-gray-50">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Yangi mahsulot qo&apos;shish</h1>
          <p className="text-gray-500 mt-0.5">Yangi mahsulot tafsilotlarini kiriting yoki shtrix-kodni skanerlang</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="space-y-6">
        <div className="card p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Shtrix-kod (Skanerlang)</label>
            <input
              {...register('barcode')}
              type="text"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault(); // Skaner Enter bosganda forma saqlanib ketmasligi uchun
                }
              }}
              className={`input font-mono text-lg ${errors.barcode ? 'input-error' : ''}`}
              placeholder="Shtrix-kod skanerlang..."
            />
            {errors.barcode && <p className="text-xs text-red-500 mt-1">{errors.barcode.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Mahsulot nomi</label>
            <input
              {...register('name')}
              type="text"
              className={`input ${errors.name ? 'input-error' : ''}`}
              placeholder="Masalan: Absolut Vodka 0.5L"
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
              list="brand-options"
              className={`input ${errors.brand_name ? 'input-error' : ''}`}
              placeholder="Brend nomini kiriting..."
            />
            <datalist id="brand-options">
              {brandsData?.data?.results?.map((b) => (
                <option key={b.id} value={b.name} />
              ))}
            </datalist>
            {errors.brand_name && <p className="text-xs text-red-500 mt-1">{errors.brand_name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Hajmi</label>
              <input
                {...register('volume')}
                type="text"
                className={`input ${errors.volume ? 'input-error' : ''}`}
                placeholder="0.5"
              />
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
            <input
              {...register('purchase_price')}
              type="number"
              className={`input ${errors.purchase_price ? 'input-error' : ''}`}
              placeholder="85000"
            />
            {errors.purchase_price && <p className="text-xs text-red-500 mt-1">{errors.purchase_price.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Sotish narxi (UZS)</label>
            <input
              {...register('selling_price')}
              type="number"
              className={`input ${errors.selling_price ? 'input-error' : ''}`}
              placeholder="110000"
            />
            {errors.selling_price && <p className="text-xs text-red-500 mt-1">{errors.selling_price.message}</p>}
          </div>

          <div className="md:col-span-2 pt-4 border-t">
            <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase">Boshlang&apos;ich ombor qoldig&apos;i</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Soni (Kirim miqdori)</label>
                <input
                  {...register('initial_stock', { valueAsNumber: true })}
                  type="number"
                  className="input"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Ushbu kirim uchun to&apos;lov turi</label>
                <select {...register('payment_method')} className="input">
                  <option value="CASH">Naqd (To'langan)</option>
                  <option value="DEBT">Nasiya (Qarz)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="md:col-span-2 pt-4 border-t grid grid-cols-1 md:grid-cols-2 gap-6">
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

          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Yaroqlilik muddati</label>
            <input {...register('expiration_date')} type="date" className="input" />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Tavsif</label>
            <textarea {...register('description')} className="input min-h-24" placeholder="Qo&apos;shimcha ma&apos;lumotlar..." />
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
          <button type="submit" disabled={createMutation.isPending} className="btn-primary">
            <Save size={18} />
            Saqlash
          </button>
        </div>
      </form>
    </div>
  );
}
