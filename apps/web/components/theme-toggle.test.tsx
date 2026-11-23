import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "./theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.matchMedia = ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
  });

  it("applies the stored theme on mount", async () => {
    window.localStorage.setItem("theme", "dark");
    render(<ThemeToggle />);

    const button = await screen.findByRole("button");
    expect(button.getAttribute("aria-label")).toContain("Theme: dark (dark)");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("cycles system → light → dark → system and persists the choice", async () => {
    render(<ThemeToggle />);

    const button = await screen.findByRole("button");
    expect(button.getAttribute("aria-label")).toContain("Theme: system (dark)");

    await userEvent.click(button);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
    expect(window.localStorage.getItem("theme")).toBe("light");

    await userEvent.click(button);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("theme")).toBe("dark");

    await userEvent.click(button);
    expect(window.localStorage.getItem("theme")).toBe("system");
  });

  it("falls back to system for unknown stored values", async () => {
    window.localStorage.setItem("theme", "sepia");
    render(<ThemeToggle />);

    const button = await screen.findByRole("button");
    expect(button.getAttribute("aria-label")).toContain("Theme: system");
  });
});
