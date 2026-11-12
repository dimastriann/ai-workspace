"use client";

import { type DragEvent, useRef, useState } from "react";

import { Button, Card } from "@/components/ui";
import { useDocuments, useUploadDocument } from "@/lib/queries/documents";
import { useWorkspaceStore } from "@/lib/stores/workspace";
import type { DocumentRecord } from "@/lib/types";

import styles from "./page.module.css";

interface UploadStatus {
  type: "success" | "error";
  text: string;
}

function formatSize(bytes: number) {
  if (bytes === 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${Number.parseFloat((bytes / 1024 ** index).toFixed(1))} ${units[index]}`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

function statusClass(status: string) {
  if (status === "completed") {
    return styles.statusCompleted;
  }
  if (status === "error") {
    return styles.statusError;
  }
  return styles.statusProcessing;
}

export default function DocumentsPage() {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const { data: documents = [], isLoading } = useDocuments(workspaceId);
  const upload = useUploadDocument(workspaceId);

  const fileInput = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<UploadStatus | null>(null);

  async function handleFile(file: File) {
    setStatus(null);
    try {
      await upload.mutateAsync(file);
      setStatus({ type: "success", text: "Upload successful. Processing started." });
    } catch {
      setStatus({ type: "error", text: "Error uploading file." });
    }
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) {
      void handleFile(file);
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Document Intelligence</h1>
        <p className={styles.secondary}>
          Upload and manage documents for Retrieval-Augmented Generation.
        </p>
      </header>

      <div className={styles.grid}>
        <Card header="Upload Document" className={styles.uploadCard}>
          <Button
            variant="secondary"
            className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
            onClick={() => fileInput.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            disabled={!workspaceId || upload.isPending}
          >
            <input
              ref={fileInput}
              type="file"
              className={styles.hidden}
              accept=".pdf,.md,.csv,.txt,.py,.js,.ts,.rs"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void handleFile(file);
                }
                event.target.value = "";
              }}
            />
            {upload.isPending ? (
              <span className={styles.dropContent}>
                <span className={styles.spinner} aria-hidden="true" />
                <span>Uploading...</span>
              </span>
            ) : (
              <span className={styles.dropContent}>
                <span className={styles.dropIcon} aria-hidden="true">
                  📥
                </span>
                <span className={styles.dropTitle}>Click or drag &amp; drop</span>
                <span className={styles.dropHint}>PDF, MD, CSV, Code</span>
              </span>
            )}
          </Button>

          {status ? (
            <div className={`${styles.status} ${styles[status.type]}`}>{status.text}</div>
          ) : null}
          {!workspaceId ? (
            <div className={`${styles.status} ${styles.error}`}>
              Create or select a workspace first.
            </div>
          ) : null}
        </Card>

        <Card
          className={styles.listCard}
          header={
            <div className={styles.listHeader}>
              <span>Knowledge Base</span>
            </div>
          }
        >
          {isLoading ? (
            <div className={styles.center}>
              <span className={styles.spinner} aria-hidden="true" />
            </div>
          ) : documents.length === 0 ? (
            <div className={styles.empty}>No documents in this workspace.</div>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Chunks</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document: DocumentRecord) => (
                    <tr key={document.id}>
                      <td className={styles.filename}>{document.filename}</td>
                      <td>
                        <span className={styles.badge}>{document.document_type}</span>
                      </td>
                      <td>{formatSize(document.size_bytes)}</td>
                      <td>{document.chunk_count}</td>
                      <td>
                        <span className={`${styles.statusBadge} ${statusClass(document.status)}`}>
                          {document.status}
                        </span>
                      </td>
                      <td>{formatDate(document.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
