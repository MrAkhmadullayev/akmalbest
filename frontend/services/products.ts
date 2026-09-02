import apiClient from '@/lib/api-client';
import type { Product, PaginatedResponse, ApiResponse } from '@/types';

export const productsService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Product>>('/products/', { params }),

  getById: (id: string) =>
    apiClient.get<Product>(`/products/${id}/`),

  getByBarcode: (barcode: string) =>
    apiClient.get<ApiResponse<Product>>(`/products/barcode/${barcode}/`),

  create: (data: FormData) =>
    apiClient.post<Product>('/products/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  update: (id: string, data: FormData) =>
    apiClient.patch<Product>(`/products/${id}/`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  delete: (id: string) =>
    apiClient.delete(`/products/${id}/`),

  addStock: (id: string, data: { quantity: number; purchase_price?: number; payment_method: string; notes?: string }) =>
    apiClient.post(`/products/${id}/add_stock/`, data),
};

export const categoriesService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<import('@/types').Category>>('/categories/', { params }),

  create: (data: { name: string; description?: string }) =>
    apiClient.post('/categories/', data),

  update: (id: string, data: { name: string; description?: string }) =>
    apiClient.patch(`/categories/${id}/`, data),

  delete: (id: string) =>
    apiClient.delete(`/categories/${id}/`),
};

export const brandsService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<import('@/types').Brand>>('/brands/', { params }),

  create: (data: { name: string; description?: string }) =>
    apiClient.post('/brands/', data),

  update: (id: string, data: { name: string; description?: string }) =>
    apiClient.patch(`/brands/${id}/`, data),

  delete: (id: string) =>
    apiClient.delete(`/brands/${id}/`),
};
