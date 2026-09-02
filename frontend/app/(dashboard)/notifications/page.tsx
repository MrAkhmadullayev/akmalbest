'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsService } from '@/services/notifications';
import { formatDateTime } from '@/lib/utils';
import { Bell, Check, Trash } from 'lucide-react';

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsService.getAll({ page_size: '100' }),
  });

  const readMutation = useMutation({
    mutationFn: (id: string) => notificationsService.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
    },
  });

  const readAllMutation = useMutation({
    mutationFn: () => notificationsService.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
    },
  });

  const notifications = data?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><Bell size={24} /></span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Bildirishnomalar</h1>
            <p className="text-gray-500 mt-0.5">Tizim ogohlantirishlari, kam qolgan tovarlar va muddati o&apos;tayotgan qarzlar</p>
          </div>
        </div>
        {notifications.some((n: any) => !n.is_read) && (
          <button
            onClick={() => readAllMutation.mutate()}
            disabled={readAllMutation.isPending}
            className="btn-secondary btn-sm"
          >
            Barchasini o&apos;qildi deb belgilash
          </button>
        )}
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-8 text-gray-500">Yuklanmoqda...</div>
        ) : (
          notifications.map((n: any) => (
            <div
              key={n.id}
              className={`p-4 rounded-xl border flex items-start justify-between gap-4 transition-all ${
                n.is_read
                  ? 'bg-white border-gray-200 opacity-75'
                  : 'bg-white border-indigo-500/30 shadow-sm ring-1 ring-indigo-500/10'
              }`}
            >
              <div>
                <span className="text-xs text-gray-400 font-mono">{formatDateTime(n.created_at)}</span>
                <h3 className={`font-bold text-gray-950 mt-1 ${n.is_read ? 'font-medium' : ''}`}>
                  {n.title}
                </h3>
                <p className="text-sm text-gray-600 mt-1">{n.message}</p>
              </div>

              {!n.is_read && (
                <button
                  onClick={() => readMutation.mutate(n.id)}
                  className="p-1 text-indigo-600 hover:bg-indigo-50 rounded-lg cursor-pointer"
                  title="O'qildi deb belgilash"
                >
                  <Check size={18} />
                </button>
              )}
            </div>
          ))
        )}
        {!isLoading && notifications.length === 0 && (
          <div className="card py-16 text-center text-gray-400">
            Bildirishnomalar yo&apos;q
          </div>
        )}
      </div>
    </div>
  );
}
