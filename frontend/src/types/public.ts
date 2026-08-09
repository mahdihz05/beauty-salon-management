import type { BranchService, Staff } from "./salon";

export interface PublicCategory {
  id: number;
  name: string;
  slug: string;
  icon: string;
  service_count: number;
  salon_count: number;
}

export interface PublicBranchService extends BranchService {
  description: string;
  category_id: number;
}
export interface PublicBranch {
  id: number;
  name: string;
  city_name: string;
  district_name: string;
  address: string;
  phone: string;
  working_hours: Record<string, unknown>;
  amenities: string[];
  services: PublicBranchService[];
  staff: Staff[];
}
export interface PublicSalon {
  id: number;
  name: string;
  slug: string;
  type: "women" | "men" | "unisex";
  type_label: string;
  description: string;
  rating_average: string;
  review_count: number;
  is_featured: boolean;
  city: string;
  district: string;
  cover_image: string | null;
  min_price: number | null;
  is_favorite: boolean;
  images?: { id: number; image: string; alt_text: string; is_cover: boolean }[];
  branches?: PublicBranch[];
}
export interface Favorite {
  id: number;
  salon: number;
  salon_details: PublicSalon;
  created_at: string;
}
