"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useEffect, useState } from "react";

import { Button, Card } from "@/components/ui";
import { useLogin, useMe } from "@/lib/queries/auth";

import styles from "./page.module.css";

function safeNext(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }
  return value;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const { data: user, isLoading } = useMe();
  const login = useLogin();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(next);
    }
  }, [isLoading, user, router, next]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await login.mutateAsync({ email, password });
      router.replace(next);
    } catch {
      // The error is rendered from the mutation state.
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.brand}>
        <span aria-hidden="true">🧠</span>
        <span className="gradient-text">AI Workspace</span>
      </div>

      <Card className={styles.card} header="Sign in">
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={styles.input}
            />
          </label>

          <label className={styles.field}>
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={styles.input}
            />
          </label>

          {login.isError ? (
            <p className={styles.error}>
              {login.error instanceof Error ? login.error.message : "Login failed"}
            </p>
          ) : null}

          <Button type="submit" loading={login.isPending}>
            Sign in
          </Button>
        </form>
      </Card>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
