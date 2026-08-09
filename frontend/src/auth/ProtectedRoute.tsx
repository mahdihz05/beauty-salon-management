import type { PropsWithChildren } from "react";
import { Redirect } from "wouter";
import { useAuth } from "./useAuth";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { user } = useAuth();
  return user ? children : <Redirect to="/login" />;
}
