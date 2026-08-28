import { useState } from "react";
import {Badge, Button, Icon, Modal, Panel, PanelHeader, Toggle,
} from "./OrganizationUi";

interface AISettingsCardProps {
  enabled: boolean;
  isUpdating?: boolean;
  canManage?: boolean;
  onChange: (enabled: boolean) => void;
}

const AI_CAPABILITIES = [
  "Drawing tagging",
  "BOQ line suggestions",
  "Progress note summaries",
];

export function AISettingsCard({
  enabled,
  isUpdating = false,
  canManage = false,
  onChange,
}: AISettingsCardProps) {
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
          eyebrow="AI GOVERNANCE"
          title="Assistive intelligence"
          description="AI is controlled at organization level. It remains assistive and never becomes an authority for project or financial state."
          action={
            <Badge tone={enabled ? "green" : "slate"}>
              {enabled ? "Enabled" : "Disabled"}
            </Badge>
          }
        />

        <div className="grid gap-5 p-5 md:grid-cols-[1fr_auto] md:items-center">
          <div className="flex gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[#fbefd9] text-[#b98626]">
              <Icon name="spark" size={16} />
            </div>

            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[#191410]">
                {enabled ? "AI features are available" : "AI features are off"}
              </div>

              <p className="mt-1 max-w-2xl text-[11.5px] leading-5 text-[#6b6152]">
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
                        ? "border-[#e1d5bc] bg-white text-[#332a21]"
                        : "border-[#e1d5bc] bg-[#f5efe3] text-[#a2957c]"
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
              {isUpdating ? "Updating…" : enabled ? "Enabled" : "Disabled"}
            </span>

            <Toggle
              checked={enabled}
              onChange={requestChange}
              disabled={!canManage || isUpdating}
              label="Toggle organization AI features"
            />
          </div>
        </div>

        {!canManage ? (
          <div className="border-t border-[#e1d5bc] bg-[#f5efe3] px-5 py-3 text-[11px] text-[#6b6152]">
            You can view the organization setting, but only users with
            organization management permission can change it.
          </div>
        ) : null}
      </Panel>

      {confirming ? (
        <Modal
          title={
            nextEnabled
              ? "Enable AI for this organization?"
              : "Disable AI for this organization?"
          }
          onClose={() => setConfirming(false)}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[#fbefd9] text-[#b98626]">
            <Icon name="spark" size={16} />
          </div>

          <p className="mt-4 text-[12px] leading-5 text-[#6b6152]">
            {nextEnabled
              ? "This enables the organization-level AI path. Keep in mind that AI output remains assistive and must not be treated as approved business state."
              : "This stops organization-level AI features. Existing records are not deleted by this setting change."}
          </p>

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              Cancel
            </Button>

            <Button
              variant={nextEnabled ? "primary" : "danger"}
              onClick={confirmChange}
            >
              {nextEnabled ? "Enable AI" : "Disable AI"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
