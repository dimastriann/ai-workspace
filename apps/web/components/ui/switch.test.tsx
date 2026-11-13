import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Switch } from "./switch";

describe("Switch", () => {
  it("exposes switch semantics", () => {
    render(<Switch checked={false} onChange={() => {}} label="Images" />);

    expect(screen.getByRole("switch", { name: "Images" })).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with the next value", async () => {
    const onChange = vi.fn();
    render(<Switch checked={false} onChange={onChange} label="Images" />);

    await userEvent.click(screen.getByRole("switch", { name: "Images" }));

    expect(onChange).toHaveBeenCalledWith(true);
  });
});
