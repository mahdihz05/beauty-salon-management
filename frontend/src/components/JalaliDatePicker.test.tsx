import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JalaliDatePicker } from "./JalaliDatePicker";

describe("JalaliDatePicker", () => {
  it("shows the selected Gregorian API value as a Persian date", () => {
    render(<JalaliDatePicker value="2026-03-21" onChange={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: "انتخاب تاریخ شمسی" }),
    ).toHaveTextContent("۱ فروردین ۱۴۰۵");
  });

  it("opens a Persian calendar and returns a Gregorian API date", () => {
    const onChange = vi.fn();
    render(<JalaliDatePicker value="2026-03-21" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "انتخاب تاریخ شمسی" }));
    expect(
      screen.getByRole("dialog", { name: "انتخاب تاریخ شمسی" }),
    ).toHaveTextContent("۱۴۰۵ فروردین هجری شمسی");
    fireEvent.click(
      screen.getByRole("button", { name: "۱۴۰۵ فروردین ۲, یکشنبه" }),
    );
    expect(onChange).toHaveBeenCalledWith("2026-03-22");
  });
});
