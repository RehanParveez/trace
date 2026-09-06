import {useEffect,
  type ReactNode,
} from "react";
import {identityApi,
} from "../api/identity.api";
import axios from "axios";
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
      if (!identityStorage.hasSession()) {
        if (!cancelled) {
          setUser(null);
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
      } catch (error) {
        if (
          axios.isAxiosError(error) &&
          [401, 403].includes(error.response?.status ?? 0)
        ) {
          identityStorage.clear();
          if (!cancelled) {
            setUser(null);
          }
        }
      } finally {
        if (!cancelled) {
          setHydrating(false);
        }
      }
    }

    void hydrate();

    return () => {
      cancelled = true;
    };
  }, [
    setUser,
    setHydrating,
  ]);

  return children;
}