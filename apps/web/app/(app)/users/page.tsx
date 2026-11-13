"use client";

import { type FormEvent, useState } from "react";

import { Button, Card, Select, Switch } from "@/components/ui";
import { useMe } from "@/lib/queries/auth";
import { useCreateUser, useUpdateUser, useUsers } from "@/lib/queries/users";
import type { Role } from "@/lib/types";

import styles from "./page.module.css";

const ROLES: Role[] = ["viewer", "member", "admin"];
const ROLE_OPTIONS = ROLES.map((role) => ({
  value: role,
  label: role[0].toUpperCase() + role.slice(1),
}));

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

            <div className={styles.field}>
              <span>Role</span>
              <Select
                label="Role"
                value={role}
                onChange={(event) => setRole(event.target.value as Role)}
                options={ROLE_OPTIONS}
              />
            </div>

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
                    <td data-label="Email">{user.email}</td>
                    <td data-label="Role">
                      <Select
                        label={`Role for ${user.email}`}
                        value={user.role}
                        onChange={(event) =>
                          updateUser.mutate({
                            id: user.id,
                            role: event.target.value as Role,
                          })
                        }
                        options={ROLE_OPTIONS}
                      />
                    </td>
                    <td data-label="Active">
                      <Switch
                        label={`Active for ${user.email}`}
                        checked={user.is_active}
                        onChange={(checked) =>
                          updateUser.mutate({
                            id: user.id,
                            is_active: checked,
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
