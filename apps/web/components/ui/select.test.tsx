import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Select } from "./select";

const options = [
  { value: "viewer", label: "Viewer" },
  { value: "member", label: "Member" },
];

describe("Select", () => {
  it("renders options and reports changes", async () => {
    const onChange = vi.fn();
    render(<Select label="Role" options={options} defaultValue="viewer" onChange={onChange} />);

    const select = screen.getByRole("combobox", { name: "Role" });
    await userEvent.selectOptions(select, "member");

    expect(onChange).toHaveBeenCalled();
    expect(select).toHaveValue("member");
  });

  it("supports a disabled state", () => {
    render(<Select label="Role" options={options} disabled />);

    expect(screen.getByRole("combobox", { name: "Role" })).toBeDisabled();
  });
});
