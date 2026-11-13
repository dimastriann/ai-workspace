"use client";

import { type FormEvent, useEffect, useState } from "react";

import { Button, Modal, Select } from "@/components/ui";
import { useCreateWorkspace, useWorkspaces } from "@/lib/queries/workspaces";
import { useWorkspaceStore } from "@/lib/stores/workspace";

import styles from "./workspace-switcher.module.css";

const NEW_WORKSPACE = "__new__";

export function WorkspaceSwitcher() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const createWorkspace = useCreateWorkspace();
  const currentWorkspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  const setWorkspace = useWorkspaceStore((state) => state.setWorkspace);

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId && workspaces && workspaces.length > 0) {
      setWorkspace(workspaces[0].id);
    }
  }, [currentWorkspaceId, workspaces, setWorkspace]);

  function closeCreate() {
    setCreateOpen(false);
    setName("");
    setDescription("");
    setError(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Workspace name is required.");
      return;
    }

    setError(null);
    try {
      const workspace = await createWorkspace.mutateAsync({
        name: trimmed,
        description: description.trim(),
      });
      setWorkspace(workspace.id);
      closeCreate();
    } catch {
      setError("Failed to create workspace.");
    }
  }

  if (isLoading) {
    return <p className={styles.loading}>Loading workspaces…</p>;
  }

  if (!workspaces || workspaces.length === 0) {
    return (
      <>
        <Button
          className={styles.newButton}
          variant="secondary"
          size="sm"
          onClick={() => setCreateOpen(true)}
        >
          Create workspace
        </Button>
        <CreateWorkspaceModal
          open={createOpen}
          name={name}
          description={description}
          error={error}
          loading={createWorkspace.isPending}
          onNameChange={setName}
          onDescriptionChange={setDescription}
          onClose={closeCreate}
          onSubmit={handleCreate}
        />
      </>
    );
  }

  return (
    <>
      <div className={styles.switcher}>
        <Select
          label="Workspace"
          value={currentWorkspaceId ?? ""}
          onChange={(next) => {
            if (next === NEW_WORKSPACE) {
              setCreateOpen(true);
              return;
            }
            setWorkspace(next);
          }}
          options={[
            ...workspaces.map((workspace) => ({
              value: workspace.id,
              label: workspace.name,
            })),
            { value: NEW_WORKSPACE, label: "+ New workspace" },
          ]}
        />
      </div>

      <CreateWorkspaceModal
        open={createOpen}
        name={name}
        description={description}
        error={error}
        loading={createWorkspace.isPending}
        onNameChange={setName}
        onDescriptionChange={setDescription}
        onClose={closeCreate}
        onSubmit={handleCreate}
      />
    </>
  );
}

interface CreateWorkspaceModalProps {
  open: boolean;
  name: string;
  description: string;
  error: string | null;
  loading: boolean;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function CreateWorkspaceModal({
  open,
  name,
  description,
  error,
  loading,
  onNameChange,
  onDescriptionChange,
  onClose,
  onSubmit,
}: CreateWorkspaceModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New workspace"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="create-workspace" loading={loading}>
            Create
          </Button>
        </>
      }
    >
      <form id="create-workspace" className={styles.form} onSubmit={onSubmit}>
        <label className={styles.field}>
          <span>Name</span>
          <input
            className={styles.input}
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            maxLength={100}
            required
          />
        </label>

        <label className={styles.field}>
          <span>Description (optional)</span>
          <textarea
            className={styles.textarea}
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            maxLength={500}
            rows={3}
          />
        </label>

        {error ? <p className={styles.error}>{error}</p> : null}
      </form>
    </Modal>
  );
}
