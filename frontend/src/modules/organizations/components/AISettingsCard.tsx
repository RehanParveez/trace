import { useState } from "react";
import {Badge, Button, Icon, Modal, Panel, PanelHeader, Toggle,
} from "./OrganizationUi";
import { useTranslation } from "react-i18next";

interface AISettingsCardProps {
  enabled: boolean;
  isUpdating?: boolean;
  canManage?: boolean;
  onChange: (enabled: boolean) => void;
}

const AI_CAPABILITIES = [
  "dashboard.ai.cap.drawing",
  "dashboard.ai.cap.boq",
  "dashboard.ai.cap.progress",
];

export function AISettingsCard({
  enabled,
  isUpdating = false,
  canManage = false,
  onChange,
}: AISettingsCardProps) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);

  const nextEnabled = !enabled;

  function requestChange() {
    if (!canManage || isUpdating) {
      return;
    }

    setConfirming(true);
  }

  function confirmChange() {
    setConfirming(false);
    onChange(nextEnabled);
  }

  return (
    <>
      <Panel>
        <PanelHeader
         eyebrow={t("dashboard.ai.eyebrow")}
         title={t("dashboard.ai.title")}
         description={t("dashboard.ai.description")}
         action={
          <Badge tone={enabled ? "green" : "slate"}>
           {enabled ? t("org.header.enabled") : t("org.header.disabled")}
          </Badge>
         }
      />

        <div className="grid gap-5 p-5 md:grid-cols-[1fr_auto] md:items-center">
          <div className="flex gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
              <Icon name="spark" size={16} />
            </div>

            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                {enabled ? t("dashboard.ai.available") : t("dashboard.ai.off")}
              </div>

              <p className="mt-1 max-w-2xl text-[12.5px] leading-5 text-[var(--color-text-secondary)]">
                {enabled
                  ? "Organization-approved AI features may process supported project content. Generated output must remain a suggestion until a human confirms it."
                  : "No organization AI processing is enabled. Turn it on only when your team is comfortable with the configured AI processing path."}
              </p>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {AI_CAPABILITIES.map((capability) => (
                  <span
                    key={capability}
                    className={`rounded-full border px-2.5 py-1 text-[10.5px] font-medium ${
                      enabled
                        ? "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-primary)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]"
                    }`}
                  >
                    {capability}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 md:justify-end">
            <span className="text-[11px] font-semibold text-[#6b6152] md:hidden">
              {isUpdating ? t("dashboard.ai.updating") : enabled ? t("org.header.enabled") : t("org.header.disabled")}
            </span>

            <Toggle
              checked={enabled}
              onChange={requestChange}
              disabled={!canManage || isUpdating}
              label={t("dashboard.ai.toggleLabel")}
            />
          </div>
        </div>

        {!canManage ? (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3 text-[12px] text-[var(--color-text-secondary)]">
            {t("dashboard.ai.viewOnly")}
          </div>
        ) : null}
      </Panel>

      {confirming ? (
        <Modal
          title={ nextEnabled ? t("dashboard.ai.enableTitle") : t("dashboard.ai.disableTitle") }
          onClose={() => setConfirming(false)}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
            <Icon name="spark" size={16} />
          </div>

          <p className="mt-4 text-[13px] leading-5 text-[var(--color-text-secondary)]">
            {nextEnabled ? t("dashboard.ai.enableBody") : t("dashboard.ai.disableBody")}
          </p>

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>

            <Button
              variant={nextEnabled ? "primary" : "danger"}
              onClick={confirmChange}
            >
              {nextEnabled ? t("dashboard.ai.enableConfirm") : t("dashboard.ai.disableConfirm")}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
