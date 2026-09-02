'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { debtsService } from '@/services/debts';
import { formatCurrency, getDebtStatus } from '@/lib/utils';
import { Search, Plus, Calendar, DollarSign, Wallet } from 'lucide-react';

export default function DebtsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Pay debt modal / form states
  const [selectedDebt, setSelectedDebt] = useState<any>(null);
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('CASH');
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['debts', search, page],
    queryFn: () => debtsService.getAll({ search, page: page.toString() }),
  });

  const payMutation = useMutation({
    mutationFn: (payload: any) => debtsService.makePayment(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debts'] });
      setSelectedDebt(null);
      setAmount('');
      setNotes('');
      setErrorMsg('');
    },
    onError: (err: any) => {
      setErrorMsg(err?.response?.data?.message || 'To\'lov qabul qilishda xatolik.');
    },
  });

  const handlePaySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDebt || !amount) return;

    payMutation.mutate({
      debt_id: selectedDebt.id,
      amount: parseFloat(amount),
      payment_method: paymentMethod,
      notes,
    });
  };

  const debts = data?.data?.results || [];
  const totalCount = data?.data?.count || 0;
  const pageSize = 25;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Qarzlar (Nasiyalar) boshqaruvi</h1>
          <p className="text-gray-500 mt-1">Mijozlar nasiba qarzdorliklari va qarz to&apos;lovlari monitoringi</p>
        </div>
      </div>

      <div className="card p-4 flex gap-4">
        <div className="flex-1 relative">
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
            placeholder="Mijoz ismi yoki telefon raqami bo&apos;yicha qidirish..."
            className="input !pl-10"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Debts Table */}
        <div className="card overflow-hidden lg:col-span-2">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mijoz</th>
                  <th>Telefon</th>
                  <th>Boshlang&apos;ich qarz</th>
                  <th>To&apos;langan</th>
                  <th>Qoldiq qarz</th>
                  <th>Muddat</th>
                  <th>Holat</th>
                  <th className="text-right">To&apos;lov</th>
                </tr>
              </thead>
              <tbody>
                {debts.map((d: any) => {
                  const status = getDebtStatus(d.status);
                  return (
                    <tr key={d.id}>
                      <td className="font-medium text-gray-900">{d.customer_name}</td>
                      <td className="text-gray-500 text-xs">{d.customer_phone}</td>
                      <td>{formatCurrency(d.original_amount)}</td>
                      <td className="text-emerald-600 font-medium">{formatCurrency(d.paid_amount)}</td>
                      <td className="font-bold text-red-600">{formatCurrency(d.remaining_amount)}</td>
                      <td className="text-xs text-gray-500">{d.due_date}</td>
                      <td>
                        <span className={`badge ${status.color}`}>
                          {status.icon} {status.label}
                        </span>
                      </td>
                      <td>
                        <div className="flex justify-end">
                          {d.status !== 'PAID' && (
                            <button
                              onClick={() => {
                                setSelectedDebt(d);
                                setAmount(d.remaining_amount);
                              }}
                              className="btn-success btn-sm px-3 py-1 cursor-pointer"
                            >
                              To&apos;lash
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {debts.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center text-gray-400 py-12">
                      Qarzlar topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
              <span className="text-sm text-gray-500">Jami {totalCount} ta qarz</span>
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

        {/* Debt Payment form */}
        {selectedDebt && (
          <div className="card p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Qarzni to&apos;lash</h2>
              <p className="text-sm text-gray-500 font-medium">{selectedDebt.customer_name}</p>
            </div>

            {errorMsg && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded border border-red-200">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handlePaySubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  To&apos;lov summasi (UZS)
                </label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="input font-bold text-lg"
                  max={selectedDebt.remaining_amount}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">To&apos;lov usuli</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CASH')}
                    className={`btn text-sm py-2 ${
                      paymentMethod === 'CASH' ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Naqd
                  </button>
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CARD')}
                    className={`btn text-sm py-2 ${
                      paymentMethod === 'CARD' ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Karta
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Izoh / Qo&apos;shimcha ma&apos;lumot
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="input min-h-16 text-sm"
                  placeholder="Izoh..."
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedDebt(null)}
                  className="btn-secondary flex-1"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={payMutation.isPending}
                  className="btn-success flex-1"
                >
                  To&apos;lovni yakunlash
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
