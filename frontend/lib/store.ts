"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Recruiter {
  id: string;
  name: string;
  email: string;
}

interface AuthState {
  recruiter: Recruiter | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (recruiter: Recruiter, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      recruiter: null,
      token: null,
      isAuthenticated: false,

      setAuth: (recruiter, token) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("zenhire_token", token);
        }
        set({ recruiter, token, isAuthenticated: true });
      },

      clearAuth: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("zenhire_token");
        }
        set({ recruiter: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: "zenhire-auth",
      partialize: (state) => ({
        recruiter: state.recruiter,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
