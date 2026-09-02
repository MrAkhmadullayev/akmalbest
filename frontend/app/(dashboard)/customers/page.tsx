'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customersService } from '@/services/customers';
import { formatCurrency } from '@/lib/utils';
import { Plus, Edit, Phone, MapPin, Search } from 'lucide-react';

export default function CustomersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Form states
  const [editingCustomer, setEditingCustomer] = useState<any>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [notes, setNotes] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['customers', search, page],
    queryFn: () => customersService.getAll({ search, page: page.toString() }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => customersService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      customersService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      resetForm();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) return;

    const payload = { full_name: fullName, phone, address, notes };

    if (editingCustomer) {
      updateMutation.mutate({ id: editingCustomer.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (c: any) => {
    setEditingCustomer(c);
    setFullName(c.full_name);
    setPhone(c.phone || '');
    setAddress(c.address || '');
    setNotes(c.notes || '');
  };

  const resetForm = () => {
    setEditingCustomer(null);
    setFullName('');
    setPhone('');
    setAddress('');
    setNotes('');
  };

  const customers = data?.data?.results || [];
  const totalCount = data?.data?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Form panel */}
      <div className="card p-6 h-fit space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {editingCustomer ? 'Mijozni tahrirlash' : 'Yangi mijoz qo\'shish'}
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">Mijoz ma&apos;lumotlarini to&apos;ldiring</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">F.I.SH (To&apos;liq ism)</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="input"
              placeholder="Masalan: Akbar Xolmatov"
              required
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
              placeholder="Toshkent sh., Yunusobod..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Izoh</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input min-h-20"
              placeholder="Qo&apos;shimcha ma&apos;lumotlar..."
            />
          </div>

          <div className="flex gap-2">
            {editingCustomer && (
              <button type="button" onClick={resetForm} className="btn-secondary flex-1">
                Bekor qilish
              </button>
            )}
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="btn-primary flex-1"
            >
              {editingCustomer ? 'Yangilash' : 'Saqlash'}
            </button>
          </div>
        </form>
      </div>

      {/* List panel */}
      <div className="card p-6 lg:col-span-2 space-y-4 flex flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">Mijozlar ro&apos;yxati</h2>
          </div>

          <div className="relative">
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
              placeholder="F.I.SH yoki telefon bo&apos;yicha qidirish..."
              className="input !pl-10"
            />
          </div>

          {isLoading ? (
            <div className="text-center text-gray-500 py-8">Yuklanmoqda...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {customers.map((c) => (
                <div key={c.id} className="p-4 rounded-xl border border-gray-200 flex flex-col justify-between space-y-4 hover:border-indigo-500/30 transition-all">
                  <div>
                    <h3 className="font-bold text-gray-900">{c.full_name}</h3>
                    <div className="mt-3 space-y-1.5 text-xs text-gray-600">
                      <p className="flex items-center gap-1.5">
                        <Phone size={13} className="text-gray-400" />
                        {c.phone || '-'}
                      </p>
                      <p className="flex items-center gap-1.5">
                        <MapPin size={13} className="text-gray-400" />
                        {c.address || '-'}
                      </p>
                    </div>
                  </div>

                  <div className="border-t pt-3 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-gray-400 font-medium">QARZ QOLDIG&apos;I</p>
                      <p className={`text-sm font-bold ${parseFloat(c.total_debt) > 0 ? 'text-red-600' : 'text-gray-500'}`}>
                        {formatCurrency(c.total_debt)}
                      </p>
                    </div>
                    <button
                      onClick={() => handleEdit(c)}
                      className="text-sm text-indigo-600 hover:text-indigo-700 font-medium cursor-pointer"
                    >
                      Tahrirlash
                    </button>
                  </div>
                </div>
              ))}
              {customers.length === 0 && (
                <div className="col-span-2 text-center text-gray-400 py-12">
                  Mijozlar topilmadi
                </div>
              )}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pt-4 border-t border-gray-100 flex items-center justify-between mt-4">
            <span className="text-sm text-gray-500">Jami {totalCount} ta mijoz</span>
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
    </div>
  );
}
