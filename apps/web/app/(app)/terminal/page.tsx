"use client";

import { Button, Card } from "@/components/ui";
import { useMe } from "@/lib/queries/auth";
import { usePublicSettings } from "@/lib/queries/public-settings";
import { useWorkspaces } from "@/lib/queries/workspaces";
import { useWorkspaceStore } from "@/lib/stores/workspace";

import styles from "./page.module.css";

const TERMINAL_URL = process.env.NEXT_PUBLIC_TERMINAL_URL ?? "http://localhost:8092";

export default function TerminalPage() {
  const { data: user } = useMe();
  const { data: flags, isLoading } = usePublicSettings();
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const { data: workspaces = [] } = useWorkspaces();
  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;
  const enabled = flags?.["features.terminal"] === true;
  const allowed = user?.role === "member" || user?.role === "admin";

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Workspace Terminal</h1>
        <p className={styles.secondary}>
          Browse the workspace files in a read-only terminal. This optional service is disabled by
          default.
        </p>
      </header>

      <Card>
        {isLoading ? <p>Loading…</p> : null}
        {!isLoading && !enabled ? (
          <p className={styles.notice}>
            Terminal is disabled. Ask an admin to enable <code>features.terminal</code> and start
            the optional <code>runtime</code> profile.
          </p>
        ) : null}
        {!isLoading && enabled && !allowed ? (
          <p className={styles.notice}>Terminal access requires member access.</p>
        ) : null}
        {enabled && allowed ? (
          <>
            <div className={styles.actions}>
              <Button
                variant="primary"
                onClick={() => window.open(TERMINAL_URL, "_blank", "noopener")}
              >
                Open terminal
              </Button>
              <span className={styles.url}>{TERMINAL_URL}</span>
            </div>
            {activeWorkspace ? (
              <p className={styles.notice}>
                Active workspace: <strong>{activeWorkspace.name}</strong> — the shell starts at the
                shared root; its files are in{" "}
                <code>/home/coder/workspace/{activeWorkspace.id}</code>.
              </p>
            ) : null}
          </>
        ) : null}
      </Card>

      {enabled && allowed ? (
        <section className={styles.frameSection} aria-label="Workspace terminal">
          <iframe className={styles.frame} src={TERMINAL_URL} title="Workspace terminal" />
        </section>
      ) : null}
    </div>
  );
}
