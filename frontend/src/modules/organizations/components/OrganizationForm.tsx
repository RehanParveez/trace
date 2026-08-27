import {type FormEvent, useEffect, useState,
} from "react";
import type {Organization, OrganizationUpdateRequest,
} from "../types/organization.types";
import {Button, Field, Icon, inputClass, Modal,
} from "./OrganizationUi";

interface OrganizationFormProps {
  organization: Organization;
  isSubmitting?: boolean;
  onSubmit: (
    payload: OrganizationUpdateRequest,
  ) => void;
  onCancel?: () => void;
}

export function OrganizationForm({
  organization,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: OrganizationFormProps) {
  const [name, setName] =
    useState(organization.name);

  const [slug, setSlug] =
    useState(organization.slug);

  useEffect(() => {
    setName(organization.name);
    setSlug(organization.slug);
  }, [
    organization.name,
    organization.slug,
  ]);

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    onSubmit({
      name: name.trim(),
      slug: slug.trim().toLowerCase(),
    });
  }

  return (
    <Modal
      title="Edit organization"
      description="Update the workspace identity used across Trace."
      onClose={() =>
        onCancel?.()
      }
    >
      <form
        onSubmit={handleSubmit}
        className="space-y-4"
      >
        <Field
          label="Organization name"
          hint="Use the official operating name your team recognizes."
        >
          <input
            value={name}
            onChange={(event) =>
              setName(event.target.value)
            }
            minLength={2}
            maxLength={255}
            required
            className={inputClass}
            autoFocus
          />
        </Field>

        <Field
          label="Workspace slug"
          hint="Lowercase URL-safe identifier. Changing it may affect shared links."
        >
          <input
            value={slug}
            onChange={(event) =>
              setSlug(event.target.value)
            }
            minLength={2}
            maxLength={100}
            required
            className={inputClass}
          />
        </Field>

        <div className="flex items-center justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          {onCancel ? (
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
            >
              Cancel
            </Button>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#080d18]/30 border-t-[#080d18]" />
            ) : (
              <Icon
                name="check"
                size={13}
              />
            )}

            {isSubmitting
              ? "Saving…"
              : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}