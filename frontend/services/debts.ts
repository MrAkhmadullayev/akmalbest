import apiClient from '@/lib/api-client';
import type { Debt, DebtPayment, PaginatedResponse, ApiResponse } from '@/types';

export const debtsService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Debt>>('/debts/', { params }),

  getById: (id: string) =>
    apiClient.get<Debt>(`/debts/${id}/`),

  makePayment: (data: {
    debt_id: string;
    amount: number;
    payment_method: string;
    notes?: string;
  }) => apiClient.post<ApiResponse<DebtPayment>>('/debt-payments/create/', data),

  getNotifications: () =>
    apiClient.get<ApiResponse<{ due_debts_count: number }>>('/debts/notifications/'),
};
