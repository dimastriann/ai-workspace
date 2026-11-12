import type { ReactNode } from "react";

import styles from "./card.module.css";

export interface CardProps {
  header?: ReactNode;
  footer?: ReactNode;
  hoverable?: boolean;
  className?: string;
  children?: ReactNode;
}

export function Card({ header, footer, hoverable = false, className, children }: CardProps) {
  const classes = [styles.card, hoverable ? styles.hoverable : "", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      {header ? <div className={styles.header}>{header}</div> : null}
      <div className={styles.body}>{children}</div>
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </div>
  );
}
