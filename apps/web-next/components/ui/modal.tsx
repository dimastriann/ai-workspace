"use client";

import { type ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";

import styles from "./modal.module.css";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: ReactNode;
  footer?: ReactNode;
}

export function Modal({ open, onClose, title = "", children, footer }: ModalProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    // biome-ignore lint/a11y: backdrop click and Escape both close the dialog.
    <div
      className={styles.overlay}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className={styles.container} role="dialog" aria-modal="true" aria-label={title}>
        <div className={styles.header}>
          <h3 className={styles.title}>{title}</h3>
          <button className={styles.close} onClick={onClose} aria-label="Close modal" type="button">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className={styles.body}>{children}</div>
        {footer ? <div className={styles.footer}>{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
