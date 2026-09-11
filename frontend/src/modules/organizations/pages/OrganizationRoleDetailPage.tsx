import { useNavigate, useParams } from "react-router-dom";
import {useCreateRole, usePermissions, useRole, useUpdateRole,
} from "../hooks";
import type { RoleCreateRequest } from "../types/organization.types";
import { RoleForm } from "../components/RoleForm";
import {Button, ErrorState, Icon, LoadingState, PageHeader,
} from "../components/OrganizationUi";
import { useTranslation } from "react-i18next";

export function OrganizationRoleDetailPage() {
  const navigate = useNavigate();
  const { roleId } = useParams<{ roleId: string }>();

  const isNew = roleId === "new";
  const { t } = useTranslation();

  const roleQuery = useRole(isNew ? undefined : roleId);
  const permissionsQuery = usePermissions();

  const createRole = useCreateRole();
  const updateRole = useUpdateRole();

  if (permissionsQuery.isLoading || (!isNew && roleQuery.isLoading)) {
    return (
      <LoadingState
        label={isNew ? t("roleDetail.loadingNew") : t("roleDetail.loading")}
      />
    );
  }

  if (permissionsQuery.isError || (!isNew && roleQuery.isError)) {
    return (
      <ErrorState
        title={t("roleDetail.loadError")}
        onRetry={() => {
          void permissionsQuery.refetch();

          if (!isNew) {
            void roleQuery.refetch();
          }
        }}
      />
    );
  }

  const role = isNew ? undefined : roleQuery.data;

  return (
    <div>
      <PageHeader
        eyebrow={isNew ? t("roleDetail.newEyebrow") : t("roleDetail.detailEyebrow")}
        title={isNew ? "Create role" : (role?.name ?? "Role")}
        description={isNew ? t("roleDetail.createDesc") : (role?.description ?? "")}
        actions={
          <Button
            variant="ghost"
            onClick={() => navigate("/app/organization/roles")}
          >
            <Icon name="arrow" size={13} />
            {t("roleDetail.back")}
          </Button>
        }
      />

      <RoleForm
        role={role}
        permissions={permissionsQuery.data ?? []}
        isSubmitting={createRole.isPending || updateRole.isPending}
        onSubmit={(payload) => {
          if (isNew) {
           createRole.mutate(payload as RoleCreateRequest, {
            onSuccess: (created) =>
             navigate(`/app/organization/roles/${created.id}`),
           });

    return;
    }

    updateRole.mutate(
      { roleId: roleId!, payload },
      {
        onSuccess: () =>
          navigate(`/app/organization/roles/${roleId}`),
      },
    );
  }}
        onCancel={() => navigate("/app/organization/roles")}
      />
    </div>
  );
}
