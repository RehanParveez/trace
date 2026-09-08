import { type FormEvent, useEffect, useState } from "react";
import type {Organization, OrganizationUpdateRequest,
} from "../types/organization.types";
import { Button, Field, Icon, inputClass, Modal } from "./OrganizationUi";

interface OrganizationFormProps {
  organization: Organization;
  isSubmitting?: boolean;
  onSubmit: (payload: OrganizationUpdateRequest) => void;
  onCancel?: () => void;
}

function normalizeSlug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function OrganizationForm({
  organization,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: OrganizationFormProps) {
  const [name, setName] = useState(organization.name);
  const [slug, setSlug] = useState(organization.slug);

  useEffect(() => {
    setName(organization.name);
    setSlug(organization.slug);
  }, [organization.name, organization.slug]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit({
      name: name.trim(),
      slug: normalizeSlug(slug),
    });
  }

  const slugChanged = normalizeSlug(slug) !== organization.slug;

  return (
    <Modal
      title="Edit organization"
      description="Update the workspace identity used across Trace."
      onClose={() => onCancel?.()}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Organization name"
          hint="Use the official operating name your team recognizes."
        >
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            minLength={2}
            maxLength={255}
            required
            className={inputClass}
            autoFocus
          />
        </Field>

        <Field
          label="Workspace slug"
          hint="Lowercase, URL-safe identifier used in shared links."
        >
          <input
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            minLength={2}
            maxLength={100}
            required
            className={inputClass}
          />
        </Field>

        <div className="flex items-center gap-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 font-mono text-[12px] text-[var(--color-text-secondary)]">
          <Icon name="external" size={13} className="shrink-0 text-[var(--color-text-muted)]" />
          <span className="truncate">
            trace.app/<span className="text-[var(--color-text-primary)]">{normalizeSlug(slug) || "…"}</span>
          </span>

          {slugChanged ? (
            <span className="ml-auto shrink-0 rounded-full bg-[var(--color-warning-bg)] px-2 py-0.5 text-[10px] font-sans font-semibold text-[var(--color-warning)]">
              Changing this may break shared links
            </span>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          {onCancel ? (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          ) : null}

          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#080d18]/30 border-t-[#080d18]" />
            ) : (
              <Icon name="check" size={13} />
            )}

            {isSubmitting ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
