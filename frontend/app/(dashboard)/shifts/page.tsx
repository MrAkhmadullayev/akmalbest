'use client';

import { useQuery } from '@tanstack/react-query';
import { reportsService } from '@/services/reports';
import { formatCurrency, formatDateTime } from '@/lib/utils';
import { Clock, Wallet, CreditCard, TrendingUp, ShoppingBag, DollarSign } from 'lucide-react';
import { useState } from 'react';

export default function ShiftsPage() {
  const [selectedShift, setSelectedShift] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['shifts'],
    queryFn: () => reportsService.getShifts(),
  });

  const shifts = data?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Smenalar tarixi</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Yopilgan smenalar (Z-Report) bo&apos;yicha kunlik savdo va xarajat hisobotlari</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shifts List */}
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
                  <div 
                    key={shift.id}
                    onClick={() => setSelectedShift(shift)}
                    className={`p-4 rounded-xl border cursor-pointer transition-colors ${
                      selectedShift?.id === shift.id 
                        ? 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800' 
                        : 'bg-white border-gray-100 hover:border-indigo-100 dark:bg-gray-800 dark:border-gray-700'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-bold text-indigo-600">#{shift.shift_number}</span>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {shift.closed_by_name}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <Clock size={14} className="text-gray-400" />
                        <span>{formatDateTime(shift.closed_at)}</span>
                      </div>
                      <div className="flex items-center justify-between pt-2 border-t border-gray-100 mt-2">
                        <span className="text-gray-500">Jami savdo:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(shift.total_sales)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Shift Details */}
        <div className="lg:col-span-2">
          {selectedShift ? (
            <div className="card p-6 space-y-6">
              <div className="border-b border-gray-100 pb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  Smena #{selectedShift.shift_number}
                </h2>
                <p className="text-gray-500 text-sm mt-1">
                  Yopilgan vaqt: {formatDateTime(selectedShift.closed_at)} | Kassir: {selectedShift.closed_by_name}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  Ochilgan vaqt: {formatDateTime(selectedShift.opened_at)}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-indigo-600 mb-2">
                    <ShoppingBag size={18} />
                    <span className="font-medium">Jami Savdo</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_sales)}</p>
                  <p className="text-sm text-indigo-600 mt-1">{selectedShift.sales_count} ta tranzaksiya</p>
                </div>

                <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-emerald-600 mb-2">
                    <TrendingUp size={18} />
                    <span className="font-medium">Sof Foyda</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_profit)}</p>
                  <p className="text-sm text-emerald-600 mt-1">Sof qolgan summa</p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 mb-2">
                    <Wallet size={18} />
                    <span className="font-medium">Naqd Tushum</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_cash)}</p>
                </div>

                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-blue-600 mb-2">
                    <CreditCard size={18} />
                    <span className="font-medium">Karta Tushum</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_card)}</p>
                </div>
                
                <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-orange-600 mb-2">
                    <Clock size={18} />
                    <span className="font-medium">Nasiya (Qarz)</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_debt)}</p>
                </div>

                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-red-600 mb-2">
                    <DollarSign size={18} />
                    <span className="font-medium">Xarajatlar</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">{formatCurrency(selectedShift.total_expenses)}</p>
                </div>
              </div>
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
