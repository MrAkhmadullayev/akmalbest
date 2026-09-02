'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { suppliersService } from '@/services/suppliers';
import { Plus, Edit, Phone, MapPin } from 'lucide-react';

export default function SuppliersPage() {
  const queryClient = useQueryClient();
  const [editingSupplier, setEditingSupplier] = useState<any>(null);
  const [name, setName] = useState('');
  const [contactPerson, setContactPerson] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [notes, setNotes] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => suppliersService.getAll({ page_size: '100' }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => suppliersService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      suppliersService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      resetForm();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const payload = { name, contact_person: contactPerson, phone, address, notes };

    if (editingSupplier) {
      updateMutation.mutate({ id: editingSupplier.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (s: any) => {
    setEditingSupplier(s);
    setName(s.name);
    setContactPerson(s.contact_person || '');
    setPhone(s.phone || '');
    setAddress(s.address || '');
    setNotes(s.notes || '');
  };

  const resetForm = () => {
    setEditingSupplier(null);
    setName('');
    setContactPerson('');
    setPhone('');
    setAddress('');
    setNotes('');
  };

  const suppliers = data?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Form */}
      <div className="card p-6 h-fit space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {editingSupplier ? 'Tahrirlash' : 'Yangi yetkazib beruvchi'}
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">Tafsilotlarini kiriting</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Kompaniya nomi</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="Masalan: Premium Drinks"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Mas&apos;ul shaxs</label>
            <input
              type="text"
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
              className="input"
              placeholder="Masalan: Dilshod Umarov"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Telefon</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="input"
              placeholder="+998901234567"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Manzil</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="input"
              placeholder="Toshkent sh., Chilonzor tumani..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Izoh</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input min-h-20"
              placeholder="Izoh..."
            />
          </div>

          <div className="flex gap-2">
            {editingSupplier && (
              <button type="button" onClick={resetForm} className="btn-secondary flex-1">
                Bekor qilish
              </button>
            )}
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="btn-primary flex-1"
            >
              {editingSupplier ? 'Yangilash' : 'Saqlash'}
            </button>
          </div>
        </form>
      </div>

      {/* List */}
      <div className="card p-6 lg:col-span-2 space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Yetkazib beruvchilar ro&apos;yxati</h2>

        {isLoading ? (
          <div className="text-center text-gray-500 py-8">Yuklanmoqda...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suppliers.map((s) => (
              <div key={s.id} className="p-4 rounded-xl border border-gray-200 hover:border-indigo-500/30 transition-all flex flex-col justify-between space-y-4">
                <div>
                  <h3 className="font-bold text-gray-900">{s.name}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{s.contact_person || 'Mas\'ul shaxs belgilanmagan'}</p>

                  <div className="mt-3 space-y-1.5 text-xs text-gray-600">
                    <p className="flex items-center gap-1.5">
                      <Phone size={13} className="text-gray-400" />
                      {s.phone || '-'}
                    </p>
                    <p className="flex items-center gap-1.5">
                      <MapPin size={13} className="text-gray-400" />
                      {s.address || '-'}
                    </p>
                  </div>
                </div>

                <div className="border-t pt-3 flex items-center justify-between">
                  <span className="text-xs font-semibold text-indigo-600">
                    {s.total_purchases} ta xarid
                  </span>
                  <button
                    onClick={() => handleEdit(s)}
                    className="text-sm text-indigo-600 hover:text-indigo-700 font-medium cursor-pointer"
                  >
                    Tahrirlash
                  </button>
                </div>
              </div>
            ))}
            {suppliers.length === 0 && (
              <div className="col-span-2 text-center text-gray-400 py-12">
                Yetkazib beruvchilar topilmadi
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
