"use client";

import type { FolderTree } from "@/lib/types";

import styles from "./folder-tree.module.css";

interface FolderTreeProps {
  folders: FolderTree[];
  selectedId: string | null;
  onSelect: (folderId: string | null) => void;
  onEdit: (folder: FolderTree) => void;
  onDelete: (folder: FolderTree) => void;
}

export function FolderTreeView({
  folders,
  selectedId,
  onSelect,
  onEdit,
  onDelete,
}: FolderTreeProps) {
  return (
    <div className={styles.tree}>
      <button
        type="button"
        className={`${styles.row} ${styles.allRow} ${selectedId === null ? styles.selected : ""}`}
        onClick={() => onSelect(null)}
      >
        <span className={styles.icon} aria-hidden="true">
          🗂️
        </span>
        <span className={styles.name}>All documents</span>
      </button>

      {folders.length === 0 ? (
        <p className={styles.empty}>No folders yet.</p>
      ) : (
        folders.map((folder) => (
          <FolderNode
            key={folder.id}
            folder={folder}
            depth={0}
            selectedId={selectedId}
            onSelect={onSelect}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))
      )}
    </div>
  );
}

interface FolderNodeProps extends Omit<FolderTreeProps, "folders"> {
  folder: FolderTree;
  depth: number;
}

function FolderNode({ folder, depth, selectedId, onSelect, onEdit, onDelete }: FolderNodeProps) {
  return (
    <div>
      <div
        className={`${styles.row} ${selectedId === folder.id ? styles.selected : ""}`}
        style={{ paddingLeft: `${depth * 14}px` }}
      >
        <button type="button" className={styles.select} onClick={() => onSelect(folder.id)}>
          <span className={styles.icon} aria-hidden="true">
            📁
          </span>
          <span className={styles.name}>{folder.name}</span>
        </button>
        <span className={styles.actions}>
          <button
            type="button"
            className={styles.action}
            aria-label={`Edit ${folder.name}`}
            onClick={() => onEdit(folder)}
          >
            Edit
          </button>
          <button
            type="button"
            className={`${styles.action} ${styles.danger}`}
            aria-label={`Delete ${folder.name}`}
            onClick={() => onDelete(folder)}
          >
            Delete
          </button>
        </span>
      </div>

      {folder.children.map((child) => (
        <FolderNode
          key={child.id}
          folder={child}
          depth={depth + 1}
          selectedId={selectedId}
          onSelect={onSelect}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
