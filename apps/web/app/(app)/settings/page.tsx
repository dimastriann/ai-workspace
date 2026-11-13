"use client";

import { useState } from "react";

import { Button, Card, Switch } from "@/components/ui";
import { useMe } from "@/lib/queries/auth";
import { useSettings, useUpdateSetting } from "@/lib/queries/settings";
import type { SettingValue } from "@/lib/types";

import styles from "./page.module.css";

function isSecret(key: string): boolean {
  return key.includes("api_key") || key.includes("secret");
}

function SettingRow({ name, value }: { name: string; value: SettingValue }) {
  const update = useUpdateSetting();
  const secret = isSecret(name);
  const [draft, setDraft] = useState(
    typeof value === "string" && value !== "********" ? value : "",
  );

  if (typeof value === "boolean") {
    return (
      <div className={styles.row}>
        <code className={styles.label}>{name}</code>
        <div className={styles.toggle}>
          <Switch
            checked={value}
            label={name}
            onChange={(checked) => update.mutate({ key: name, value: checked })}
          />
          <span>{value ? "Enabled" : "Disabled"}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.row}>
      <code className={styles.label}>{name}</code>
      <div className={styles.inputGroup}>
        <input
          className={styles.input}
          type={secret ? "password" : "text"}
          value={draft}
          placeholder={secret ? "••••••••" : ""}
          onChange={(event) => setDraft(event.target.value)}
        />
        <Button
          size="sm"
          variant="secondary"
          loading={update.isPending}
          disabled={secret && draft.length === 0}
          onClick={() =>
            update.mutate({ key: name, value: draft }, { onSuccess: () => secret && setDraft("") })
          }
        >
          Save
        </Button>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { data: user } = useMe();
  const { data: settings, isLoading, error } = useSettings();

  if (user && user.role !== "admin") {
    return (
      <div className={styles.container}>
        <p className={styles.notice}>Admin access required.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.secondary}>Global configuration and feature flags.</p>
      </header>

      <Card header="Platform settings">
        {isLoading ? <div className={styles.notice}>Loading…</div> : null}
        {error ? <div className={styles.notice}>Failed to load settings.</div> : null}
        {settings ? (
          <div className={styles.rows}>
            {Object.entries(settings).map(([key, value]) => (
              <SettingRow key={key} name={key} value={value} />
            ))}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
