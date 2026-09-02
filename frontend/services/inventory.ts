import apiClient from '@/lib/api-client';
import type { InventoryItem, InventoryTransaction, PaginatedResponse, ApiResponse } from '@/types';

export const inventoryService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<InventoryItem>>('/inventory/', { params }),

  getTransactions: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<InventoryTransaction>>('/inventory/transactions/', { params }),

  adjust: (data: { product_id: string; new_quantity: number; notes?: string }) =>
    apiClient.post<ApiResponse>('/inventory/adjust/', data),
};
