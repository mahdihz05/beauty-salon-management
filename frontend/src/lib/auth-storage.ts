import type { AuthTokens, User } from "../types/auth";

const TOKENS_KEY = "nobatara.auth.tokens";
const USER_KEY = "nobatara.auth.user";
const LEGACY_TOKENS_KEY = "stitch.auth.tokens";
const LEGACY_USER_KEY = "stitch.auth.user";

export const authStorage = {
  getTokens(): AuthTokens | null {
    const value =
      localStorage.getItem(TOKENS_KEY) ??
      localStorage.getItem(LEGACY_TOKENS_KEY);
    return value ? (JSON.parse(value) as AuthTokens) : null;
  },
  getUser(): User | null {
    const value =
      localStorage.getItem(USER_KEY) ?? localStorage.getItem(LEGACY_USER_KEY);
    return value ? (JSON.parse(value) as User) : null;
  },
  set(tokens: AuthTokens, user: User) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.removeItem(LEGACY_TOKENS_KEY);
    localStorage.removeItem(LEGACY_USER_KEY);
  },
  setTokens(tokens: AuthTokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  },
  setUser(user: User) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKENS_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(LEGACY_TOKENS_KEY);
    localStorage.removeItem(LEGACY_USER_KEY);
  },
};
