import { useMemo, useState } from "react";
import type { Permission } from "../types/organization.types";
import { humanizePermission } from "../utils/organization.utils";
import { Icon } from "./OrganizationUi";
import { useTranslation } from "react-i18next";

interface PermissionSelectorProps {
  permissions: Permission[];
  selectedIds: string[];
  disabled?: boolean;
  onChange: (permissionIds: string[]) => void;
}

interface PermissionGroup {
  group: string;
  items: Array<{ permission: Permission; label: string }>;
}

export function PermissionSelector({
  permissions,
  selectedIds,
  disabled = false,
  onChange,
}: PermissionSelectorProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [showRawKeys, setShowRawKeys] = useState(false);

  const groups = useMemo<PermissionGroup[]>(() => {
    const map = new Map<string, PermissionGroup["items"]>();

    for (const permission of permissions) {
      const { group, label } = humanizePermission(permission.key);
      const existing = map.get(group) ?? [];

      existing.push({ permission, label });
      map.set(group, existing);
    }

    return Array.from(map.entries())
      .map(([group, items]) => ({
        group,
        items: items.sort((a, b) => a.label.localeCompare(b.label)),
      }))
      .sort((a, b) => a.group.localeCompare(b.group));
  }, [permissions]);

  const filteredGroups = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return groups;
    }

    return groups
      .map((group) => ({
        group: group.group,
        items: group.items.filter(
          (item) =>
            item.label.toLowerCase().includes(normalized) ||
            item.permission.key.toLowerCase().includes(normalized) ||
            group.group.toLowerCase().includes(normalized),
        ),
      }))
      .filter((group) => group.items.length > 0);
  }, [groups, query]);

  function togglePermission(permissionId: string) {
    onChange(
      selectedIds.includes(permissionId)
        ? selectedIds.filter((id) => id !== permissionId)
        : [...selectedIds, permissionId],
    );
  }

  function toggleGroup(groupItems: PermissionGroup["items"]) {
    const groupIds = groupItems.map((item) => item.permission.id);
    const allSelected = groupIds.every((id) => selectedIds.includes(id));

    onChange(
      allSelected
        ? selectedIds.filter((id) => !groupIds.includes(id))
        : Array.from(new Set([...selectedIds, ...groupIds])),
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
            {t("permissions.accessMatrix")}
          </div>

          <h3 className="mt-1 font-[Archivo] text-[15px] font-bold text-[var(--color-text-primary)]">
            {t("permissions.whatRoleCanDo")}
          </h3>

          <p className="mt-1 max-w-md text-[12.5px] leading-5 text-[var(--color-text-secondary)]">
            {t("permissions.whatRoleCanDoDesc")}
</p>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
           {t("permissions.selectedCount", { selected: selectedIds.length, total: permissions.length })}
          </span>

          <button
            type="button"
            onClick={() => setShowRawKeys((value) => !value)}
            className="text-[11.5px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
          >
            {showRawKeys ? t("permissions.hideKeys") : t("permissions.showKeys")}
          </button>
        </div>
      </div>

      <div className="mb-4 flex h-10 items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5">
        <Icon name="search" size={14} className="text-[var(--color-text-muted)]" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("permissions.filterPlaceholder")}
          className="w-full bg-transparent text-[13px] outline-none placeholder:text-[var(--color-text-muted)]"
        />
      </div>

      {filteredGroups.length === 0 ? (
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-6 text-center text-[12.5px] text-[var(--color-text-secondary)]">
          {t("permissions.noMatch", { query })}
        </div>
      ) : (
        <div className="space-y-5">
          {filteredGroups.map(({ group, items }) => {
            const groupIds = items.map((item) => item.permission.id);
            const allSelected = groupIds.every((id) => selectedIds.includes(id));
            const someSelected = groupIds.some((id) => selectedIds.includes(id));

            return (
              <div key={group}>
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                      {group}
                    </span>

                    {someSelected && !allSelected ? (
                      <span className="rounded-full bg-[var(--color-warning-bg)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-warning)]">
                        {t("permissions.partial")}
                      </span>
                    ) : null}
                  </div>

                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => toggleGroup(items)}
                    className="text-[11px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {allSelected ? t("permissions.clearGroup") : t("permissions.selectAll")}
                  </button>
                </div>

                <div className="grid gap-2 sm:grid-cols-2">
                  {items.map(({ permission, label }) => {
                    const selected = selectedIds.includes(permission.id);

                    return (
                      <label
                        key={permission.id}
                        className={`flex gap-3 rounded-[var(--radius-md)] border p-3 transition ${
                          selected
                            ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]"
                            : "border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)]"
                        } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
                      >
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={selected}
                          disabled={disabled}
                          onChange={() => togglePermission(permission.id)}
                        />

                        <span
                          className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] border ${
                            selected
                              ? "border-[var(--color-trace-gold-dark)] bg-[var(--color-trace-gold)] text-[var(--color-trace-navy)]"
                              : "border-[var(--color-border-strong)] bg-[var(--color-surface)] text-transparent"
                          }`}
                        >
                          <Icon name="check" size={12} strokeWidth={2.4} />
                        </span>

                        <span className="min-w-0">
                          <span className="block text-[13px] font-semibold text-[var(--color-text-primary)]">
                            {label}
                          </span>

                          {showRawKeys ? (
                            <span className="mt-0.5 block break-all font-mono text-[10.5px] text-[var(--color-text-muted)]">
                              {permission.key}
                            </span>
                          ) : null}

                          {permission.description ? (
                            <span className="mt-1 block text-[11.5px] leading-4 text-[var(--color-text-secondary)]">
                              {permission.description}
                            </span>
                          ) : null}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}