import apiClient from '@/lib/api-client';
import type { Notification, PaginatedResponse } from '@/types';

export const notificationsService = {
  getAll: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<Notification>>('/notifications/', { params }),

  markAsRead: (id: string) =>
    apiClient.post(`/notifications/${id}/read/`),

  markAllAsRead: () =>
    apiClient.post('/notifications/read-all/'),

  getUnreadCount: () =>
    apiClient.get<{ count: number }>('/notifications/unread-count/'),
};
