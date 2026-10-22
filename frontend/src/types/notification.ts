export interface NotificationResponse {
  id: string;
  company_id: string;
  tender_id?: string | null;
  notification_type: 'DEADLINE_48H' | 'DEADLINE_OVERDUE' | 'REQUIREMENTS_UPDATED';
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  tender_title?: string | null;
  submission_deadline?: string | null;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
