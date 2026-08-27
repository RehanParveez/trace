import {useNavigate, useParams,
} from "react-router-dom";
import {useCreateRole, usePermissions, useRole, useUpdateRole,
} from "../hooks";
import {RoleForm,
} from "../components/RoleForm";
import {Button, ErrorState, Icon, LoadingState, PageHeader,
} from "../components/OrganizationUi"
import { RoleCreateRequest } from "../types/organization.types";

export function OrganizationRoleDetailPage() {
  const navigate =
    useNavigate();

  const {
    roleId,
  } = useParams<{
    roleId: string;
  }>();

  const isNew =
    roleId === "new";

  const roleQuery =
    useRole(
      isNew
        ? undefined
        : roleId,
    );

  const permissionsQuery =
    usePermissions();

  const createRole =
    useCreateRole();

  const updateRole =
    useUpdateRole();

  if (
    permissionsQuery.isLoading ||
    (!isNew &&
      roleQuery.isLoading)
  ) {
    return (
      <LoadingState
        label={
          isNew
            ? "Preparing role editor…"
            : "Loading role…"
        }
      />
    );
  }

  if (
    permissionsQuery.isError ||
    (!isNew &&
      roleQuery.isError)
  ) {
    return (
      <ErrorState
        title="We couldn't load the role editor"
        onRetry={() => {
          void permissionsQuery.refetch();

          if (!isNew) {
            void roleQuery.refetch();
          }
        }}
      />
    );
  }

  const role =
    isNew
      ? undefined
      : roleQuery.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          isNew
            ? "NEW ROLE"
            : "ROLE DETAIL"
        }
        title={
          isNew
            ? "Create role"
            : role?.name ??
              "Role"
        }
        description={
          isNew
            ? "Create a focused access profile for a construction workflow responsibility."
            : role?.description ??
              "Review and manage the role's access boundary."
        }
        actions={
          <Button
            variant="ghost"
            onClick={() =>
              navigate(
                "/app/organization/roles",
              )
            }
          >
            <Icon
              name="arrow"
              size={13}
            />
            Back to roles
          </Button>
        }
      />

      <RoleForm
  role={role}
  permissions={
    permissionsQuery.data ??
    []
  }
  isSubmitting={
    createRole.isPending ||
    updateRole.isPending
  }
  onSubmit={(payload) => {
    if (isNew) {
      createRole.mutate(
        payload as RoleCreateRequest,
        {
          onSuccess:
            (created) =>
              navigate(
                `/app/organization/roles/${created.id}`,
              ),
          },
      );

      return;
    }
    updateRole.mutate(
      {
        roleId:
          roleId!,
        payload,
      },
      {
        onSuccess: () =>
          navigate(
            `/app/organization/roles/${roleId}`,
          ),
      },
    );
  }}
  onCancel={() =>
    navigate(
      "/app/organization/roles",
    )
  }
/>
    </div>
  );
}