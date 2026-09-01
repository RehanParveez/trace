import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, EmptyState, ErrorState, Icon, LoadingState, PageHeader, Panel } from "../../organizations/components/OrganizationUi";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications } from "../hooks";
import { formatNotificationTime, getNotificationIcon } from "../utils/notification.utils";

export function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const notificationsQuery = useNotifications(unreadOnly);
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const navigate = useNavigate();

  if (notificationsQuery.isLoading) return <LoadingState label="Loading notifications…" />;
  if (notificationsQuery.isError) return <ErrorState title="Couldn't load notifications" onRetry={() => void notificationsQuery.refetch()} />;

  const notifications = notificationsQuery.data ?? [];

  return (
    <div className="space-y-7">
      <PageHeader
        title="Notifications"
        description="Updates across your projects — drawing parsing, BOQ approvals, progress claims and account activity."
        actions={
          <button type="button" onClick={() => markAllRead.mutate()} className="text-[11px] font-semibold text-[#b98626] hover:text-[#9a6f1c]">
            Mark all read
          </button>
        }
      />

      <div className="flex gap-2">
        {([false, true] as const).map((value) => (
          <button
            key={String(value)}
            type="button"
            onClick={() => setUnreadOnly(value)}
            className={`rounded-[7px] border px-3 py-1.5 text-[10.5px] font-semibold transition ${
              unreadOnly === value ? "border-[#d9a441] bg-[#fbefd9] text-[#76531a]" : "border-[#e1d5bc] bg-white text-[#6b6152] hover:border-[#cdbd9c]"
            }`}
          >
            {value ? "Unread" : "All"}
          </button>
        ))}
      </div>

      <Panel className="overflow-hidden">
        {notifications.length === 0 ? (
          <EmptyState icon="mail" title="Nothing here" description="You're fully caught up." />
        ) : (
          <div className="divide-y divide-[#e1d5bc]">
            {notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => {
                  if (!notification.is_read) markRead.mutate(notification.id);
                  if (notification.link_path) navigate(notification.link_path);
                }}
                className={`flex w-full items-start gap-3.5 p-4 text-left transition hover:bg-[#f5efe3] ${notification.is_read ? "" : "bg-[#fffaf0]"}`}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[#fbefd9] text-[#b98626]">
                  <Icon name={getNotificationIcon(notification.type)} size={15} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[12.5px] font-semibold text-[#191410]">{notification.title}</span>
                    {!notification.is_read ? <Badge tone="gold">New</Badge> : null}
                  </div>
                  {notification.body ? <div className="mt-1 text-[11px] text-[#6b6152]">{notification.body}</div> : null}
                  <div className="mt-1.5 text-[10px] text-[#a2957c]">{formatNotificationTime(notification.created_at)}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}