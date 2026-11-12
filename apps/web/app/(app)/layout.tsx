import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";

import styles from "./layout.module.css";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.layout}>
      <AppHeader />
      <div className={styles.body}>
        <AppSidebar />
        <main className={styles.main}>{children}</main>
      </div>
    </div>
  );
}
