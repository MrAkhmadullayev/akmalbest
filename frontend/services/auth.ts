import apiClient from '@/lib/api-client';
import type { User, LoginResponse, PaginatedResponse } from '@/types';

export const authService = {
  login: (data: { username: string; password: string }) =>
    apiClient.post<LoginResponse>('/auth/login/', data),

  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh/', { refresh: refreshToken }),

  logout: (refreshToken: string) =>
    apiClient.post('/auth/logout/', { refresh: refreshToken }),

  me: () =>
    apiClient.get<User>('/auth/me/'),
};

export const usersService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<User>>('/auth/users/', { params }),

  create: (data: Record<string, unknown>) =>
    apiClient.post('/auth/users/', data),

  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/auth/users/${id}/`, data),

  delete: (id: string) =>
    apiClient.delete(`/auth/users/${id}/`),
};
