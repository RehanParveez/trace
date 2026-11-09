import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Icon, Modal, Panel, PanelHeader } from "./OrganizationUi";
import type { LearningConsent } from "../types/organization.types";

interface LearningConsentCardProps {
  value: LearningConsent;
  isUpdating?: boolean;
  canManage?: boolean;
  onChange: (value: LearningConsent) => void;
}

const CHOICES: LearningConsent[] = ["OFF", "OWN", "SHARED"];

export function LearningConsentCard({ value, isUpdating = false, canManage = false, onChange }: LearningConsentCardProps) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<LearningConsent | null>(null);

  function pick(choice: LearningConsent) {
    if (!canManage || isUpdating || choice === value) {
      return;
    }
    setPending(choice);
  }

  function confirm() {
    if (pending) {
      onChange(pending);
    }
    setPending(null);
  }

  return (
    <>
      <Panel data-testid="learning-consent-card">
        <PanelHeader
          eyebrow={t("org.learning.eyebrow")}
          title={t("org.learning.title")}
          description={t("org.learning.description")}
          action={<Badge tone={value === "OFF" ? "slate" : value === "OWN" ? "blue" : "green"}>{t(`org.learning.state.${value}`)}</Badge>}
        />

        <div className="grid gap-3 p-5 md:grid-cols-3" role="radiogroup" aria-label={t("org.learning.title")}>
          {CHOICES.map((choice) => {
            const selected = choice === value;
            return (
              <button
                key={choice}
                type="button"
                role="radio"
                aria-checked={selected}
                disabled={!canManage || isUpdating}
                onClick={() => pick(choice)}
                data-testid={`learning-consent-${choice}`}
                className={`rounded-[var(--radius-lg)] border p-4 text-start transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  selected
                    ? "border-[var(--color-trace-gold-dark)] bg-[var(--color-warning-bg)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)]"
                }`}
              >
                <div className="flex items-center gap-2 text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                  <Icon name="spark" size={14} />
                  {t(`org.learning.choice.${choice}`)}
                </div>
                <p className="mt-2 text-[12.5px] leading-5 text-[var(--color-text-secondary)]">{t(`org.learning.choiceDesc.${choice}`)}</p>
              </button>
            );
          })}
        </div>

        {!canManage ? (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3 text-[12px] text-[var(--color-text-secondary)]">
            {t("org.learning.viewOnly")}
          </div>
        ) : null}
      </Panel>

      {pending ? (
        <Modal title={t(`org.learning.confirmTitle.${pending}`)} onClose={() => setPending(null)}>
          <p className="text-[13px] leading-5 text-[var(--color-text-secondary)]">{t(`org.learning.confirmBody.${pending}`)}</p>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setPending(null)}>
              {t("common.cancel")}
            </Button>
            <Button variant={pending === "OFF" ? "danger" : "primary"} onClick={confirm}>
              {t(`org.learning.confirm.${pending}`)}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
