import type { AuthTokens, User } from "../types/auth";

const TOKENS_KEY = "salovina.auth.tokens";
const USER_KEY = "salovina.auth.user";
const LEGACY_TOKENS_KEYS = ["nobatara.auth.tokens", "stitch.auth.tokens"];
const LEGACY_USER_KEYS = ["nobatara.auth.user", "stitch.auth.user"];

function readFirst(keys: string[]) {
  for (const key of keys) {
    const value = localStorage.getItem(key);
    if (value) return value;
  }
  return null;
}

function removeAll(keys: string[]) {
  keys.forEach((key) => localStorage.removeItem(key));
}

export const authStorage = {
  getTokens(): AuthTokens | null {
    const value = localStorage.getItem(TOKENS_KEY) ?? readFirst(LEGACY_TOKENS_KEYS);
    return value ? (JSON.parse(value) as AuthTokens) : null;
  },
  getUser(): User | null {
    const value = localStorage.getItem(USER_KEY) ?? readFirst(LEGACY_USER_KEYS);
    return value ? (JSON.parse(value) as User) : null;
  },
  set(tokens: AuthTokens, user: User) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    removeAll(LEGACY_TOKENS_KEYS);
    removeAll(LEGACY_USER_KEYS);
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
    removeAll(LEGACY_TOKENS_KEYS);
    removeAll(LEGACY_USER_KEYS);
  },
};
