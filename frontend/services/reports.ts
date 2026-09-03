import apiClient from '@/lib/api-client';
import type { DashboardData } from '@/types';

export const reportsService = {
  getDashboard: () =>
    apiClient.get<DashboardData>('/reports/dashboard/'),

  getSalesReport: (params?: Record<string, string>) =>
    apiClient.get('/reports/sales/', { params }),

  getProfitReport: (params?: Record<string, string>) =>
    apiClient.get('/reports/profit/', { params }),

  getInventoryReport: () =>
    apiClient.get('/reports/inventory/'),

  getDebtReport: () =>
    apiClient.get('/reports/debts/'),

  closeShift: () =>
    apiClient.post('/reports/close-shift/'),

  getShifts: () =>
    apiClient.get('/reports/shifts/'),
};
