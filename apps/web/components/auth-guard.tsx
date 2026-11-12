"use client";

import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { useMe } from "@/lib/queries/auth";

import styles from "./auth-guard.module.css";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useMe();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && user === null) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, user, router, pathname]);

  if (isLoading) {
    return <div className={styles.loading}>Loading…</div>;
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
