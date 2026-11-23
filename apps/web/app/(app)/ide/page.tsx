"use client";

import { Button, Card } from "@/components/ui";
import { useMe } from "@/lib/queries/auth";
import { usePublicSettings } from "@/lib/queries/public-settings";
import { useWorkspaces } from "@/lib/queries/workspaces";
import { buildRuntimeUrl } from "@/lib/runtime";
import { useWorkspaceStore } from "@/lib/stores/workspace";

import styles from "./page.module.css";

const IDE_URL = process.env.NEXT_PUBLIC_IDE_URL ?? "http://localhost:8091";

export default function IdePage() {
  const { data: user } = useMe();
  const { data: flags, isLoading } = usePublicSettings();
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const { data: workspaces = [] } = useWorkspaces();
  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;
  const ideUrl = buildRuntimeUrl(IDE_URL, activeWorkspace?.id);
  const enabled = flags?.["features.code_server"] === true;
  const allowed = user?.role === "admin";

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Workspace IDE</h1>
        <p className={styles.secondary}>
          Edit the active workspace in code-server. This optional service is disabled by default.
        </p>
      </header>

      <Card>
        {isLoading ? <p>Loading…</p> : null}
        {!isLoading && !enabled ? (
          <p className={styles.notice}>
            IDE is disabled. Ask an admin to enable <code>features.code_server</code> and start the
            optional <code>runtime</code> profile.
          </p>
        ) : null}
        {!isLoading && enabled && !allowed ? (
          <p className={styles.notice}>IDE access is admin-only.</p>
        ) : null}
        {enabled && allowed ? (
          <div className={styles.actions}>
            <Button variant="primary" onClick={() => window.open(ideUrl, "_blank", "noopener")}>
              {activeWorkspace ? `Open IDE: ${activeWorkspace.name}` : "Open IDE"}
            </Button>
            <span className={styles.url}>{ideUrl}</span>
          </div>
        ) : null}
      </Card>

      {enabled && allowed ? (
        <section className={styles.frameSection} aria-label="Workspace IDE">
          <iframe className={styles.frame} src={ideUrl} title="Workspace IDE" />
        </section>
      ) : null}
    </div>
  );
}
