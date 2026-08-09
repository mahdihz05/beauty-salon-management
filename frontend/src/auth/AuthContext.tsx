import { useMemo, useState, type PropsWithChildren } from "react";
import { api } from "../api/client";
import { authStorage } from "../lib/auth-storage";
import type { User } from "../types/auth";
import { AuthContext, type AuthContextValue } from "./auth-context";

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUserState] = useState<User | null>(() =>
    authStorage.getUser(),
  );
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      login(response) {
        authStorage.set(
          { access: response.access, refresh: response.refresh },
          response.user,
        );
        setUserState(response.user);
      },
      setUser(nextUser) {
        authStorage.setUser(nextUser);
        setUserState(nextUser);
      },
      async logout() {
        const refresh = authStorage.getTokens()?.refresh;
        try {
          if (refresh) await api.post("/auth/logout/", { refresh });
        } finally {
          authStorage.clear();
          setUserState(null);
        }
      },
    }),
    [user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
