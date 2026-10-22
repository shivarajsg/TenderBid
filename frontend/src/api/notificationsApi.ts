import { apiClient } from './client';
import {
  NotificationListResponse,
  NotificationResponse,
  UnreadCountResponse,
} from '../types/notification';

export const notificationsApi = {
  listNotifications: async (unreadOnly?: boolean): Promise<NotificationListResponse> => {
    const res = await apiClient.get<NotificationListResponse>('/notifications', {
      params: unreadOnly ? { unread_only: true } : undefined,
    });
    return res.data;
  },

  getUnreadCount: async (): Promise<UnreadCountResponse> => {
    const res = await apiClient.get<UnreadCountResponse>('/notifications/unread-count');
    return res.data;
  },

  markAsRead: async (notificationId: string): Promise<NotificationResponse> => {
    const res = await apiClient.patch<NotificationResponse>(`/notifications/${notificationId}/read`);
    return res.data;
  },

  markAllAsRead: async (): Promise<{ message: string }> => {
    const res = await apiClient.post<{ message: string }>('/notifications/mark-all-read');
    return res.data;
  },

  triggerDeadlineCheck: async (): Promise<{ status: string; alerts_generated: number; message: string }> => {
    const res = await apiClient.post('/notifications/trigger-check');
    return res.data;
  },
};
