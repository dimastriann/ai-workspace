"use client";

import type { SelectHTMLAttributes } from "react";

import styles from "./select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  label?: string;
}

export function Select({ options, label, className, ...rest }: SelectProps) {
  const classes = [styles.select, className].filter(Boolean).join(" ");

  return (
    <span className={styles.wrapper}>
      <select className={classes} aria-label={label} {...rest}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <svg
        className={styles.chevron}
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </span>
  );
}
