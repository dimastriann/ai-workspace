"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button, Card, Select } from "@/components/ui";
import { useAgentStream } from "@/lib/hooks/use-agent-stream";
import { agentKeys, useAgentRuns, useSkills } from "@/lib/queries/agents";
import { useWorkspaceStore } from "@/lib/stores/workspace";

import styles from "./page.module.css";

export default function AgentsPage() {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const queryClient = useQueryClient();
  const { data: skills = [] } = useSkills();
  const { data: runs = [] } = useAgentRuns(workspaceId);
  const { output, tools, status, runId, error, send, reset } = useAgentStream();

  const [instruction, setInstruction] = useState("");
  const [skill, setSkill] = useState("");

  const busy = status === "running";
  const canRun = Boolean(workspaceId) && instruction.trim().length > 0 && !busy;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || busy) {
      return;
    }

    await send(instruction, workspaceId, skill || null);
    if (workspaceId) {
      await queryClient.invalidateQueries({
        queryKey: agentKeys.runs(workspaceId),
      });
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Autonomous Agents</h1>
        <p className={styles.secondary}>
          Run a bounded tool-calling agent over your workspace documents.
        </p>
      </header>

      <div className={styles.grid}>
        <Card header="New Task">
          <form className={styles.form} onSubmit={handleSubmit}>
            <textarea
              className={styles.textarea}
              placeholder="Describe the task for the agent..."
              aria-label="Task description"
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              disabled={busy}
            />

            <div className={styles.field}>
              <span>Skill</span>
              <Select
                label="Skill"
                value={skill}
                onChange={(next) => setSkill(next)}
                disabled={busy}
                options={[
                  { value: "", label: "Default (search + calculator)" },
                  ...skills.map((item) => ({
                    value: item.name,
                    label: `${item.name} — ${item.description}`,
                  })),
                ]}
              />
            </div>

            {!workspaceId ? <p className={styles.hint}>Select a workspace first.</p> : null}

            <div className={styles.actions}>
              <Button type="submit" loading={busy} disabled={!canRun}>
                Execute Agent
              </Button>
              {status !== "idle" ? (
                <Button type="button" variant="ghost" onClick={reset}>
                  Clear
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <Card
          className={styles.runCard}
          header={
            <div className={styles.runHeader}>
              <span>Run</span>
              <span className={`${styles.status} ${styles[status] ?? ""}`}>{status}</span>
            </div>
          }
        >
          {tools.length > 0 ? (
            <div className={styles.tools}>
              {tools.map((tool) => (
                <div key={tool.id} className={styles.tool}>
                  <span className={styles.toolName}>{tool.tool}</span>
                  <span className={tool.status === "completed" ? styles.ok : styles.fail}>
                    {tool.status}
                  </span>
                  <span className={styles.toolOutput}>{tool.output}</span>
                </div>
              ))}
            </div>
          ) : null}

          {output ? (
            <pre className={styles.output}>{output}</pre>
          ) : (
            <div className={styles.empty}>No output yet.</div>
          )}

          {runId ? <div className={styles.runId}>run {runId}</div> : null}
          {error ? <p className={styles.error}>{error}</p> : null}
        </Card>
      </div>

      <Card className={styles.history} header="Recent runs">
        {runs.length === 0 ? (
          <div className={styles.empty}>No task history available.</div>
        ) : (
          <div className={styles.runs}>
            {runs.map((run) => (
              <div key={run.id} className={styles.runRow}>
                <span className={styles.runInstruction}>{run.instruction}</span>
                <span className={styles.runSkill}>{run.skill ?? "default"}</span>
                <span className={`${styles.status} ${styles[run.status] ?? ""}`}>{run.status}</span>
                <span className={styles.runDate}>{new Date(run.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
