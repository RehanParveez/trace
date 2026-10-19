import { useState } from "react";
import { useTranslation } from "react-i18next";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import {Badge, Button, EmptyState, ErrorState, Field, Icon, LoadingState, Modal, PageHeader, Panel, PanelHeader, inputClass, useToast,
} from "../../organizations/components/OrganizationUi";
import {useCancelDeletion, useCreateSupportGrant, useDownloadExport, useExports, usePrivacyOverview, useRequestDeletion, useRequestExport, useRevokeSupportGrant, useSupportGrants,
} from "../hooks/usePrivacy";
import type {DeletionRequest, ExportJob, PrivacyOverview, SupportGrant,
} from "../types/privacy.types";

function apiMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response
    ?.data?.detail;
  return typeof detail === "string" && detail ? detail : fallback;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const ROW =
  "flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] px-5 py-3.5 first:border-t-0";

function EncryptionPanel({ overview }: { overview: PrivacyOverview }) {
  const { t } = useTranslation();
  const { encryption } = overview;

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("privacy.enc.eyebrow", "Encryption")}
        title={t("privacy.enc.title", "Encryption at rest")}
        description={t(
          "privacy.enc.desc",
          "Sensitive fields are sealed with a key unique to your organization before they reach the database.",
        )}
        action={
          <Badge tone={encryption.enabled && encryption.key_ready ? "green" : "gold"}>
            {encryption.enabled
              ? t("privacy.enc.on", "Active")
              : t("privacy.enc.off", "Not enabled")}
          </Badge>
        }
      />
      <div className="p-5 text-[13px] leading-5 text-[var(--color-text-secondary)]">
        {encryption.enabled ? (
          <>
            <p>
              {t("privacy.enc.keyLine", "Key provider")}:{" "}
              <span className="font-mono font-semibold text-[var(--color-text-primary)]">
                {encryption.provider}
              </span>
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {encryption.fields.map((field) => (
                <span
                  key={field}
                  className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[10.5px] font-medium text-[var(--color-text-primary)]"
                >
                  {field}
                </span>
              ))}
            </div>
          </>
        ) : (
          <p>
            {t(
              "privacy.enc.offBody",
              "Field-level encryption has not been switched on for this deployment yet.",
            )}
          </p>
        )}
        <p className="mt-3 text-[12px] text-[var(--color-text-muted)]">
          {t(
            "privacy.enc.note",
            "Drawings are processed on our servers to compute quantities, so this is protection from storage and staff access, not end-to-end encryption.",
          )}
        </p>
      </div>
    </Panel>
  );
}

function SupportAccessPanel({
  overview,
  canManage,
}: {
  overview: PrivacyOverview;
  canManage: boolean;
}) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const grantsQuery = useSupportGrants();
  const createGrant = useCreateSupportGrant();
  const revokeGrant = useRevokeSupportGrant();

  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [hours, setHours] = useState(24);

  const active = overview.active_support_grant;
  const maxHours = overview.support_grant_max_hours;
  const reasonValid = reason.trim().length >= 10;

  function submit() {
    createGrant.mutate(
      { reason: reason.trim(), hours },
      {
        onSuccess: () => {
          setOpen(false);
          setReason("");
          showToast({ tone: "success", title: t("privacy.sup.granted", "Support access granted") });
        },
        onError: (error) =>
          showToast({
            tone: "error",
            title: t("privacy.sup.grantFailed", "Could not grant access"),
            description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
          }),
      },
    );
  }

  function revoke(grant: SupportGrant) {
    revokeGrant.mutate(grant.id, {
      onSuccess: () =>
        showToast({ tone: "success", title: t("privacy.sup.revoked", "Support access revoked") }),
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("privacy.sup.revokeFailed", "Could not revoke access"),
          description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
        }),
    });
  }

  const grants = grantsQuery.data ?? [];

  return (
    <>
      <Panel>
        <PanelHeader
          eyebrow={t("privacy.sup.eyebrow", "Support access")}
          title={t("privacy.sup.title", "Who can see your data")}
          description={t(
            "privacy.sup.desc",
            "By default nobody at Trace can open your projects, drawings or BOQs. Grant time-limited, read-only access only when you want help, and revoke it at any moment.",
          )}
          action={
            <Badge tone={active ? "gold" : "green"}>
              {active
                ? t("privacy.sup.open", "Access open")
                : t("privacy.sup.closed", "No access")}
            </Badge>
          }
        />

        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] p-5">
          <div className="min-w-0 text-[13px] text-[var(--color-text-secondary)]">
            {active ? (
              <>
                {t("privacy.sup.expires", "Trace support can read your data until")}{" "}
                <span className="font-semibold text-[var(--color-text-primary)]">
                  {formatDate(active.expires_at)}
                </span>
                .
              </>
            ) : (
              t("privacy.sup.none", "No support grant is currently active.")
            )}
          </div>
          {canManage ? (
            active ? (
              <Button
                variant="danger"
                disabled={revokeGrant.isPending}
                onClick={() => revoke(active)}
              >
                {t("privacy.sup.revokeNow", "Revoke now")}
              </Button>
            ) : (
              <Button variant="primary" onClick={() => setOpen(true)}>
                <Icon name="key" size={14} />
                {t("privacy.sup.grant", "Grant support access")}
              </Button>
            )
          ) : null}
        </div>

        {grantsQuery.isLoading ? (
          <div className="p-5 text-[12.5px] text-[var(--color-text-muted)]">
            {t("privacy.loading", "Loading…")}
          </div>
        ) : grants.length === 0 ? (
          <EmptyState
            icon="shield"
            title={t("privacy.sup.emptyTitle", "No access has ever been granted")}
            description={t(
              "privacy.sup.emptyBody",
              "Every grant and every support read is recorded in your audit log.",
            )}
          />
        ) : (
          <div>
            {grants.map((grant) => (
              <div key={grant.id} className={ROW}>
                <div className="min-w-0">
                  <div className="truncate text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {grant.reason}
                  </div>
                  <div className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">
                    {formatDate(grant.starts_at)} → {formatDate(grant.expires_at)}
                  </div>
                </div>
                <Badge
                  tone={
                    grant.status === "ACTIVE"
                      ? "gold"
                      : grant.status === "REVOKED"
                        ? "red"
                        : "slate"
                  }
                >
                  {grant.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {open ? (
        <Modal
          title={t("privacy.sup.modalTitle", "Grant support access")}
          description={t(
            "privacy.sup.modalDesc",
            "Read-only. Expires automatically. You can revoke it at any time.",
          )}
          onClose={() => setOpen(false)}
        >
          <div className="space-y-4">
            <Field
              label={t("privacy.sup.reason", "Reason")}
              hint={t("privacy.sup.reasonHint", "At least 10 characters. Shown in your audit log.")}
            >
              <textarea
                className={inputClass}
                rows={3}
                maxLength={500}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </Field>
            <Field
              label={t("privacy.sup.duration", "Duration (hours)")}
              hint={`${t("privacy.sup.max", "Maximum")}: ${maxHours}`}
            >
              <input
                type="number"
                className={inputClass}
                min={1}
                max={maxHours}
                value={hours}
                onChange={(event) =>
                  setHours(Math.min(maxHours, Math.max(1, Number(event.target.value) || 1)))
                }
              />
            </Field>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              variant="primary"
              disabled={!reasonValid || createGrant.isPending}
              onClick={submit}
            >
              {t("privacy.sup.confirm", "Grant access")}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

function exportTone(status: ExportJob["status"]): "green" | "red" | "blue" | "slate" {
  if (status === "COMPLETED") return "green";
  if (status === "FAILED") return "red";
  if (status === "QUEUED" || status === "RUNNING") return "blue";
  return "slate";
}

function ExportPanel({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const exportsQuery = useExports();
  const requestExport = useRequestExport();
  const download = useDownloadExport();

  const jobs = exportsQuery.data ?? [];
  const busy = jobs.some((job) => job.status === "QUEUED" || job.status === "RUNNING");

  function start() {
    requestExport.mutate(undefined, {
      onSuccess: () =>
        showToast({
          tone: "success",
          title: t("privacy.exp.started", "Export started"),
          description: t("privacy.exp.startedBody", "We will have it ready in a few minutes."),
        }),
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("privacy.exp.failed", "Could not start export"),
          description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
        }),
    });
  }

  function fetchFile(job: ExportJob) {
    download.mutate(job.id, {
      onSuccess: (result) => {
        window.location.assign(result.url);
      },
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("privacy.exp.downloadFailed", "Could not prepare download"),
          description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
        }),
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("privacy.exp.eyebrow", "Your data")}
        title={t("privacy.exp.title", "Export everything")}
        description={t(
          "privacy.exp.desc",
          "Download a complete copy of your organization's data and uploaded files. Download links are short-lived.",
        )}
        action={
          canManage ? (
            <Button variant="primary" disabled={busy || requestExport.isPending} onClick={start}>
              <Icon name="download" size={14} />
              {t("privacy.exp.request", "Request export")}
            </Button>
          ) : undefined
        }
      />
      {exportsQuery.isLoading ? (
        <div className="p-5 text-[12.5px] text-[var(--color-text-muted)]">
          {t("privacy.loading", "Loading…")}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          icon="download"
          title={t("privacy.exp.emptyTitle", "No exports yet")}
          description={t("privacy.exp.emptyBody", "Request one to get a full archive of your data.")}
        />
      ) : (
        <div>
          {jobs.map((job) => (
            <div key={job.id} className={ROW}>
              <div className="min-w-0">
                <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                  {formatDate(job.created_at)}
                </div>
                <div className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">
                  {job.status === "COMPLETED"
                    ? `${formatBytes(job.size_bytes)} · ${job.row_count ?? 0} rows · ${job.file_count ?? 0} files · expires ${formatDate(job.expires_at)}`
                    : job.status === "FAILED"
                      ? (job.error_message ?? t("privacy.exp.genericFail", "The export failed."))
                      : t("privacy.exp.working", "Building your archive…")}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={exportTone(job.status)}>{job.status}</Badge>
                {job.status === "COMPLETED" && canManage ? (
                  <Button size="sm" disabled={download.isPending} onClick={() => fetchFile(job)}>
                    {t("privacy.exp.download", "Download")}
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function DeletionPanel({
  overview,
  canManage,
}: {
  overview: PrivacyOverview;
  canManage: boolean;
}) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const requestDeletion = useRequestDeletion();
  const cancelDeletion = useCancelDeletion();

  const [open, setOpen] = useState(false);
  const [confirmName, setConfirmName] = useState("");
  const [reason, setReason] = useState("");

  const pending: DeletionRequest | null = overview.pending_deletion;
  const nameMatches = confirmName.trim() === overview.organization_name;

  function submit() {
    requestDeletion.mutate(
      { confirm_name: confirmName.trim(), reason: reason.trim() || null },
      {
        onSuccess: () => {
          setOpen(false);
          setConfirmName("");
          setReason("");
          showToast({
            tone: "info",
            title: t("privacy.del.scheduled", "Deletion scheduled"),
            description: t("privacy.del.scheduledBody", "You can still cancel before the deadline."),
          });
        },
        onError: (error) =>
          showToast({
            tone: "error",
            title: t("privacy.del.failed", "Could not schedule deletion"),
            description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
          }),
      },
    );
  }

  function cancel() {
    cancelDeletion.mutate(undefined, {
      onSuccess: () =>
        showToast({ tone: "success", title: t("privacy.del.cancelled", "Deletion cancelled") }),
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("privacy.del.cancelFailed", "Could not cancel"),
          description: apiMessage(error, t("privacy.tryAgain", "Please try again.")),
        }),
    });
  }

  return (
    <>
      <Panel>
        <PanelHeader
          eyebrow={t("privacy.del.eyebrow", "Danger zone")}
          title={t("privacy.del.title", "Delete organization")}
          description={t(
            "privacy.del.desc",
            "Permanently erases every project, drawing, BOQ, file and member record, and destroys your encryption key. This cannot be undone once the grace period ends.",
          )}
          action={pending ? <Badge tone="red">{t("privacy.del.pending", "Scheduled")}</Badge> : undefined}
        />
        <div className="flex flex-wrap items-center justify-between gap-3 p-5">
          <div className="min-w-0 text-[13px] text-[var(--color-text-secondary)]">
            {pending ? (
              <>
                {t("privacy.del.runsOn", "Everything will be erased on")}{" "}
                <span className="font-semibold text-[var(--color-danger)]">
                  {formatDate(pending.scheduled_for)}
                </span>
                . {t("privacy.del.cancelHint", "Cancel before then to keep your data.")}
              </>
            ) : (
              `${t("privacy.del.grace", "After you confirm, there is a grace period of")} ${overview.grace_days} ${t("privacy.del.days", "days before anything is erased.")}`
            )}
          </div>
          {canManage ? (
            pending ? (
              <Button disabled={cancelDeletion.isPending} onClick={cancel}>
                {t("privacy.del.cancel", "Cancel deletion")}
              </Button>
            ) : (
              <Button variant="danger" onClick={() => setOpen(true)}>
                {t("privacy.del.start", "Delete organization")}
              </Button>
            )
          ) : null}
        </div>
      </Panel>

      {open ? (
        <Modal
          title={t("privacy.del.modalTitle", "Delete this organization?")}
          onClose={() => setOpen(false)}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[var(--color-danger-bg)] text-[var(--color-danger)]">
            <Icon name="alert" size={16} />
          </div>
          <p className="mt-4 text-[13px] leading-5 text-[var(--color-text-secondary)]">
            {t(
              "privacy.del.modalBody",
              "Export your data first if you need a copy. Type the organization name to confirm.",
            )}
          </p>
          <div className="mt-4 space-y-4">
            <Field label={`${t("privacy.del.typeName", "Type")} “${overview.organization_name}”`}>
              <input
                className={inputClass}
                value={confirmName}
                onChange={(event) => setConfirmName(event.target.value)}
                autoComplete="off"
              />
            </Field>
            <Field label={t("privacy.del.reason", "Reason (optional)")}>
              <textarea
                className={inputClass}
                rows={2}
                maxLength={1000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </Field>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              variant="danger"
              disabled={!nameMatches || requestDeletion.isPending}
              onClick={submit}
            >
              {t("privacy.del.confirm", "Schedule deletion")}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

export function DataPrivacyPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const overviewQuery = usePrivacyOverview();

  const canManage = permissions.includes(IDENTITY_PERMISSIONS.ORGANIZATION_MANAGE);

  if (overviewQuery.isLoading) {
    return <LoadingState />;
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <ErrorState
        title={t("privacy.loadFailed", "We couldn't load your privacy settings")}
        description={
          canManage
            ? undefined
            : t("privacy.needManage", "You need the organization manage permission to view this page.")
        }
        onRetry={() => void overviewQuery.refetch()}
      />
    );
  }

  const overview = overviewQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("privacy.eyebrow", "DATA & PRIVACY")}
        title={t("privacy.pageTitle", "Data privacy")}
        description={t(
          "privacy.pageDesc",
          "You decide who can see your data, you can take a full copy at any time, and you can have it erased.",
        )}
      />
      <SupportAccessPanel overview={overview} canManage={canManage} />
      <EncryptionPanel overview={overview} />
      <ExportPanel canManage={canManage} />
      <DeletionPanel overview={overview} canManage={canManage} />
    </div>
  );
}
