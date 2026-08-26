import {Navigate, Outlet, useLocation,
} from "react-router-dom";
import { useAuthStore } from "../store/auth.store";

export function ProtectedRoute() {
  const user = useAuthStore(
    (state) => state.user,
  );

  const isHydrating =
    useAuthStore(
      (state) => state.isHydrating,
    );

  const location =
    useLocation();

  if (isHydrating) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#F5EFE3]">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[#D9A441] border-t-transparent" />

          <p className="font-mono text-[10px] uppercase tracking-[.14em] text-[#8B806F]">
            Restoring session
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location,
        }}
      />
    );
  }

  return <Outlet />;
}