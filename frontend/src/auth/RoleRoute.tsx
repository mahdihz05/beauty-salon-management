import type { PropsWithChildren } from "react";
import { Redirect } from "wouter";
import type { UserRole } from "../types/auth";
import { useAuth } from "./useAuth";

interface RoleRouteProps extends PropsWithChildren {
  roles: UserRole[];
}

export function RoleRoute({ roles, children }: RoleRouteProps) {
  const { user } = useAuth();
  if (!user) return <Redirect to="/login" />;
  return roles.includes(user.role) ? children : <Redirect to="/" />;
}
