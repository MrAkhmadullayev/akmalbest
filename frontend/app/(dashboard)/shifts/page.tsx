'use client';

import { useQuery } from '@tanstack/react-query';
import { reportsService } from '@/services/reports';
import { formatCurrency, formatDateTime } from '@/lib/utils';
import { Clock, Wallet, CreditCard, TrendingUp, ShoppingBag, DollarSign, X, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import Link from 'next/link';
import type { ShiftDetailKind } from '@/types';

/** Karta -> qaysi ma'lumot ochilishi. `kind` backendga yuboriladi. */
type CardDef = {
  kind: ShiftDetailKind;
  label: string;
  field: string;
  icon: typeof ShoppingBag;
  tone: string;
  note?: (s: any) => string;
};

const CARDS: CardDef[] = [
  {
    kind: 'sales', label: 'Jami Savdo', field: 'total_sales', icon: ShoppingBag,
    tone: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 hover:bg-indigo-100 dark:hover:bg-indigo-900/40',
    note: (s) => `${s.sales_count} ta tranzaksiya`,
  },
  {
    kind: 'profit', label: 'Sof Foyda', field: 'total_profit', icon: TrendingUp,
    tone: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 hover:bg-emerald-100 dark:hover:bg-emerald-900/40',
    note: () => 'Qaytarilganlar ayirilgan',
  },
  {
    kind: 'cash', label: 'Naqd Tushum', field: 'total_cash', icon: Wallet,
    tone: 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700',
  },
  {
    kind: 'card', label: 'Karta Tushum', field: 'total_card', icon: CreditCard,
    tone: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/40',
  },
  {
    kind: 'debt', label: 'Nasiya (Qarz)', field: 'total_debt', icon: Clock,
    tone: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 hover:bg-orange-100 dark:hover:bg-orange-900/40',
  },
  {
    kind: 'expenses', label: 'Xarajatlar', field: 'total_expenses', icon: DollarSign,
    tone: 'bg-red-50 dark:bg-red-900/20 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/40',
  },
];

const EXTRA_CARDS: CardDef[] = [
  {
    kind: 'debt_payments_cash', label: "Qarz to'lovi (Naqd)", field: 'total_debt_payments_cash', icon: Wallet,
    tone: 'bg-teal-50 dark:bg-teal-900/20 text-teal-600 hover:bg-teal-100 dark:hover:bg-teal-900/40',
    note: () => 'Nasiya to’lovlari — naqd',
  },
  {
    kind: 'debt_payments_card', label: "Qarz to'lovi (Karta)", field: 'total_debt_payments_card', icon: CreditCard,
    tone: 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-600 hover:bg-cyan-100 dark:hover:bg-cyan-900/40',
    note: () => 'Nasiya to’lovlari — karta',
  },
  {
    kind: 'returns', label: 'Qaytarimlar', field: 'total_returns', icon: ShoppingBag,
    tone: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/40',
    note: () => 'Qaytarilgan tovarlar summasi',
  },
];

export default function ShiftsPage() {
  const [selectedShift, setSelectedShift] = useState<any>(null);
  // Qaysi karta ochilgan. null bo'lsa tafsilot paneli yopiq.
  const [openKind, setOpenKind] = useState<{ kind: ShiftDetailKind; label: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['shifts'],
    queryFn: () => reportsService.getShifts(),
  });

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['shift-details', selectedShift?.id, openKind?.kind],
    queryFn: () => reportsService.getShiftDetails(selectedShift.id, openKind!.kind),
    enabled: !!selectedShift?.id && !!openKind,
  });

  const shifts = data?.data?.results || [];
  const detail = detailData?.data;

  const openCard = (card: CardDef) => setOpenKind({ kind: card.kind, label: card.label });

  const renderCard = (card: CardDef) => {
    const Icon = card.icon;
    const value = selectedShift[card.field];
    const active = openKind?.kind === card.kind;
    return (
      <button
        key={card.label}
        type="button"
        onClick={() => openCard(card)}
        className={`p-4 rounded-xl text-left w-full transition-colors cursor-pointer ${card.tone} ${
          active ? 'ring-2 ring-offset-1 ring-indigo-400 dark:ring-offset-gray-900' : ''
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <Icon size={18} />
          <span className="font-medium">{card.label}</span>
          <ChevronRight size={16} className="ml-auto opacity-60" />
        </div>
        <p className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white break-words">
          {formatCurrency(value)}
        </p>
        <p className="text-xs mt-1 opacity-80">{card.note ? card.note(selectedShift) : 'Tafsilotlar uchun bosing'}</p>
      </button>
    );
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Smenalar tarixi</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Yopilgan smenalar (Z-Report). Har bir ko&apos;rsatkich ustiga bosib, o&apos;sha smenada aynan nima
          bo&apos;lganini ko&apos;rish mumkin.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Smenalar ro'yxati */}
        <div className="lg:col-span-1 space-y-4">
          <div className="card p-4">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Ro&apos;yxat</h2>
            {isLoading ? (
              <div className="text-center text-gray-500 py-4">Yuklanmoqda...</div>
            ) : shifts.length === 0 ? (
              <div className="text-center text-gray-500 py-4">Smenalar topilmadi</div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {shifts.map((shift: any) => (
                  <button
                    key={shift.id}
                    type="button"
                    onClick={() => {
                      setSelectedShift(shift);
                      setOpenKind(null);
                    }}
                    className={`p-4 rounded-xl border cursor-pointer transition-colors w-full text-left ${
                      selectedShift?.id === shift.id
                        ? 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800'
                        : 'bg-white border-gray-100 hover:border-indigo-100 dark:bg-gray-800 dark:border-gray-700'
                    }`}
                  >
                    <div className="flex flex-wrap justify-between items-start gap-2 mb-2">
                      <span className="font-bold text-indigo-600">#{shift.shift_number}</span>
                      <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                        {shift.closed_by_name}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <Clock size={14} className="text-gray-400" />
                        <span>{formatDateTime(shift.closed_at)}</span>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-100 dark:border-gray-700 mt-2">
                        <span className="text-gray-500">Jami savdo:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {formatCurrency(shift.total_sales)}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Smena tafsilotlari */}
        <div className="lg:col-span-2">
          {selectedShift ? (
            <div className="card p-4 sm:p-6 space-y-6">
              <div className="border-b border-gray-100 dark:border-gray-800 pb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Smena #{selectedShift.shift_number}
                </h2>
                <p className="text-gray-500 text-sm mt-1">
                  Yopilgan: {formatDateTime(selectedShift.closed_at)} | Kassir: {selectedShift.closed_by_name}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  Ochilgan: {formatDateTime(selectedShift.opened_at)}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{CARDS.map(renderCard)}</div>

              {/* Qo'shimcha harakatlar */}
              {EXTRA_CARDS.some((c) => parseFloat(selectedShift[c.field] || '0') > 0) && (
                <div className="border-t border-gray-100 dark:border-gray-800 pt-6">
                  <h3 className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase mb-4">
                    Qo&apos;shimcha harakatlar
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                    {EXTRA_CARDS.filter((c) => parseFloat(selectedShift[c.field] || '0') > 0).map(renderCard)}
                  </div>
                </div>
              )}

              {/* Kutilgan kassa */}
              <div className="border-t border-gray-100 dark:border-gray-800 pt-6">
                <div className="p-4 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-indigo-600 mb-1">Kutilgan kassa (Naqd)</p>
                      <p className="text-xs text-gray-500">
                        Naqd savdo + Qarz naqd to&apos;lovlari − Xarajatlar
                      </p>
                    </div>
                    <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-300">
                      {formatCurrency(selectedShift.expected_cash)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Tanlangan kartaning tafsilotlari */}
              {openKind && (
                <div className="border-t border-gray-100 dark:border-gray-800 pt-6">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                      <h3 className="font-bold text-gray-900 dark:text-white">
                        {detail?.label || openKind.label}
                      </h3>
                      {detail && (
                        <p className="text-sm text-gray-500">
                          {detail.count} ta yozuv · jami {formatCurrency(detail.total)}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setOpenKind(null)}
                      className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
                      aria-label="Tafsilotlarni yopish"
                    >
                      <X size={18} />
                    </button>
                  </div>

                  {detailLoading ? (
                    <div className="py-8 text-center text-gray-500">Yuklanmoqda...</div>
                  ) : !detail || detail.results.length === 0 ? (
                    <div className="py-8 text-center text-gray-400">
                      Bu smenada bunday harakat qayd etilmagan
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="data-table min-w-[620px]">
                        <thead>
                          <tr>
                            <th>Vaqt</th>
                            <th>Tavsif</th>
                            <th>Kim</th>
                            <th className="text-right">Summa</th>
                            {openKind.kind === 'profit' && <th className="text-right">Foyda</th>}
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {detail.results.map((row) => (
                            <tr key={row.id}>
                              <td className="whitespace-nowrap text-gray-500">
                                {formatDateTime(row.created_at)}
                              </td>
                              <td>
                                <span className="font-medium text-gray-900 dark:text-white">{row.title}</span>
                                {row.subtitle && (
                                  <span className="block text-xs text-gray-500">{row.subtitle}</span>
                                )}
                              </td>
                              <td className="text-gray-600 dark:text-gray-400">{row.person || '-'}</td>
                              <td className="text-right font-semibold whitespace-nowrap">
                                {formatCurrency(row.amount)}
                              </td>
                              {openKind.kind === 'profit' && (
                                <td className="text-right text-emerald-600 whitespace-nowrap">
                                  {formatCurrency(row.extra)}
                                </td>
                              )}
                              <td className="text-right">
                                {row.link && (
                                  <Link
                                    href={row.link}
                                    className="text-indigo-600 hover:text-indigo-800 text-sm whitespace-nowrap"
                                  >
                                    Ochish
                                  </Link>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="card p-12 text-center text-gray-400">
              <Clock size={48} className="mx-auto mb-4 opacity-20" />
              <p>Tafsilotlarini ko&apos;rish uchun chap tomondan smenani tanlang</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
