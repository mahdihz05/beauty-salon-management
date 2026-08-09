import type { Booking, DiscountCode, Payment, Review } from "./booking";
import type { Branch, BranchService, Salon, Staff } from "./salon";

export interface AdminSalon extends Salon {
  owner: number;
  owner_name: string;
  owner_phone: string;
  rating_average: number;
  review_count: number;
  is_featured: boolean;
  rejection_reason: string;
  created_at: string;
  updated_at: string;
}

export interface AdminSalonMetrics {
  booking_count: number;
  completed_count: number;
  confirmed_count: number;
  cancelled_count: number;
  no_show_count: number;
  gross_revenue: number;
  paid_revenue: number;
  refunded_amount: number;
  customer_count: number;
  branch_count: number;
  service_count: number;
  staff_count: number;
  payment_count: number;
  review_count: number;
}

export interface AdminSalonCustomer {
  id: number;
  name: string;
  phone: string;
  booking_count: number;
  completed_count: number;
  total_spent: number;
  last_booking_at: string | null;
}

export interface AdminSalonOverview {
  salon: AdminSalon;
  metrics: AdminSalonMetrics;
  branches: Branch[];
  services: BranchService[];
  staff: Staff[];
  customers: AdminSalonCustomer[];
  bookings: Booking[];
  payments: Payment[];
  reviews: Review[];
  discounts: DiscountCode[];
}
