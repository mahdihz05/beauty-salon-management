export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Salon {
  id: number;
  owner?: number;
  owner_name?: string;
  name: string;
  slug: string;
  type: "women" | "men" | "unisex";
  type_label: string;
  description: string;
  status: "draft" | "pending" | "approved" | "rejected" | "suspended";
  status_label: string;
  branches: Branch[];
  created_at?: string;
  updated_at?: string;
}

export interface Branch {
  id: number;
  salon: number;
  salon_name?: string;
  name: string;
  city?: number;
  city_name: string;
  address: string;
  phone: string;
  working_hours: Record<
    string,
    { is_open: boolean; start: string; end: string } | [string, string]
  >;
  is_active: boolean;
}

export interface BranchClosure {
  id: number;
  branch: number;
  branch_name: string;
  starts_at: string;
  ends_at: string;
  reason: string;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface Service {
  id: number;
  salon: number | null;
  category: number;
  category_name: string;
  name: string;
  description: string;
}

export interface BranchService {
  id: number;
  branch: number;
  branch_name: string;
  service: number;
  service_name: string;
  category_name: string;
  price: number;
  price_type: "fixed" | "starting_from";
  price_type_label: string;
  duration_minutes: number;
  is_active: boolean;
}

export interface Staff {
  id: number;
  branch: number;
  branch_name: string;
  user: number | null;
  first_name: string;
  last_name: string;
  full_name: string;
  photo: string | null;
  bio: string;
  experience_years: number;
  is_active: boolean;
  shifts: StaffShift[];
  staff_services: StaffService[];
}

export interface StaffShift {
  id: number;
  staff: number;
  day_of_week: number;
  day_label: string;
  start_time: string | null;
  end_time: string | null;
  is_off: boolean;
}

export interface StaffService {
  id: number;
  staff: number;
  branch_service: number;
  service_name: string;
  price_override: number | null;
  duration_override_minutes: number | null;
}

export interface StaffTimeOff {
  id: number;
  staff: number;
  starts_at: string;
  ends_at: string;
  reason: string;
}

export interface City {
  id: number;
  name: string;
  slug: string;
}
