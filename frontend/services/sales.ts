import apiClient from '@/lib/api-client';
import type { Sale, PaginatedResponse, ApiResponse } from '@/types';

export interface CreateSalePayload {
  items: Array<{
    product_id: string;
    quantity: number;
    discount?: number;
  }>;
  payment_method: 'CASH' | 'CARD' | 'DEBT';
  customer_id?: string | null;
  customer_name?: string;
  customer_phone?: string;
  discount?: number;
  paid_amount?: number | null;
  due_date?: string | null;
}

export const salesService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Sale>>('/sales/', { params }),

  getById: (id: string) =>
    apiClient.get<Sale>(`/sales/${id}/`),

  create: (data: CreateSalePayload) =>
    apiClient.post<ApiResponse<Sale> & { change_amount: string }>('/sales/', data),

  returnItem: (saleId: string, data: { sale_item_id: string; return_quantity: number }) =>
    apiClient.post<ApiResponse>(`/sales/${saleId}/return/`, data),

  cancel: (saleId: string) =>
    apiClient.post<ApiResponse>(`/sales/${saleId}/cancel/`),
};
