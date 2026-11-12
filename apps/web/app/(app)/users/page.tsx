"use client";

import { type FormEvent, useState } from "react";

import { Button, Card } from "@/components/ui";
import { useMe } from "@/lib/queries/auth";
import { useCreateUser, useUpdateUser, useUsers } from "@/lib/queries/users";
import type { Role } from "@/lib/types";

import styles from "./page.module.css";

const ROLES: Role[] = ["viewer", "member", "admin"];

export default function UsersPage() {
  const { data: me } = useMe();
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [error, setError] = useState<string | null>(null);

  if (me && me.role !== "admin") {
    return (
      <div className={styles.container}>
        <p className={styles.notice}>Admin access required.</p>
      </div>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await createUser.mutateAsync({ email, password, role });
      setEmail("");
      setPassword("");
      setRole("member");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create user");
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Users</h1>
        <p className={styles.secondary}>Manage accounts and roles.</p>
      </header>

      <div className={styles.grid}>
        <Card header="Invite user">
          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.field}>
              <span>Email</span>
              <input
                type="email"
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
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={styles.input}
              />
            </label>

            <label className={styles.field}>
              <span>Role</span>
              <select
                value={role}
                onChange={(event) => setRole(event.target.value as Role)}
                className={styles.input}
              >
                {ROLES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            {error ? <p className={styles.error}>{error}</p> : null}

            <Button type="submit" loading={createUser.isPending}>
              Create user
            </Button>
          </form>
        </Card>

        <Card header="All users">
          {isLoading ? <div className={styles.notice}>Loading…</div> : null}
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {(users ?? []).map((user) => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>
                      <select
                        className={styles.select}
                        value={user.role}
                        onChange={(event) =>
                          updateUser.mutate({
                            id: user.id,
                            role: event.target.value as Role,
                          })
                        }
                      >
                        {ROLES.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={user.is_active}
                        onChange={(event) =>
                          updateUser.mutate({
                            id: user.id,
                            is_active: event.target.checked,
                          })
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
