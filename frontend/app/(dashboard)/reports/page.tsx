'use client';

import { useQuery } from '@tanstack/react-query';
import { reportsService } from '@/services/reports';
import { formatCurrency } from '@/lib/utils';
import { BarChart3, TrendingUp, TrendingDown, DollarSign, Package } from 'lucide-react';

export default function ReportsPage() {
  const { data: salesData, isLoading: isSalesLoading } = useQuery({
    queryKey: ['report-sales'],
    queryFn: () => reportsService.getSalesReport(),
  });

  const { data: profitData, isLoading: isProfitLoading } = useQuery({
    queryKey: ['report-profit'],
    queryFn: () => reportsService.getProfitReport(),
  });

  const { data: inventoryData, isLoading: isInvLoading } = useQuery({
    queryKey: ['report-inventory'],
    queryFn: () => reportsService.getInventoryReport(),
  });

  const { data: debtData, isLoading: isDebtLoading } = useQuery({
    queryKey: ['report-debts'],
    queryFn: () => reportsService.getDebtReport(),
  });

  const salesReport = salesData?.data;
  const profitReport = profitData?.data;
  const inventoryReport = inventoryData?.data;
  const debtReport = debtData?.data;

  if (isSalesLoading || isProfitLoading || isInvLoading || isDebtLoading) {
    return <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>;
  }

  return (
    <div className="p-6 lg:p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analitika va Hisobotlar</h1>
        <p className="text-gray-500 mt-1">Do&apos;konning umumiy moliyaviy va savdo ko&apos;rsatkichlari</p>
      </div>

      {/* Financial Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 font-medium">SAVDO REVENUE</p>
              <p className="text-2xl font-extrabold text-indigo-600 mt-1">
                {formatCurrency(profitReport?.revenue || 0)}
              </p>
            </div>
            <span className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><DollarSign size={20} /></span>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 font-medium">YALPI FOYDA</p>
              <p className="text-2xl font-extrabold text-emerald-600 mt-1">
                {formatCurrency(profitReport?.gross_profit || 0)}
              </p>
            </div>
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg"><TrendingUp size={20} /></span>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 font-medium">UMUMIY XARAJAT</p>
              <p className="text-2xl font-extrabold text-red-600 mt-1">
                {formatCurrency(profitReport?.total_expenses || 0)}
              </p>
            </div>
            <span className="p-2 bg-red-50 text-red-600 rounded-lg"><TrendingDown size={20} /></span>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 font-medium">SOF FOYDA</p>
              <p className="text-2xl font-extrabold text-teal-600 mt-1">
                {formatCurrency(profitReport?.net_profit || 0)}
              </p>
            </div>
            <span className="p-2 bg-teal-50 text-teal-600 rounded-lg"><DollarSign size={20} /></span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top selling products table */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-bold text-gray-900">Eng ko&apos;p sotilgan mahsulotlar (TOP 10)</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mahsulot</th>
                  <th className="text-center">Sotilgan soni</th>
                  <th className="text-right">Tushum</th>
                  <th className="text-right">Sof foyda</th>
                </tr>
              </thead>
              <tbody>
                {salesReport?.top_products?.map((p: any, idx: number) => (
                  <tr key={idx}>
                    <td className="font-medium text-gray-900">{p.product__name}</td>
                    <td className="text-center font-bold">{p.total_qty} ta</td>
                    <td className="text-right font-semibold text-gray-700">{formatCurrency(p.total_revenue)}</td>
                    <td className="text-right font-semibold text-emerald-600">{formatCurrency(p.total_profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Inventory snapshot report */}
        <div className="card p-6 space-y-6">
          <h2 className="font-bold text-gray-900 border-b pb-3">Ombor balansi hisoboti</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-xl">
              <span className="text-xs text-gray-400 font-bold block">JAMI MAHSULOT TURI</span>
              <span className="text-2xl font-extrabold text-gray-900 mt-1 inline-block">
                {inventoryReport?.total_products || 0} xil
              </span>
            </div>

            <div className="p-4 bg-gray-50 rounded-xl">
              <span className="text-xs text-gray-400 font-bold block">OMBOR QOLDIQ QIYMATI</span>
              <span className="text-lg font-extrabold text-gray-900 mt-1 inline-block">
                {formatCurrency(inventoryReport?.total_stock_value || 0)}
              </span>
            </div>

            <div className="p-4 bg-red-50 rounded-xl">
              <span className="text-xs text-red-500 font-bold block">TUGAGAN MAHSULOTLAR</span>
              <span className="text-2xl font-extrabold text-red-600 mt-1 inline-block">
                {inventoryReport?.out_of_stock_count || 0} ta
              </span>
            </div>

            <div className="p-4 bg-amber-50 rounded-xl">
              <span className="text-xs text-amber-500 font-bold block">KAM QOLGANLAR</span>
              <span className="text-2xl font-extrabold text-amber-600 mt-1 inline-block">
                {inventoryReport?.low_stock_count || 0} ta
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
