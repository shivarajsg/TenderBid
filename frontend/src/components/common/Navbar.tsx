import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { notificationsApi } from '../../api/notificationsApi';
import { NotificationResponse } from '../../types/notification';
import {
  LogOut,
  User as UserIcon,
  Shield,
  FileCheck2,
  Bell,
  Check,
  CheckCheck,
  Clock,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';
import { Button } from './Button';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<NotificationResponse[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const fetchUnread = async () => {
    if (!user) return;
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch {
      // Ignore background badge errors
    }
  };

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      const res = await notificationsApi.listNotifications();
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // Ignore error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 45000); // Poll count every 45s
    return () => clearInterval(interval);
  }, [user]);

  const toggleDropdown = () => {
    if (!isOpen) {
      fetchNotifications();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationsApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Ignore
    }
  };

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
      <div className="px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shadow-md shadow-blue-500/20">
            <FileCheck2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-lg font-bold bg-gradient-to-r from-blue-700 to-indigo-700 bg-clip-text text-transparent">
              TenderBid AI
            </span>
            <span className="hidden sm:inline-block ml-2 text-xs font-medium text-slate-500 border-l border-slate-300 pl-2">
              MSME Tender Intelligence
            </span>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            {/* Notification Bell with Badge */}
            <div className="relative">
              <button
                onClick={toggleDropdown}
                className="relative p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none"
                title="Notifications"
                aria-label="Notifications"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown Panel */}
              {isOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-50">
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-800">Alerts & Reminders</span>
                      {unreadCount > 0 && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">
                          {unreadCount} new
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-xs text-blue-600 hover:underline font-semibold flex items-center gap-1"
                      >
                        <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                    {isLoading ? (
                      <div className="p-6 text-center text-xs text-slate-400">Loading alerts...</div>
                    ) : notifications.length === 0 ? (
                      <div className="p-8 text-center text-xs text-slate-400">
                        <Clock className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                        No alerts right now. Track tenders to receive 48h deadline reminders.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`p-3.5 text-xs transition-colors hover:bg-slate-50/80 ${
                            !n.is_read ? 'bg-blue-50/40' : 'bg-white'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-start gap-2">
                              {n.notification_type === 'DEADLINE_48H' ? (
                                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                              ) : n.notification_type === 'DEADLINE_OVERDUE' ? (
                                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                              ) : (
                                <Bell className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                              )}
                              <div>
                                <p className={`font-semibold ${!n.is_read ? 'text-slate-900' : 'text-slate-600'}`}>
                                  {n.title}
                                </p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">{n.message}</p>
                                <div className="flex items-center gap-3 mt-1.5">
                                  <span className="text-[10px] text-slate-400">
                                    {new Date(n.created_at).toLocaleDateString()}
                                  </span>
                                  {n.tender_id && (
                                    <Link
                                      to={`/tenders/${n.tender_id}`}
                                      onClick={() => setIsOpen(false)}
                                      className="text-blue-600 hover:underline font-semibold text-[10px] flex items-center gap-0.5"
                                    >
                                      View Tender <ExternalLink className="w-2.5 h-2.5" />
                                    </Link>
                                  )}
                                </div>
                              </div>
                            </div>

                            {!n.is_read && (
                              <button
                                onClick={(e) => handleMarkAsRead(n.id, e)}
                                className="text-slate-400 hover:text-blue-600 p-1"
                                title="Mark as read"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 text-center">
                    <p className="text-[10px] text-slate-400">
                      Evaluates active tracked bids against UTC closing deadlines.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                  user.role === 'ADMIN'
                    ? 'bg-purple-100 text-purple-700 border border-purple-200'
                    : 'bg-blue-100 text-blue-700 border border-blue-200'
                }`}
              >
                {user.role === 'ADMIN' ? (
                  <Shield className="w-3 h-3" />
                ) : (
                  <UserIcon className="w-3 h-3" />
                )}
                {user.role}
              </span>
              <div className="hidden md:block text-right">
                <p className="text-sm font-semibold text-slate-800">{user.full_name}</p>
                <p className="text-xs text-slate-500">{user.email}</p>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              icon={<LogOut className="w-4 h-4" />}
              onClick={logout}
              title="Sign Out"
            >
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        )}
      </div>
    </header>
  );
};

