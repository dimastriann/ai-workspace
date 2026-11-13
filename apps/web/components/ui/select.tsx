"use client";

import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import styles from "./select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
}

interface Position {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

export function Select({
  options,
  value,
  onChange,
  label,
  placeholder = "Select…",
  disabled = false,
  className,
  id,
}: SelectProps) {
  const baseId = useId();
  const listboxId = `${baseId}-listbox`;
  const wrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [position, setPosition] = useState<Position | null>(null);

  const selectedIndex = useMemo(
    () => options.findIndex((option) => option.value === value),
    [options, value],
  );
  const selected = selectedIndex >= 0 ? options[selectedIndex] : undefined;

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const rect = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const spaceAbove = rect.top - 8;
    const estimated = Math.min(options.length * 38 + 12, 280);
    const openUp = spaceBelow < estimated && spaceAbove > spaceBelow;
    const maxHeight = Math.max(120, Math.min(280, openUp ? spaceAbove : spaceBelow));

    setPosition({
      top: openUp ? Math.max(8, rect.top - maxHeight - 4) : rect.bottom + 4,
      left: rect.left,
      width: rect.width,
      maxHeight,
    });
  }, [options.length]);

  const openList = useCallback(() => {
    setActiveIndex(Math.max(selectedIndex, 0));
    updatePosition();
    setOpen(true);
  }, [selectedIndex, updatePosition]);

  const closeList = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  const selectOption = useCallback(
    (next: string) => {
      onChange(next);
      setOpen(false);
      triggerRef.current?.focus();
    },
    [onChange],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);

    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (wrapperRef.current?.contains(target) || listboxRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    switch (event.key) {
      case "ArrowDown":
      case "ArrowUp": {
        event.preventDefault();
        if (!open) {
          openList();
          return;
        }
        if (options.length === 0) {
          return;
        }
        const delta = event.key === "ArrowDown" ? 1 : -1;
        setActiveIndex((index) => (index + delta + options.length) % options.length);
        break;
      }
      case "Home":
        if (open && options.length > 0) {
          event.preventDefault();
          setActiveIndex(0);
        }
        break;
      case "End":
        if (open && options.length > 0) {
          event.preventDefault();
          setActiveIndex(options.length - 1);
        }
        break;
      case "Enter":
      case " ": {
        event.preventDefault();
        if (!open) {
          openList();
        } else if (options[activeIndex]) {
          selectOption(options[activeIndex].value);
        }
        break;
      }
      case "Escape":
        if (open) {
          event.preventDefault();
          closeList();
        }
        break;
      case "Tab":
        if (open) {
          setOpen(false);
        }
        break;
    }
  }

  return (
    <div ref={wrapperRef} className={[styles.wrapper, className].filter(Boolean).join(" ")}>
      <button
        ref={triggerRef}
        id={id}
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={open ? listboxId : undefined}
        aria-activedescendant={open ? `${baseId}-option-${activeIndex}` : undefined}
        aria-label={label ?? selected?.label ?? placeholder}
        disabled={disabled}
        className={styles.trigger}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={handleKeyDown}
      >
        <span className={styles.value}>{selected?.label ?? placeholder}</span>
        <svg
          className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
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
      </button>

      {open && position
        ? createPortal(
            <div
              ref={listboxRef}
              id={listboxId}
              role="listbox"
              tabIndex={-1}
              aria-label={label ?? placeholder}
              className={styles.listbox}
              style={{
                top: position.top,
                left: position.left,
                width: position.width,
                maxHeight: position.maxHeight,
              }}
            >
              {options.length === 0 ? (
                <div className={styles.empty}>No options</div>
              ) : (
                options.map((option, index) => (
                  <div
                    key={option.value}
                    id={`${baseId}-option-${index}`}
                    role="option"
                    tabIndex={-1}
                    aria-selected={option.value === value}
                    className={[
                      styles.option,
                      index === activeIndex ? styles.optionActive : "",
                      option.value === value ? styles.optionSelected : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    onMouseEnter={() => setActiveIndex(index)}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectOption(option.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        selectOption(option.value);
                      }
                    }}
                  >
                    {option.label}
                  </div>
                ))
              )}
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
