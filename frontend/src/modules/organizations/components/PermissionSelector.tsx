import { useMemo } from "react";
import type { Permission } from "../types/organization.types";
import { Icon, SectionLabel } from "./OrganizationUi";

interface PermissionSelectorProps {
  permissions: Permission[];
  selectedIds: string[];
  disabled?: boolean;
  onChange: (permissionIds: string[]) => void;
}

function getResourceGroup(permission: Permission): string {
  const [resource] = permission.key.split(".");

  return resource || "general";
}

export function PermissionSelector({
  permissions,
  selectedIds,
  disabled = false,
  onChange,
}: PermissionSelectorProps) {
  const groups = useMemo(() => {
    const map = new Map<string, Permission[]>();

    for (const permission of permissions) {
      const group = getResourceGroup(permission);
      const existing = map.get(group) ?? [];

      existing.push(permission);
      map.set(group, existing);
    }

    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permissions]);

  function togglePermission(permissionId: string) {
    onChange(
      selectedIds.includes(permissionId)
        ? selectedIds.filter((id) => id !== permissionId)
        : [...selectedIds, permissionId],
    );
  }

  function toggleGroup(groupPermissions: Permission[]) {
    const groupIds = groupPermissions.map((permission) => permission.id);
    const allSelected = groupIds.every((id) => selectedIds.includes(id));

    onChange(
      allSelected
        ? selectedIds.filter((id) => !groupIds.includes(id))
        : Array.from(new Set([...selectedIds, ...groupIds])),
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
            Access matrix
          </div>

          <h3 className="mt-1 font-[Archivo] text-[14px] font-bold text-[#191410]">
            Permissions
          </h3>

          <p className="mt-1 text-[11px] leading-4 text-[#6b6152]">
            Select the capabilities this role can use, grouped by resource.
          </p>
        </div>

        <span className="font-mono text-[10px] text-[#a2957c]">
          {selectedIds.length}/{permissions.length}
        </span>
      </div>

      <div className="space-y-5">
        {groups.map(([group, groupPermissions]) => {
          const groupIds = groupPermissions.map((permission) => permission.id);
          const allSelected = groupIds.every((id) => selectedIds.includes(id));

          return (
            <div key={group}>
              <div className="mb-2 flex items-center justify-between">
                <SectionLabel>{group}</SectionLabel>

                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => toggleGroup(groupPermissions)}
                  className="text-[10.5px] font-semibold text-[#b98626] hover:text-[#9a6f1c] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {allSelected ? "Clear group" : "Select all"}
                </button>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                {groupPermissions.map((permission) => {
                  const selected = selectedIds.includes(permission.id);

                  return (
                    <label
                      key={permission.id}
                      className={`flex gap-3 rounded-[10px] border p-3 transition ${
                        selected
                          ? "border-[#d9a441] bg-[#fbefd9]"
                          : "border-[#e1d5bc] bg-white hover:bg-[#f5efe3]"
                      } ${
                        disabled
                          ? "cursor-not-allowed opacity-60"
                          : "cursor-pointer"
                      }`}
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
                            ? "border-[#b98626] bg-[#d9a441] text-[#080d18]"
                            : "border-[#cbbb9c] bg-white text-transparent"
                        }`}
                      >
                        <Icon name="check" size={12} strokeWidth={2.4} />
                      </span>

                      <span className="min-w-0">
                        <span className="block break-all font-mono text-[10.5px] font-semibold text-[#332a21]">
                          {permission.key}
                        </span>

                        {permission.description ? (
                          <span className="mt-1 block text-[10.5px] leading-4 text-[#6b6152]">
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
    </div>
  );
}
