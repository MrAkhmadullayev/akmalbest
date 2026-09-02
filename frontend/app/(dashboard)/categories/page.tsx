'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { categoriesService } from '@/services/products';
import { Plus, Edit, Trash2 } from 'lucide-react';

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesService.getAll({ page_size: '100' }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      categoriesService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setName('');
      setDescription('');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { name: string; description?: string } }) =>
      categoriesService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setName('');
      setDescription('');
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => categoriesService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    if (editingId) {
      updateMutation.mutate({ id: editingId, payload: { name, description } });
    } else {
      createMutation.mutate({ name, description });
    }
  };

  const handleEdit = (category: any) => {
    setEditingId(category.id);
    setName(category.name);
    setDescription(category.description || '');
  };

  const handleDelete = (id: string) => {
    if (confirm('Ushbu kategoriyani o\'chirmoqchimisiz?')) {
      deleteMutation.mutate(id);
    }
  };

  const categories = data?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Left panel - Add / Edit form */}
      <div className="card p-6 h-fit space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {editingId ? 'Kategoriyani tahrirlash' : 'Yangi kategoriya qo\'shish'}
          </h2>
          <p className="text-gray-500 text-sm mt-0.5">
            Kategoriya ma&apos;lumotlarini to&apos;ldiring
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Nomi</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="Masalan: Vodka"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Tavsif</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input min-h-20"
              placeholder="Tavsif..."
            />
          </div>

          <div className="flex gap-2">
            {editingId && (
              <button
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setName('');
                  setDescription('');
                }}
                className="btn-secondary flex-1"
              >
                Bekor qilish
              </button>
            )}
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="btn-primary flex-1"
            >
              {editingId ? 'Yangilash' : 'Qo\'shish'}
            </button>
          </div>
        </form>
      </div>

      {/* Right panel - List */}
      <div className="card p-6 lg:col-span-2 space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Kategoriyalar ro&apos;yxati</h2>

        {isLoading ? (
          <div className="text-center text-gray-500 py-8">Yuklanmoqda...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nomi</th>
                  <th>Tavsif</th>
                  <th className="text-center">Mahsulotlar soni</th>
                  <th className="text-right">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((c) => (
                  <tr key={c.id}>
                    <td className="font-medium text-gray-900">{c.name}</td>
                    <td className="text-gray-500 max-w-xs truncate">{c.description || '-'}</td>
                    <td className="text-center font-semibold">{c.product_count}</td>
                    <td>
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(c)}
                          className="p-1 text-blue-400 hover:text-blue-600 cursor-pointer"
                        >
                          <Edit size={18} />
                        </button>
                        <button
                          onClick={() => handleDelete(c.id)}
                          className="p-1 text-red-400 hover:text-red-600 cursor-pointer"
                          disabled={c.product_count > 0}
                          title={c.product_count > 0 ? "Ushbu kategoriyada mahsulotlar bor" : ""}
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {categories.length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-center text-gray-400 py-8">
                      Kategoriyalar topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
