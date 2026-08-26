import {Navigate,
} from "react-router-dom";
import type {ReactNode,
} from "react";
import { useAuthStore } from "../store/auth.store";

type Props = {
  children: ReactNode;
};

export function PublicOnlyRoute({
  children,
}: Props) {
  const user = useAuthStore(
    (state) => state.user,
  );

  const isHydrating =
    useAuthStore(
      (state) => state.isHydrating,
    );

  if (isHydrating) {
    return <IdentityLoadingScreen />;
  }

  if (user) {
    return (
      <Navigate
        to="/app/profile"
        replace
      />
    );
  }

  return children;
}

function IdentityLoadingScreen() {
  return (
    <div className="grid min-h-screen place-items-center bg-[#F5EFE3]">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[#D9A441] border-t-transparent" />

        <p className="font-mono text-[10px] uppercase tracking-[.14em] text-[#8B806F]">
          Loading Trace
        </p>
      </div>
    </div>
  );
}