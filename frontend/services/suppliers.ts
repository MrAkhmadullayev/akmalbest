import apiClient from '@/lib/api-client';
import type { Supplier, PaginatedResponse } from '@/types';

export const suppliersService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Supplier>>('/suppliers/', { params }),

  getById: (id: string) =>
    apiClient.get<Supplier>(`/suppliers/${id}/`),

  create: (data: Partial<Supplier>) =>
    apiClient.post<Supplier>('/suppliers/', data),

  update: (id: string, data: Partial<Supplier>) =>
    apiClient.patch<Supplier>(`/suppliers/${id}/`, data),
};

export const purchasesService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get('/purchases/', { params }),

  create: (data: {
    supplier: string;
    invoice_number?: string;
    purchase_date: string;
    notes?: string;
    items: Array<{ product_id: string; quantity: number; purchase_price: number }>;
  }) => apiClient.post('/purchases/', data),
};
