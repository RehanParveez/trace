import { create } from "zustand";
import type { User } from "../types/identity.types";
import { identityStorage } from "../utils/identity.storage";

type AuthState = {
  user: User | null;
  isHydrating: boolean;

  setUser: (user: User | null) => void;
  setHydrating: (value: boolean) => void;
  clearSession: () => void;
};

export const useAuthStore = create<AuthState>(
  (set) => ({
    user: null,

    isHydrating: true,

    setUser: (user) => {
      set({ user });
    },

    setHydrating: (value) => {
      set({
        isHydrating: value,
      });
    },

    clearSession: () => {
      identityStorage.clear();

      set({
        user: null,
      });
    },
  }),
);