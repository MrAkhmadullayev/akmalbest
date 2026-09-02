import apiClient from '@/lib/api-client';
import type { Expense, ExpenseCategory, PaginatedResponse } from '@/types';

export const expensesService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Expense>>('/expenses/', { params }),

  create: (data: Partial<Expense>) =>
    apiClient.post<Expense>('/expenses/', data),

  getCategories: () =>
    apiClient.get<PaginatedResponse<ExpenseCategory>>('/expense-categories/'),

  createCategory: (data: { name: string }) =>
    apiClient.post<ExpenseCategory>('/expense-categories/', data),
};
