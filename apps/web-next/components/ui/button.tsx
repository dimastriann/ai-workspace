"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  const classes = [styles.button, styles[`variant-${variant}`], styles[`size-${size}`], className]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} disabled={disabled || loading} type={type} {...rest}>
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
