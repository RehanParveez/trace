import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, EmptyState, Field, inputClass, Panel, PanelHeader, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useProjects } from "../../projects";
import { useCreateWhatsAppSender, useDeleteWhatsAppSender, useUpdateWhatsAppSender, useWhatsAppSenders } from "../hooks";
import { useTranslation } from "react-i18next";

export function SendersPanel() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const sendersQuery = useWhatsAppSenders();
  const projectsQuery = useProjects();
  const createSender = useCreateWhatsAppSender();
  const updateSender = useUpdateWhatsAppSender();
  const deleteSender = useDeleteWhatsAppSender();

  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const senders = sendersQuery.data ?? [];
  const projects = projectsQuery.data ?? [];
  const projectName = (id: string | null) => projects.find((p) => p.id === id)?.name ?? "—";

  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createSender.mutate(
      { phone_number: phone.trim(), display_name: name.trim(), default_project_id: projectId || null },
      {
        onSuccess: () => {
          setPhone("");
          setName("");
          setProjectId("");
          showToast({ tone: "success", title: t("whatsapp.senders.added") });
        },
        onError: (err) => setError(getApiErrorMessage(err, t("whatsapp.senders.addError"))),
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("whatsapp.senders.eyebrow")}
        title={t("whatsapp.senders.title")}
        description={senders.length === 0 ? t("whatsapp.senders.openDescription") : t("whatsapp.senders.restrictedDescription")}
      />

      <div className="space-y-5 p-5">
        <form onSubmit={add} className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
          <Field label={t("whatsapp.senders.phone")} hint={t("whatsapp.senders.phoneHint")}>
            <input required className={inputClass} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="0300 1234567" inputMode="tel" />
          </Field>
          <Field label={t("whatsapp.senders.name")}>
            <input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder={t("whatsapp.senders.namePlaceholder")} />
          </Field>
          <Field label={t("whatsapp.senders.defaultProject")} hint={t("whatsapp.senders.defaultProjectHint")}>
            <select className={inputClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">{t("whatsapp.senders.noDefault")}</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Button type="submit" variant="primary" disabled={createSender.isPending || !phone.trim() || !name.trim()}>{t("whatsapp.senders.add")}</Button>
        </form>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        {senders.length === 0 ? (
          <EmptyState icon="users" title={t("whatsapp.senders.emptyTitle")} description={t("whatsapp.senders.emptyDesc")} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[620px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                  <th className="px-4 py-3">{t("whatsapp.senders.name")}</th>
                  <th className="px-4 py-3">{t("whatsapp.senders.phone")}</th>
                  <th className="px-4 py-3">{t("whatsapp.senders.defaultProject")}</th>
                  <th className="px-4 py-3">{t("whatsapp.senders.status")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {senders.map((sender) => (
                  <tr key={sender.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13px] font-medium text-[var(--color-text-primary)]">{sender.display_name}</td>
                    <td className="px-4 py-3.5 font-mono text-[12.5px] text-[var(--color-text-secondary)]">{sender.phone_number}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">
                      <select
                        className={`${inputClass} !h-8`}
                        value={sender.default_project_id ?? ""}
                        onChange={(e) =>
                          updateSender.mutate({
                            senderId: sender.id,
                            payload: e.target.value ? { default_project_id: e.target.value } : { clear_default_project: true },
                          })
                        }
                      >
                        <option value="">{projectName(null)}</option>
                        {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3.5">
                      <button type="button" onClick={() => updateSender.mutate({ senderId: sender.id, payload: { is_active: !sender.is_active } })}>
                        <Badge tone={sender.is_active ? "green" : "slate"}>{sender.is_active ? t("whatsapp.senders.active") : t("whatsapp.senders.paused")}</Badge>
                      </button>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deleteSender.isPending}
                        onClick={() => {
                          if (window.confirm(t("whatsapp.senders.removeConfirm", { name: sender.display_name }))) {
                            deleteSender.mutate(sender.id, {
                              onError: (err) => showToast({ tone: "error", title: t("whatsapp.senders.removeError"), description: getApiErrorMessage(err, t("common.tryAgain")) }),
                            });
                          }
                        }}
                      >
                        {t("common.delete")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </div>
    </Panel>
  );
}