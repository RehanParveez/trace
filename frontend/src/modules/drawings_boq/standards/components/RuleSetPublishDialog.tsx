import { useEffect, useState } from "react";
import { Badge, Button, LoadingState, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { usePublishRuleSet, useValidateRuleSet } from "../hooks";
import type { RuleSet } from "../types/standards.types";
import { getIssueTone, ruleSetLabel } from "../utils/standards.utils";

export function RuleSetPublishDialog({ ruleSet, onClose }: { ruleSet: RuleSet; onClose: () => void }) {
  const validate = useValidateRuleSet();
  const publish = usePublishRuleSet();
  const { showToast } = useToast();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    validate.mutate(ruleSet.id);
  }, [ruleSet.id]);

  const issues = validate.data?.issues ?? [];
  const errorCount = issues.filter((i) => i.severity === "error").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;

  function confirm() {
    setError(null);
    publish.mutate(ruleSet.id, {
      onSuccess: () => { onClose(); showToast({ tone: "success", title: `${ruleSetLabel(ruleSet.code, ruleSet.immutable_version)} published` }); },
      onError: (e) => setError(getApiErrorMessage(e, "Couldn't publish this rule set.")),
    });
  }

  return (
    <Modal
      title={`Publish ${ruleSetLabel(ruleSet.code, ruleSet.immutable_version)}`}
      description="Publishing freezes this version. Any later change needs a new cloned version, and the currently active version of this code will be superseded."
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        {validate.isPending ? <LoadingState label="Checking rule set…" /> : null}
        {validate.isError ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{getApiErrorMessage(validate.error, "Couldn't validate this rule set.")}</div> : null}

        {validate.data ? (
          <>
            <div className="flex gap-2">
              <Badge tone={errorCount > 0 ? "red" : "green"}>{errorCount} error{errorCount === 1 ? "" : "s"}</Badge>
              <Badge tone={warningCount > 0 ? "gold" : "green"}>{warningCount} warning{warningCount === 1 ? "" : "s"}</Badge>
            </div>
            {issues.length === 0 ? (
              <p className="text-[12.5px] text-[var(--color-text-secondary)]">No issues found.</p>
            ) : (
              <ul className="max-h-[320px] space-y-2 overflow-y-auto">
                {issues.map((issue, index) => (
                  <li key={`${issue.code}-${issue.ref ?? ""}-${index}`} className="flex items-start gap-2.5 rounded-[8px] border border-[var(--color-border)] p-3">
                    <Badge tone={getIssueTone(issue.severity)}>{issue.severity}</Badge>
                    <div className="min-w-0">
                      <div className="text-[12.5px] text-[var(--color-text-primary)]">{issue.message}</div>
                      <div className="mt-0.5 font-mono text-[11px] text-[var(--color-text-muted)]">{issue.code}</div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {errorCount > 0 ? <p className="text-[12px] text-[var(--color-danger)]">Fix the errors in the draft before publishing.</p> : null}
          </>
        ) : null}

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={publish.isPending}>Cancel</Button>
          <Button type="button" variant="primary" onClick={confirm} disabled={validate.isPending || (validate.isSuccess && errorCount > 0) || publish.isPending}>{publish.isPending ? "Publishing…" : "Publish"}</Button>
        </div>
      </div>
    </Modal>
  );
}
