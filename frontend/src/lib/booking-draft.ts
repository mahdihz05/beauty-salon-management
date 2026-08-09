import type { BookingDraft } from "../types/booking";

const KEY = "stitch.booking.draft";

export const bookingDraft = {
  get(): BookingDraft | null {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as BookingDraft) : null;
  },
  set(value: BookingDraft) {
    sessionStorage.setItem(KEY, JSON.stringify(value));
  },
  clear() {
    sessionStorage.removeItem(KEY);
  },
};
