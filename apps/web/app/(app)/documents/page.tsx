"use client";

import { type DragEvent, useRef, useState } from "react";

import { FolderTreeView } from "@/components/folder-tree";
import { Button, Card, Modal, Select, Switch } from "@/components/ui";
import { useConversion, useConvertDocument } from "@/lib/queries/conversions";
import {
  useDeleteDocument,
  useDocuments,
  useMoveDocument,
  useUploadDocument,
} from "@/lib/queries/documents";
import {
  useCreateFolder,
  useDeleteFolder,
  useFolders,
  useUpdateFolder,
} from "@/lib/queries/folders";
import { useWorkspaceStore } from "@/lib/stores/workspace";
import type { ConversionFormat, DocumentRecord, FolderTree } from "@/lib/types";

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

function flattenFolders(folders: FolderTree[], depth = 0): { folder: FolderTree; depth: number }[] {
  return folders.flatMap((folder) => [
    { folder, depth },
    ...flattenFolders(folder.children, depth + 1),
  ]);
}

function folderPath(folders: FolderTree[], folderId: string): string[] {
  for (const folder of folders) {
    if (folder.id === folderId) {
      return [folder.name];
    }
    const childPath = folderPath(folder.children, folderId);
    if (childPath.length > 0) {
      return [folder.name, ...childPath];
    }
  }
  return [];
}

export default function DocumentsPage() {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const { data: documents = [], isLoading } = useDocuments(workspaceId);
  const { data: folders = [] } = useFolders(workspaceId);
  const upload = useUploadDocument(workspaceId);
  const removeDocument = useDeleteDocument(workspaceId);
  const moveDocument = useMoveDocument(workspaceId);
  const createFolder = useCreateFolder(workspaceId);
  const updateFolder = useUpdateFolder(workspaceId);
  const deleteFolder = useDeleteFolder(workspaceId);
  const startConversion = useConvertDocument();

  const fileInput = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<UploadStatus | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [folderModal, setFolderModal] = useState<{
    mode: "create" | "edit";
    folder: FolderTree | null;
  } | null>(null);
  const [folderName, setFolderName] = useState("");
  const [folderParentId, setFolderParentId] = useState("");
  const [folderError, setFolderError] = useState<string | null>(null);
  const [pendingFolderDelete, setPendingFolderDelete] = useState<FolderTree | null>(null);
  const [folderDeleteError, setFolderDeleteError] = useState<string | null>(null);
  const [folderDeleteNeedsMove, setFolderDeleteNeedsMove] = useState(false);
  const [pendingMove, setPendingMove] = useState<DocumentRecord | null>(null);
  const [moveTarget, setMoveTarget] = useState("");
  const [moveError, setMoveError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<DocumentRecord | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pendingConversion, setPendingConversion] = useState<DocumentRecord | null>(null);
  const [includeImages, setIncludeImages] = useState(false);
  const [convertFormat, setConvertFormat] = useState<ConversionFormat>("markdown");
  const [convertError, setConvertError] = useState<string | null>(null);
  const [pendingUpload, setPendingUpload] = useState<File | null>(null);
  const [uploadFormat, setUploadFormat] = useState<"none" | ConversionFormat>("none");
  const [uploadIncludeImages, setUploadIncludeImages] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const conversionQuery = useConversion(pendingConversion?.id ?? null, Boolean(pendingConversion));
  const latestConversion = conversionQuery.data;

  const flatFolders = flattenFolders(folders);
  const folderOptions = [
    { value: "", label: "Root (no folder)" },
    ...flatFolders.map(({ folder, depth }) => ({
      value: folder.id,
      label: `${"  ".repeat(depth)}${folder.name}`,
    })),
  ];
  const currentPath = selectedFolderId ? folderPath(folders, selectedFolderId) : [];
  const visibleDocuments = selectedFolderId
    ? documents.filter((document) => document.folder_id === selectedFolderId)
    : documents;

  function openUpload(file: File) {
    setPendingUpload(file);
    setUploadFormat("none");
    setUploadIncludeImages(false);
    setUploadError(null);
  }

  function closeUpload() {
    setPendingUpload(null);
    setUploadError(null);
  }

  async function handleUpload() {
    if (!pendingUpload) {
      return;
    }
    setUploadError(null);
    try {
      const result = await upload.mutateAsync({
        file: pendingUpload,
        folderId: selectedFolderId,
      });

      if (uploadFormat !== "none") {
        try {
          await startConversion.mutateAsync({
            documentId: result.document_id,
            includeImages: uploadIncludeImages,
            format: uploadFormat,
          });
          setStatus({
            type: "success",
            text: "Upload successful. Conversion queued.",
          });
        } catch {
          setStatus({
            type: "error",
            text: "Uploaded, but the conversion could not start.",
          });
        }
      } else {
        setStatus({ type: "success", text: "Upload successful. Processing started." });
      }
      closeUpload();
    } catch {
      setUploadError("Error uploading file.");
    }
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) {
      openUpload(file);
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

  function openCreateFolder() {
    setFolderModal({ mode: "create", folder: null });
    setFolderName("");
    setFolderParentId(selectedFolderId ?? "");
    setFolderError(null);
  }

  function openEditFolder(folder: FolderTree) {
    setFolderModal({ mode: "edit", folder });
    setFolderName(folder.name);
    setFolderParentId(folder.parent_id ?? "");
    setFolderError(null);
  }

  function closeFolderModal() {
    setFolderModal(null);
    setFolderName("");
    setFolderParentId("");
    setFolderError(null);
  }

  async function handleSaveFolder() {
    if (!folderModal) {
      return;
    }
    const name = folderName.trim();
    if (!name) {
      setFolderError("Folder name is required.");
      return;
    }

    setFolderError(null);
    try {
      if (folderModal.mode === "create") {
        const created = await createFolder.mutateAsync({
          name,
          parentId: folderParentId || null,
        });
        setSelectedFolderId(created.id);
      } else if (folderModal.folder) {
        await updateFolder.mutateAsync({
          folderId: folderModal.folder.id,
          name,
          parentId: folderParentId || null,
        });
      }
      closeFolderModal();
    } catch {
      setFolderError("Failed to save folder. Check for duplicate names or an invalid parent.");
    }
  }

  function openDeleteFolder(folder: FolderTree) {
    setPendingFolderDelete(folder);
    setFolderDeleteError(null);
    setFolderDeleteNeedsMove(false);
  }

  async function handleDeleteFolder(strategy: "reject" | "move_parent") {
    if (!pendingFolderDelete) {
      return;
    }
    setFolderDeleteError(null);
    try {
      await deleteFolder.mutateAsync({
        folderId: pendingFolderDelete.id,
        strategy,
      });
      if (selectedFolderId === pendingFolderDelete.id) {
        setSelectedFolderId(null);
      }
      setPendingFolderDelete(null);
    } catch {
      if (strategy === "reject") {
        setFolderDeleteError("This folder is not empty.");
        setFolderDeleteNeedsMove(true);
      } else {
        setFolderDeleteError("Could not move the contents. Resolve duplicate folder names first.");
      }
    }
  }

  function openMoveDocument(document: DocumentRecord) {
    setPendingMove(document);
    setMoveTarget(document.folder_id ?? "");
    setMoveError(null);
  }

  async function handleMoveDocument() {
    if (!pendingMove) {
      return;
    }
    setMoveError(null);
    try {
      await moveDocument.mutateAsync({
        documentId: pendingMove.id,
        folderId: moveTarget || null,
      });
      setPendingMove(null);
    } catch {
      setMoveError("Failed to move document.");
    }
  }

  function openConversion(document: DocumentRecord) {
    setPendingConversion(document);
    setIncludeImages(false);
    setConvertFormat("markdown");
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
        format: convertFormat,
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
        <div className={styles.sideColumn}>
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
              disabled={!workspaceId}
            >
              <input
                ref={fileInput}
                type="file"
                className={styles.hidden}
                accept=".pdf,.docx,.md,.csv,.txt,.py,.js,.ts,.rs"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    openUpload(file);
                  }
                  event.target.value = "";
                }}
              />
              <span className={styles.dropContent}>
                <span className={styles.dropIcon} aria-hidden="true">
                  📥
                </span>
                <span className={styles.dropTitle}>Click or drag &amp; drop</span>
                <span className={styles.dropHint}>PDF, DOCX, MD, CSV, Code</span>
              </span>
            </Button>

            {status ? (
              <div className={`${styles.status} ${styles[status.type]}`}>{status.text}</div>
            ) : null}
            {!workspaceId ? (
              <div className={`${styles.status} ${styles.error}`}>
                Create or select a workspace first.
              </div>
            ) : null}
            {selectedFolderId ? (
              <p className={styles.uploadHint}>Uploads go to {currentPath.join(" / ")}.</p>
            ) : null}
          </Card>

          <Card
            header={
              <div className={styles.listHeader}>
                <span>Folders</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={openCreateFolder}
                  disabled={!workspaceId}
                >
                  New folder
                </Button>
              </div>
            }
          >
            <FolderTreeView
              folders={folders}
              selectedId={selectedFolderId}
              onSelect={setSelectedFolderId}
              onEdit={openEditFolder}
              onDelete={openDeleteFolder}
            />
          </Card>
        </div>

        <Card
          className={styles.listCard}
          header={
            <div className={styles.listHeader}>
              <div className={styles.listTitle}>
                <span>{selectedFolderId ? currentPath.join(" / ") : "Knowledge Base"}</span>
                <span className={styles.count}>{visibleDocuments.length} documents</span>
              </div>
            </div>
          }
        >
          {isLoading ? (
            <div className={styles.center}>
              <span className={styles.spinner} aria-hidden="true" />
            </div>
          ) : visibleDocuments.length === 0 ? (
            <div className={styles.empty}>
              {selectedFolderId
                ? "No documents in this folder."
                : "No documents in this workspace."}
            </div>
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
                  {visibleDocuments.map((document: DocumentRecord) => (
                    <tr key={document.id}>
                      <td className={styles.filename} data-label="Name">
                        {document.filename}
                      </td>
                      <td data-label="Type">
                        <span className={styles.badge}>{document.document_type}</span>
                      </td>
                      <td data-label="Size">{formatSize(document.size_bytes)}</td>
                      <td data-label="Chunks">{document.chunk_count}</td>
                      <td data-label="Status">
                        <span className={`${styles.statusBadge} ${statusClass(document.status)}`}>
                          {document.status}
                        </span>
                      </td>
                      <td data-label="Created">{formatDate(document.created_at)}</td>
                      <td data-label="Actions">
                        <div className={styles.actions}>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openMoveDocument(document)}
                          >
                            Move
                          </Button>
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
        title="Convert document"
        footer={
          <>
            <Button variant="ghost" onClick={closeConversion}>
              Close
            </Button>
            <Button
              variant="primary"
              loading={startConversion.isPending}
              onClick={handleConvert}
              disabled={
                !pendingConversion ||
                latestConversion?.status === "pending" ||
                latestConversion?.status === "running"
              }
            >
              Convert
            </Button>
          </>
        }
      >
        <p>
          Convert <strong>{pendingConversion?.filename}</strong>.
        </p>

        <div className={styles.field}>
          <span>Output format</span>
          <Select
            label="Output format"
            value={convertFormat}
            onChange={(next) => setConvertFormat(next as ConversionFormat)}
            options={[
              { value: "markdown", label: "Markdown" },
              { value: "json", label: "JSON" },
              { value: "both", label: "Markdown + JSON" },
            ]}
          />
        </div>

        <div className={styles.switchRow}>
          <span>Include images</span>
          <Switch
            checked={includeImages}
            onChange={setIncludeImages}
            label="Include extracted images"
          />
        </div>

        {conversionQuery.isLoading ? <p className={styles.muted}>Checking conversion…</p> : null}

        {latestConversion ? (
          <div className={styles.conversionPanel}>
            <div className={styles.conversionRow}>
              <span>Latest</span>
              <span className={`${styles.statusBadge} ${statusClass(latestConversion.status)}`}>
                {latestConversion.status}
              </span>
            </div>

            {latestConversion.status === "completed" && pendingConversion ? (
              <div className={styles.downloads}>
                {latestConversion.format !== "json" ? (
                  <a
                    className={styles.download}
                    href={`/api/documents/${pendingConversion.id}/markdown`}
                  >
                    Download .md
                  </a>
                ) : null}
                {latestConversion.format !== "markdown" ? (
                  <a
                    className={styles.download}
                    href={`/api/documents/${pendingConversion.id}/json`}
                  >
                    Download .json
                  </a>
                ) : null}
                {latestConversion.format !== "json" && latestConversion.include_images ? (
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
        ) : null}

        {convertError ? <p className={styles.error}>{convertError}</p> : null}
      </Modal>

      <Modal
        open={Boolean(pendingUpload)}
        onClose={closeUpload}
        title="Upload document"
        footer={
          <>
            <Button variant="ghost" onClick={closeUpload}>
              Cancel
            </Button>
            <Button loading={upload.isPending} onClick={handleUpload}>
              Upload
            </Button>
          </>
        }
      >
        <p>
          <strong>{pendingUpload?.name}</strong>
          {pendingUpload ? ` · ${formatSize(pendingUpload.size)}` : null}
        </p>

        <div className={styles.field}>
          <span>After upload</span>
          <Select
            label="After upload"
            value={uploadFormat}
            onChange={(next) => setUploadFormat(next as "none" | ConversionFormat)}
            options={[
              { value: "none", label: "Keep original only" },
              { value: "markdown", label: "Convert to Markdown" },
              { value: "json", label: "Convert to JSON" },
              { value: "both", label: "Convert to Markdown + JSON" },
            ]}
          />
        </div>

        <div className={styles.switchRow}>
          <span>Include images</span>
          <Switch
            checked={uploadIncludeImages}
            onChange={setUploadIncludeImages}
            label="Include extracted images"
            disabled={uploadFormat === "none"}
          />
        </div>

        <p className={styles.muted}>The original file is always kept.</p>
        {uploadError ? <p className={styles.error}>{uploadError}</p> : null}
      </Modal>

      <Modal
        open={Boolean(folderModal)}
        onClose={closeFolderModal}
        title={folderModal?.mode === "create" ? "New folder" : "Edit folder"}
        footer={
          <>
            <Button variant="ghost" onClick={closeFolderModal}>
              Cancel
            </Button>
            <Button
              loading={createFolder.isPending || updateFolder.isPending}
              onClick={handleSaveFolder}
            >
              Save
            </Button>
          </>
        }
      >
        <div className={styles.form}>
          <label className={styles.field}>
            <span>Name</span>
            <input
              className={styles.input}
              value={folderName}
              onChange={(event) => setFolderName(event.target.value)}
              maxLength={255}
              required
            />
          </label>

          <div className={styles.field}>
            <span>Parent</span>
            <Select
              label="Parent folder"
              value={folderParentId}
              onChange={setFolderParentId}
              options={folderOptions}
            />
          </div>

          {folderError ? <p className={styles.error}>{folderError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(pendingFolderDelete)}
        onClose={() => {
          setPendingFolderDelete(null);
          setFolderDeleteError(null);
        }}
        title="Delete folder"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setPendingFolderDelete(null);
                setFolderDeleteError(null);
              }}
            >
              Cancel
            </Button>
            {folderDeleteNeedsMove ? (
              <Button
                variant="danger"
                loading={deleteFolder.isPending}
                onClick={() => handleDeleteFolder("move_parent")}
              >
                Move contents &amp; delete
              </Button>
            ) : (
              <Button
                variant="danger"
                loading={deleteFolder.isPending}
                onClick={() => handleDeleteFolder("reject")}
              >
                Delete
              </Button>
            )}
          </>
        }
      >
        <p>
          Delete <strong>{pendingFolderDelete?.name}</strong>?
        </p>
        {folderDeleteNeedsMove ? (
          <p className={styles.muted}>
            This folder is not empty. Its folders and documents will move to the parent folder.
          </p>
        ) : null}
        {folderDeleteError ? <p className={styles.error}>{folderDeleteError}</p> : null}
      </Modal>

      <Modal
        open={Boolean(pendingMove)}
        onClose={() => {
          setPendingMove(null);
          setMoveError(null);
        }}
        title="Move document"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setPendingMove(null);
                setMoveError(null);
              }}
            >
              Cancel
            </Button>
            <Button loading={moveDocument.isPending} onClick={handleMoveDocument}>
              Move
            </Button>
          </>
        }
      >
        <p>
          Move <strong>{pendingMove?.filename}</strong> to:
        </p>
        <Select
          label="Destination folder"
          value={moveTarget}
          onChange={setMoveTarget}
          options={folderOptions}
        />
        {moveError ? <p className={styles.error}>{moveError}</p> : null}
      </Modal>
    </div>
  );
}
