import {useEffect,
  type ReactNode,
} from "react";
import {identityApi,
} from "../api/identity.api";
import {useAuthStore,
} from "../store/auth.store";
import {identityStorage,
} from "../utils/identity.storage";

type Props = {
  children: ReactNode;
};

export function IdentityBootstrap({
  children,
}: Props) {
  const setUser =
    useAuthStore(
      (state) => state.setUser,
    );

  const setHydrating =
    useAuthStore(
      (state) => state.setHydrating,
    );

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const hasSession =
        identityStorage.hasSession();

      if (!hasSession) {
        if (!cancelled) {
          setHydrating(false);
        }

        return;
      }

      try {
        const response =
          await identityApi.me();

        if (!cancelled) {
          setUser(response.user);
        }
      } catch {
        identityStorage.clear();

        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setHydrating(false);
        }
      }
    }

    hydrate();

    return () => {
      cancelled = true;
    };
  }, [
    setUser,
    setHydrating,
  ]);

  return children;
}