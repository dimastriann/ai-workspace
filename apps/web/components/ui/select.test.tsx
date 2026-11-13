import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Select } from "./select";

const options = [
  { value: "viewer", label: "Viewer" },
  { value: "member", label: "Member" },
];

describe("Select", () => {
  it("renders the selected option", () => {
    render(<Select label="Role" options={options} value="viewer" onChange={() => {}} />);

    expect(screen.getByRole("combobox", { name: "Role" })).toHaveTextContent("Viewer");
  });

  it("opens a listbox and selects an option with the mouse", async () => {
    const onChange = vi.fn();
    render(<Select label="Role" options={options} value="viewer" onChange={onChange} />);

    const trigger = screen.getByRole("combobox", { name: "Role" });
    await userEvent.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(screen.getByRole("option", { name: "Member" }));

    expect(onChange).toHaveBeenCalledWith("member");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("supports keyboard navigation", async () => {
    const onChange = vi.fn();
    render(<Select label="Role" options={options} value="viewer" onChange={onChange} />);

    const trigger = screen.getByRole("combobox", { name: "Role" });
    trigger.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard("{ArrowDown}");
    await userEvent.keyboard("{Enter}");

    expect(onChange).toHaveBeenCalledWith("member");
  });

  it("closes on Escape", async () => {
    render(<Select label="Role" options={options} value="viewer" onChange={() => {}} />);

    await userEvent.click(screen.getByRole("combobox", { name: "Role" }));
    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("supports a disabled state", () => {
    render(<Select label="Role" options={options} value="viewer" onChange={() => {}} disabled />);

    expect(screen.getByRole("combobox", { name: "Role" })).toBeDisabled();
  });
});
