import Link from "next/link";

import styles from "./app-header.module.css";

export function AppHeader() {
  return (
    <header className={`${styles.header} glass`}>
      <div className={styles.left}>
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
        <div className={styles.status}>
          <span className={`${styles.statusDot} pulse-dot`} aria-hidden="true" />
          <span>Connected</span>
        </div>
      </div>
    </header>
  );
}
