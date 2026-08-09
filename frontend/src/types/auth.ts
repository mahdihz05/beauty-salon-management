export type UserRole =
  | "customer"
  | "salon_owner"
  | "branch_manager"
  | "receptionist"
  | "staff"
  | "admin";

export interface CustomerProfile {
  email: string;
  birth_date: string | null;
  gender: "woman" | "man" | "not_specified";
  avatar: string | null;
}

export interface User {
  id: number;
  phone: string;
  name: string;
  role: UserRole;
  role_label: string;
  profile?: CustomerProfile;
  created_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthResponse extends AuthTokens {
  user: User;
  is_new_user: boolean;
}
