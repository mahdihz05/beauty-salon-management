import {
  addDays,
  addMonths,
  endOfMonth,
  isSameDay,
  isSameMonth,
  startOfMonth,
} from "date-fns-jalali";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { dateFromIso, formatPersianDate, toLocalIsoDate } from "../lib/date";

interface JalaliDatePickerProps {
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  required?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
}

const weekDays = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
const persianDay = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  day: "numeric",
});

function calendarStart(month: Date) {
  const first = startOfMonth(month);
  const saturdayOffset = (first.getDay() + 1) % 7;
  return addDays(first, -saturdayOffset);
}

function isOutside(value: Date, min?: string, max?: string) {
  const iso = toLocalIsoDate(value);
  return Boolean((min && iso < min) || (max && iso > max));
}

export function JalaliDatePicker({
  value,
  onChange,
  min,
  max,
  required,
  disabled,
  ariaLabel = "انتخاب تاریخ شمسی",
}: JalaliDatePickerProps) {
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = value ? dateFromIso(value) : new Date();
  const [open, setOpen] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState(startOfMonth(selected));

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => {
    setVisibleMonth(startOfMonth(value ? dateFromIso(value) : new Date()));
  }, [value]);

  const start = calendarStart(visibleMonth);
  const days = Array.from({ length: 42 }, (_, index) => addDays(start, index));

  return (
    <div className="jalali-picker" ref={rootRef}>
      <button
        id={id}
        type="button"
        className="jalali-picker-trigger"
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{value ? formatPersianDate(selected) : "انتخاب تاریخ"}</span>
        <CalendarDays size={19} />
      </button>
      {required && (
        <input
          className="jalali-required-input"
          tabIndex={-1}
          required
          value={value}
          onChange={() => undefined}
          aria-hidden="true"
        />
      )}
      {open && (
        <div className="jalali-calendar" role="dialog" aria-label={ariaLabel}>
          <div className="jalali-calendar-head">
            <button
              type="button"
              aria-label="ماه بعد"
              onClick={() => setVisibleMonth(addMonths(visibleMonth, 1))}
            >
              <ChevronRight />
            </button>
            <strong>
              {formatPersianDate(visibleMonth, {
                month: "long",
                year: "numeric",
              })}{" "}
              هجری شمسی
            </strong>
            <button
              type="button"
              aria-label="ماه قبل"
              onClick={() => setVisibleMonth(addMonths(visibleMonth, -1))}
            >
              <ChevronLeft />
            </button>
          </div>
          <div className="jalali-weekdays" aria-hidden="true">
            {weekDays.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
          <div className="jalali-days">
            {days.map((day) => {
              const outside = !isSameMonth(day, visibleMonth);
              const unavailable = isOutside(day, min, max);
              return (
                <button
                  type="button"
                  key={toLocalIsoDate(day)}
                  className={`${outside ? "outside" : ""} ${isSameDay(day, selected) && value ? "selected" : ""}`}
                  disabled={unavailable}
                  aria-label={formatPersianDate(day, {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                  onClick={() => {
                    onChange(toLocalIsoDate(day));
                    setOpen(false);
                  }}
                >
                  {persianDay.format(day)}
                </button>
              );
            })}
          </div>
          <div className="jalali-calendar-footer">
            <span>{formatPersianDate(startOfMonth(visibleMonth))}</span>
            <span>تا {formatPersianDate(endOfMonth(visibleMonth))}</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface JalaliDateTimePickerProps {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  min?: string;
}

export function JalaliDateTimePicker({
  value,
  onChange,
  required,
  min,
}: JalaliDateTimePickerProps) {
  const [date = "", time = ""] = value.split("T");
  return (
    <div className="jalali-datetime-picker">
      <JalaliDatePicker
        value={date}
        min={min?.split("T")[0]}
        required={required}
        onChange={(nextDate) => onChange(`${nextDate}T${time || "00:00"}`)}
      />
      <input
        type="time"
        required={required}
        value={time}
        aria-label="ساعت"
        onChange={(event) => onChange(`${date}T${event.target.value}`)}
      />
    </div>
  );
}
