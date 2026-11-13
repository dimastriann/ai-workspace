"use client";

import Link from "next/link";

import { useUiStore } from "@/lib/stores/ui";

import styles from "./app-header.module.css";
import { ThemeToggle } from "./theme-toggle";

export function AppHeader() {
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);

  return (
    <header className={`${styles.header} glass dark-chrome`}>
      <div className={styles.left}>
        <button
          type="button"
          className={styles.menuButton}
          aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={sidebarOpen}
          aria-controls="app-sidebar"
          onClick={toggleSidebar}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon} aria-hidden="true">
            🧠
          </span>
          <span className={`${styles.logoText} gradient-text`}>AI Workspace</span>
        </Link>
      </div>

      <div className={styles.center}>
        <div className={styles.searchBar}>
          <svg
            className={styles.searchIcon}
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input type="text" placeholder="Search workspace..." className={styles.searchInput} />
        </div>
      </div>

      <div className={styles.right}>
        <ThemeToggle />
        <div className={styles.status}>
          <span className={`${styles.statusDot} pulse-dot`} aria-hidden="true" />
          <span>Connected</span>
        </div>
      </div>
    </header>
  );
}
