import Link from "next/link";

import { Card } from "@/components/ui";

import styles from "./page.module.css";

const stats = [
  { title: "Active Chats", count: 0, action: "View Chats", href: "/chat" },
  { title: "Documents", count: 0, action: "Manage Docs", href: "/documents" },
  { title: "Agent Tasks", count: 0, action: "Run Task", href: "/agents" },
];

export default function DashboardPage() {
  return (
    <div className={styles.container}>
      <header>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.secondary}>
          Welcome to your AI Workspace. Here is an overview of your active projects.
        </p>
      </header>

      <div className={styles.grid}>
        {stats.map((stat) => (
          <Card
            key={stat.title}
            hoverable
            header={stat.title}
            footer={
              <Link href={stat.href} className={styles.action}>
                {stat.action}
              </Link>
            }
          >
            <div className={`${styles.count} gradient-text`}>{stat.count}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}
