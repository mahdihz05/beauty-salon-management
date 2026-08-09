import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("application foundation", () => {
  it("renders the Persian home heading", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "آرایشگاه‌های نزدیک شما" }),
    ).toBeInTheDocument();
  });
});
