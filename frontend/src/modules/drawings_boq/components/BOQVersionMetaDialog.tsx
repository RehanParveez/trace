import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useUpdateBOQVersion } from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { BOQVersion } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface BOQVersionMetaDialogProps {
  projectId: string;
  version: BOQVersion;
  onClose: () => void;
}

export function BOQVersionMetaDialog({ projectId, version, onClose }: BOQVersionMetaDialogProps) {
  const { t } = useTranslation();
  const updateVersion = useUpdateBOQVersion(projectId);
  const { showToast } = useToast();
  const meta = version.export_meta ?? {};

  const [coveredArea, setCoveredArea] = useState(version.covered_area_sqft !== null ? String(version.covered_area_sqft) : "");
  const [companyName, setCompanyName] = useState(meta.company_name ?? "");
  const [clientName, setClientName] = useState(meta.client_name ?? "");
  const [projectTitle, setProjectTitle] = useState(meta.project_title ?? "");
  const [location, setLocation] = useState(meta.location ?? "");
  const [plotSize, setPlotSize] = useState(meta.plot_size ?? "");
  const [storeys, setStoreys] = useState(meta.storeys ?? "");
  const [preparedBy, setPreparedBy] = useState(meta.prepared_by ?? "");
  const [checkedBy, setCheckedBy] = useState(meta.checked_by ?? "");
  const [error, setError] = useState<string | null>(null);

  const cls = "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    updateVersion.mutate(
      {
        boqVersionId: version.id,
        payload: {
          covered_area_sqft: coveredArea === "" ? null : Number(coveredArea),
          export_meta: {
            company_name: companyName.trim() || null,
            client_name: clientName.trim() || null,
            project_title: projectTitle.trim() || null,
            location: location.trim() || null,
            plot_size: plotSize.trim() || null,
            storeys: storeys.trim() || null,
            prepared_by: preparedBy.trim() || null,
            checked_by: checkedBy.trim() || null,
          },
        },
      },
      {
        onSuccess: () => {
          onClose();
          showToast({
            tone: "success",
            title: t("boq.meta.savedToast"),
          });
        },
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("boq.meta.saveError"))),
      },
    );
  }

  return (
    <Modal title={t("boq.meta.title")} description={t("boq.meta.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.companyName")}</span>
            <input className={cls} value={companyName} onChange={(e) => setCompanyName(e.target.value)} placeholder={t("boq.meta.companyNamePlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.clientName")}</span>
            <input className={cls} value={clientName} onChange={(e) => setClientName(e.target.value)} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.projectTitle")}</span>
            <input className={cls} value={projectTitle} onChange={(e) => setProjectTitle(e.target.value)} placeholder={t("boq.meta.projectTitlePlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.location")}</span>
            <input className={cls} value={location} onChange={(e) => setLocation(e.target.value)} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.plotSize")}</span>
            <input className={cls} value={plotSize} onChange={(e) => setPlotSize(e.target.value)} placeholder={t("boq.meta.plotSizePlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.storeys")}</span>
            <input className={cls} value={storeys} onChange={(e) => setStoreys(e.target.value)} placeholder={t("boq.meta.storeysPlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.coveredArea")}</span>
            <input className={cls} type="number" step="any" value={coveredArea} onChange={(e) => setCoveredArea(e.target.value)} />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3 border-t border-[#e1d5bc] pt-3">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.preparedBy")}</span>
            <input className={cls} value={preparedBy} onChange={(e) => setPreparedBy(e.target.value)} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.meta.checkedBy")}</span>
            <input className={cls} value={checkedBy} onChange={(e) => setCheckedBy(e.target.value)} />
          </label>
        </div>

        {error ? <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={updateVersion.isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={updateVersion.isPending}>
            {updateVersion.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}