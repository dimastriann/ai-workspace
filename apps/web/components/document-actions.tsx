"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import styles from "./document-actions.module.css";

const MENU_WIDTH = 160;
const MENU_HEIGHT = 128;

interface DocumentActionsProps {
  filename: string;
  onMove: () => void;
  onConvert: () => void;
  onDelete: () => void;
}

interface MenuPosition {
  top: number;
  left: number;
}

export function DocumentActions({ filename, onMove, onConvert, onDelete }: DocumentActionsProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<MenuPosition | null>(null);

  function openMenu() {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }
    const rect = trigger.getBoundingClientRect();
    const openUp = rect.bottom + MENU_HEIGHT > window.innerHeight;
    setPosition({
      top: openUp ? rect.top - MENU_HEIGHT - 4 : rect.bottom + 4,
      left: Math.max(8, Math.min(rect.right - MENU_WIDTH, window.innerWidth - MENU_WIDTH - 8)),
    });
    setOpen(true);
  }

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    }

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKey);
    const firstItem = menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]');
    firstItem?.focus();

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  function handleMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [],
    );
    const current = items.indexOf(document.activeElement as HTMLButtonElement);

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      const next = (current + delta + items.length) % items.length;
      items[next]?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      items[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      items[items.length - 1]?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  function run(action: () => void) {
    setOpen(false);
    action();
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-label={`Actions for ${filename}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openMenu();
          }
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <circle cx="12" cy="5" r="1.6" />
          <circle cx="12" cy="12" r="1.6" />
          <circle cx="12" cy="19" r="1.6" />
        </svg>
      </button>

      {open && position
        ? createPortal(
            <div
              ref={menuRef}
              role="menu"
              aria-label={`Actions for ${filename}`}
              className={styles.menu}
              style={{ top: position.top, left: position.left }}
              onKeyDown={handleMenuKeyDown}
            >
              <button
                type="button"
                role="menuitem"
                className={styles.item}
                onClick={() => run(onMove)}
              >
                Move
              </button>
              <button
                type="button"
                role="menuitem"
                className={styles.item}
                onClick={() => run(onConvert)}
              >
                Convert
              </button>
              <button
                type="button"
                role="menuitem"
                className={`${styles.item} ${styles.danger}`}
                onClick={() => run(onDelete)}
              >
                Delete
              </button>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
