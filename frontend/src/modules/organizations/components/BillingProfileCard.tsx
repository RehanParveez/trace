import { useTranslation } from "react-i18next";
import { useBillingProfile, useSetBillingProfile } from "../hooks/useBillingProfile";
import { Panel, PanelHeader, useToast } from "./OrganizationUi";

export function BillingProfileCard({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const setting = useBillingProfile();
  const update = useSetBillingProfile();
  const data = setting.data;
  return (
    <Panel>
      <PanelHeader eyebrow={t("org.billing.eyebrow", "Pricing")} title={t("org.billing.title", "Billing profile")}
        description={t("org.billing.description", "How your BOQ lines are grouped when a project is priced. A project can use another profile for one sitting.")} />
      <div className="flex flex-wrap items-center gap-3 p-5 text-[13px]">
        <select className="rounded border border-[var(--color-border)] px-2 py-1" disabled={!canManage || !data || update.isPending} value={data?.billing_profile ?? ""} data-testid="billing-profile-select"
          onChange={(e) => update.mutate(e.target.value || null, {
            onSuccess: () => showToast({ tone: "success", title: t("org.billing.saved", "Billing profile saved") }),
            onError: () => showToast({ tone: "error", title: t("org.billing.failed", "The billing profile was not saved") }),
          })}>
          <option value="">{t("org.billing.none", "None set: the software's default")}</option>
          {(data?.profiles ?? []).map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
        {data ? <span className="text-[var(--color-text-muted)]">{t("org.billing.inForce", "In force: {{id}}", { id: data.effective })}</span> : null}
      </div>
    </Panel>
  );
}
