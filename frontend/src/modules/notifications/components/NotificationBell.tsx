import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../../organizations/components/OrganizationUi";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications, useUnreadCount } from "../hooks";
import { formatNotificationTime, getNotificationIcon } from "../utils/notification.utils";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const unreadCountQuery = useUnreadCount();
  const notificationsQuery = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const unreadCount = unreadCountQuery.data?.unread_count ?? 0;
  const notifications = notificationsQuery.data ?? [];

  useEffect(() => {
    if (!open) return;
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleClick(notificationId: string, linkPath: string | null, isRead: boolean) {
    if (!isRead) markRead.mutate(notificationId);
    setOpen(false);
    if (linkPath) navigate(linkPath);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-muted)]"
      >
        <Icon name="mail" size={15} />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[var(--color-danger)] px-1 font-mono text-[9px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 top-[calc(100%+8px)] z-40 w-[340px] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[0_16px_40px_rgba(8,13,24,0.14)]">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
            <span className="text-[13px] font-bold text-[var(--color-text-primary)]">Notifications</span>
              {unreadCount > 0 ? (
               <button type="button" onClick={() => markAllRead.mutate()} className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline">
                 Mark all read
               </button>
            ) : null}
</div>

          <div className="max-h-[380px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-[13px] text-[var(--color-text-secondary)]">You're all caught up.</div>
            ) : (
              notifications.map((notification) => (
                <button
                  key={notification.id}
                  type="button"
                  onClick={() => handleClick(notification.id, notification.link_path, notification.is_read)}
                  className={`flex w-full items-start gap-3 border-b border-[var(--color-border)] px-4 py-3 text-left transition hover:bg-[var(--color-surface-muted)] ${notification.is_read ? "" : "bg-[var(--color-warning-bg)]"}`}
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
                    <Icon name={getNotificationIcon(notification.type)} size={13} />
                  </div>
                  <div className="min-w-0 flex-1">
                   <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">{notification.title}</div>
                   {notification.body ? <div className="mt-0.5 truncate text-[12px] text-[var(--color-text-secondary)]">{notification.body}</div> : null}
                   <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">{formatNotificationTime(notification.created_at)}</div>
                  </div>
                  {!notification.is_read ? <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-trace-gold)]" /> : null}
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}