import { Button, Card } from "@/components/ui";

import styles from "./page.module.css";

export default function AgentsPage() {
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Autonomous Agents</h1>
        <p className={styles.secondary}>Run agents to automate complex multi-step tasks.</p>
      </header>

      <div className={styles.grid}>
        <Card header="New Task" className={styles.formCard}>
          <div className={styles.form}>
            <textarea
              className={styles.textarea}
              placeholder="Describe the task for the agent..."
              aria-label="Task description"
            />
            <Button disabled>Execute Agent</Button>
          </div>
        </Card>

        <Card header="Execution History" className={styles.historyCard}>
          <div className={styles.empty}>No task history available.</div>
        </Card>
      </div>
    </div>
  );
}
