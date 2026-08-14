export interface AvailableSlot {
  start_at: string;
  end_at: string;
  staff_id: number;
  staff_name: string;
  total_price: number;
  duration_minutes: number;
}

export interface BookingItem {
  id: number;
  branch_service: number;
  service_name: string;
  staff: number;
  staff_name: string;
  price: number;
  duration_minutes: number;
}

export interface Booking {
  id: number;
  customer: number;
  branch: number;
  branch_name: string;
  salon_name: string;
  staff: number;
  staff_name: string;
  status:
    | "pending_payment"
    | "awaiting_verification"
    | "confirmed"
    | "completed"
    | "cancelled"
    | "no_show";
  source: "online" | "walk_in";
  status_label: string;
  start_at: string;
  end_at: string;
  total_price: number;
  deposit_amount: number;
  discount_code: number | null;
  discount_amount: number;
  paid_amount: number;
  remaining_amount: number;
  notes: string;
  hold_expires_at: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string;
  checked_in_at?: string | null;
  checked_in_by?: number | null;
  refund_amount?: number;
  refund_destination?: "wallet" | null;
  items: BookingItem[];
}

export interface BookingDraft {
  branchId: number;
  serviceIds: number[];
  slot?: AvailableSlot;
}

export interface Payment {
  id: number;
  booking: number;
  customer_phone: string;
  salon_name: string;
  branch_name: string;
  amount: number;
  type: "deposit" | "full" | "remainder";
  status: "pending" | "paid" | "failed" | "refunded";
  method: "in_person" | "card_to_card" | "online" | "cash" | "wallet";
  tracking_code: string;
  receipt: string | null;
  verified_by: number | null;
  verified_at: string | null;
  provider: string;
  gateway_ref: string;
  redirect_url: string;
  paid_at: string | null;
  created_at: string;
}

export interface Settlement {
  id: number;
  amount: number;
  salon: number | null;
  status: "requested" | "paid" | "rejected";
  bank_account: string;
  note: string;
  owner_name: string;
  owner_phone: string;
  requested_at: string;
  processed_at: string | null;
}

export interface WalletTransaction {
  id: number;
  amount: number;
  type: string;
  type_label: string;
  related_booking: number | null;
  description: string;
  created_at: string;
}

export interface Wallet {
  balance: number;
  updated_at: string;
  transactions: WalletTransaction[];
}

export interface Review {
  id: number;
  booking: number;
  customer_name: string;
  salon: number;
  salon_name: string;
  staff: number | null;
  staff_name: string;
  overall_rating: number;
  quality_rating: number;
  cleanliness_rating: number;
  behavior_rating: number;
  value_rating: number;
  comment: string;
  status: "pending" | "published" | "hidden";
  status_label: string;
  images: { id: number; image: string }[];
  created_at: string;
}

export interface DiscountCode {
  id: number;
  code: string;
  salon: number | null;
  salon_name: string;
  type: "percent" | "fixed";
  type_label: string;
  value: number;
  minimum_purchase: number;
  maximum_discount: number | null;
  usage_limit: number | null;
  used_count: number;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
}

export interface NotificationLog {
  id: number;
  booking: number;
  event: string;
  event_label: string;
  channel: string;
  status: "pending" | "sent" | "failed";
  status_label: string;
  customer_name: string;
  customer_phone: string;
  salon_name: string;
  message: string;
  created_at: string;
  sent_at: string | null;
}

export interface CustomerSummary {
  id: number;
  name: string;
  phone: string;
  booking_count: number;
  total_spent: number;
  last_booking_at: string | null;
}

export interface ReportSummary {
  date_from: string;
  date_to: string;
  gross_revenue: number;
  commission: number;
  net_revenue: number;
  booking_count: number;
  completed_count: number;
  cancelled_count: number;
  no_show_count: number;
  average_booking_value: number;
  daily: { date: string; bookings: number; revenue: number }[];
  top_services: { service_name: string; count: number; revenue: number }[];
}
