import { createContext } from "react";
import type { AuthResponse, User } from "../types/auth";

export interface AuthContextValue {
  user: User | null;
  login: (response: AuthResponse) => void;
  setUser: (user: User) => void;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
