import type { BookingDraft } from "../types/booking";

const KEY = "salovina.booking.draft";
const LEGACY_KEYS = ["nobatara.booking.draft", "stitch.booking.draft"];

function removeLegacyDrafts() {
  LEGACY_KEYS.forEach((key) => sessionStorage.removeItem(key));
}

export const bookingDraft = {
  get(): BookingDraft | null {
    const raw =
      sessionStorage.getItem(KEY) ??
      LEGACY_KEYS.map((key) => sessionStorage.getItem(key)).find(Boolean);
    return raw ? (JSON.parse(raw) as BookingDraft) : null;
  },
  set(value: BookingDraft) {
    sessionStorage.setItem(KEY, JSON.stringify(value));
    removeLegacyDrafts();
  },
  clear() {
    sessionStorage.removeItem(KEY);
    removeLegacyDrafts();
  },
};
