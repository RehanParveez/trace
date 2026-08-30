import { useCurrentUser } from "./useIdentity";

export function usePermissionKeys(): string[] {
  const { data: user } = useCurrentUser();

  return user?.role?.permissions?.map((p) => p.key) ?? [];
}