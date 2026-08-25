import { create } from "zustand";

type AuthState = {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem("trace.access_token"),
  setAccessToken: (token) => {
    if (token) localStorage.setItem("trace.access_token", token);
    else localStorage.removeItem("trace.access_token");
    set({ accessToken: token });
  },
  clear: () => {
    localStorage.removeItem("trace.access_token");
    localStorage.removeItem("trace.refresh_token");
    set({ accessToken: null });
  },
}));
