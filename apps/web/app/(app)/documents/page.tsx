"use client";

import { type DragEvent, useRef, useState } from "react";

import { Button, Card, Modal, Switch } from "@/components/ui";
import { useConversion, useConvertDocument } from "@/lib/queries/conversions";
import { useDeleteDocument, useDocuments, useUploadDocument } from "@/lib/queries/documents";
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
  const removeDocument = useDeleteDocument(workspaceId);
  const startConversion = useConvertDocument();

  const fileInput = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<UploadStatus | null>(null);
  const [pendingDelete, setPendingDelete] = useState<DocumentRecord | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pendingConversion, setPendingConversion] = useState<DocumentRecord | null>(null);
  const [includeImages, setIncludeImages] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);
  const conversionQuery = useConversion(pendingConversion?.id ?? null, Boolean(pendingConversion));
  const latestConversion = conversionQuery.data;

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

  async function handleDelete() {
    if (!pendingDelete) {
      return;
    }
    setDeleteError(null);
    try {
      await removeDocument.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch {
      setDeleteError("Failed to delete document.");
    }
  }

  function openConversion(document: DocumentRecord) {
    setPendingConversion(document);
    setIncludeImages(false);
    setConvertError(null);
  }

  function closeConversion() {
    setPendingConversion(null);
    setIncludeImages(false);
    setConvertError(null);
  }

  async function handleConvert() {
    if (!pendingConversion) {
      return;
    }
    setConvertError(null);
    try {
      await startConversion.mutateAsync({
        documentId: pendingConversion.id,
        includeImages,
      });
    } catch {
      setConvertError("Failed to start conversion.");
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
                    <th>Actions</th>
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
                      <td>
                        <div className={styles.actions}>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openConversion(document)}
                          >
                            Convert
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setPendingDelete(document)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => {
          setPendingDelete(null);
          setDeleteError(null);
        }}
        title="Delete document"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={removeDocument.isPending} onClick={handleDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p>
          Delete <strong>{pendingDelete?.filename}</strong>? This removes its chunks and stored
          file.
        </p>
        {deleteError ? <p className={styles.error}>{deleteError}</p> : null}
      </Modal>

      <Modal
        open={Boolean(pendingConversion)}
        onClose={closeConversion}
        title="Convert to Markdown"
        footer={
          <>
            <Button variant="ghost" onClick={closeConversion}>
              Close
            </Button>
            {!conversionQuery.isLoading &&
            (!latestConversion || latestConversion.status === "error") ? (
              <Button
                variant="primary"
                loading={startConversion.isPending}
                onClick={handleConvert}
                disabled={!pendingConversion}
              >
                Convert
              </Button>
            ) : null}
          </>
        }
      >
        <p>
          Convert <strong>{pendingConversion?.filename}</strong> to Markdown.
        </p>

        {conversionQuery.isLoading ? (
          <p className={styles.muted}>Checking conversion…</p>
        ) : latestConversion ? (
          <div className={styles.conversionPanel}>
            <div className={styles.conversionRow}>
              <span>Status</span>
              <span className={`${styles.statusBadge} ${statusClass(latestConversion.status)}`}>
                {latestConversion.status}
              </span>
            </div>

            {latestConversion.status === "completed" && pendingConversion ? (
              <div className={styles.downloads}>
                <a
                  className={styles.download}
                  href={`/api/documents/${pendingConversion.id}/markdown`}
                >
                  Download .md
                </a>
                {latestConversion.include_images ? (
                  <a
                    className={styles.download}
                    href={`/api/documents/${pendingConversion.id}/markdown-zip`}
                  >
                    Download .zip (with images)
                  </a>
                ) : null}
              </div>
            ) : null}

            {latestConversion.status === "pending" || latestConversion.status === "running" ? (
              <p className={styles.muted}>Processing… this can take a few seconds.</p>
            ) : null}

            {latestConversion.status === "error" ? (
              <p className={styles.error}>{latestConversion.error ?? "Conversion failed."}</p>
            ) : null}
          </div>
        ) : (
          <div className={styles.switchRow}>
            <span>Include images</span>
            <Switch
              checked={includeImages}
              onChange={setIncludeImages}
              label="Include images in the Markdown output"
            />
          </div>
        )}

        {convertError ? <p className={styles.error}>{convertError}</p> : null}
      </Modal>
    </div>
  );
}
