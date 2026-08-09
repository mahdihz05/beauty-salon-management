import type { BookingDraft } from "../types/booking";

const KEY = "nobatara.booking.draft";
const LEGACY_KEY = "stitch.booking.draft";

export const bookingDraft = {
  get(): BookingDraft | null {
    const raw =
      sessionStorage.getItem(KEY) ?? sessionStorage.getItem(LEGACY_KEY);
    return raw ? (JSON.parse(raw) as BookingDraft) : null;
  },
  set(value: BookingDraft) {
    sessionStorage.setItem(KEY, JSON.stringify(value));
    sessionStorage.removeItem(LEGACY_KEY);
  },
  clear() {
    sessionStorage.removeItem(KEY);
    sessionStorage.removeItem(LEGACY_KEY);
  },
};
