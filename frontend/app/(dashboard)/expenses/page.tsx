'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { expensesService } from '@/services/expenses';
import { formatCurrency, formatDate } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { Plus, Search, DollarSign, XCircle } from 'lucide-react';

export default function ExpensesPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().split('T')[0]);
  const [description, setDescription] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const { user } = useAuth();
  const isAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'ADMIN';

  const { data: expensesData, isLoading } = useQuery({
    queryKey: ['expenses'],
    queryFn: () => expensesService.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => expensesService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      setTitle('');
      setAmount('');
      setDescription('');
      setShowAddForm(false);
    },
    onError: (err: any) => {
      alert(err?.response?.data?.message || err?.response?.data?.detail || "Xarajatni saqlashda xatolik yuz berdi.");
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => expensesService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
    },
    onError: (err: any) => {
      alert(err?.response?.data?.message || "Xarajatni bekor qilishda xatolik yuz berdi.");
    }
  });

  const handleDelete = (id: string, title: string) => {
    if (confirm(`"${title}" xarajatini haqiqatan ham bekor qilmoqchimisiz?`)) {
      deleteMutation.mutate(id);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !amount) return;

    createMutation.mutate({
      title,
      amount: parseFloat(amount),
      expense_date: expenseDate,
      description,
    });
  };

  const expenses = expensesData?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Xarajatlar</h1>
          <p className="text-gray-500 mt-1">Do&apos;konning umumiy operatsion va yordamchi xarajatlari</p>
        </div>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn-primary">
          <Plus size={18} />
          Yangi xarajat kiritish
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Expenses List */}
        <div className="card overflow-hidden lg:col-span-2">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sana</th>
                  <th>Sarlavha</th>
                  <th>Summa</th>
                  <th>Mas&apos;ul</th>
                  <th>Tavsif</th>
                  <th className="text-right">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((e: any) => (
                  <tr key={e.id}>
                    <td>{formatDate(e.expense_date)}</td>
                    <td className="font-medium text-gray-900">{e.title}</td>
                    <td className="font-bold text-red-600">{formatCurrency(e.amount)}</td>
                    <td>{e.created_by_name}</td>
                    <td className="text-gray-500 text-xs max-w-xs truncate">{e.description || '-'}</td>
                    <td>
                      <div className="flex justify-end gap-2">
                        {isAdmin && (
                          <button
                            onClick={() => handleDelete(e.id, e.title)}
                            disabled={deleteMutation.isPending}
                            className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-red-400 hover:text-red-600 cursor-pointer"
                            title="Bekor qilish"
                          >
                            <XCircle size={18} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {expenses.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center text-gray-400 py-12">
                      Xarajatlar kiritilmagan
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Add Expense Form */}
        {showAddForm && (
          <div className="card p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Yangi xarajat</h2>
              <p className="text-sm text-gray-500">Tafsilotlarini kiriting</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Sarlavha</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="input"
                  placeholder="Masalan: Ijara to'lovi, elektr..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Summa (UZS)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="input"
                  placeholder="Summa..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Sana</label>
                <input
                  type="date"
                  value={expenseDate}
                  onChange={(e) => setExpenseDate(e.target.value)}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Tavsif</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input min-h-16"
                  placeholder="Qo&apos;shimcha ma&apos;lumot..."
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="btn-secondary flex-1"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="btn-primary flex-1"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
