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
  is_active: boolean;
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
  first_name: string;
  last_name: string;
  full_name: string;
  photo: string | null;
  bio: string;
  experience_years: number;
  is_active: boolean;
}

export interface City {
  id: number;
  name: string;
  slug: string;
}
