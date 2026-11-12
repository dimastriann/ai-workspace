import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";
import { AuthGuard } from "@/components/auth-guard";

import styles from "./layout.module.css";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.layout}>
      <AppHeader />
      <div className={styles.body}>
        <AppSidebar />
        <main className={styles.main}>
          <AuthGuard>{children}</AuthGuard>
        </main>
      </div>
    </div>
  );
}
