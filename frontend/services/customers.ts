import apiClient from '@/lib/api-client';
import type { Customer, PaginatedResponse } from '@/types';

export const customersService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Customer>>('/customers/', { params }),

  getById: (id: string) =>
    apiClient.get<Customer>(`/customers/${id}/`),

  create: (data: Partial<Customer>) =>
    apiClient.post<Customer>('/customers/', data),

  update: (id: string, data: Partial<Customer>) =>
    apiClient.patch<Customer>(`/customers/${id}/`, data),
};
