"use client";

import { useEffect, useState } from "react";

import { Button, Card, Modal, Select } from "@/components/ui";
import { useWorkflowStream } from "@/lib/hooks/use-workflow-stream";
import {
  useCreateWorkflow,
  useDeleteWorkflow,
  useUpdateWorkflow,
  useWorkflowDetail,
  useWorkflows,
} from "@/lib/queries/workflows";
import type { Skill, WorkflowStepInput, WorkflowSummary } from "@/lib/types";

import styles from "./workflow-panel.module.css";

interface WorkflowPanelProps {
  workspaceId: string | null;
  skills: Skill[];
}

const MAX_STEPS = 10;

interface DraftStep extends WorkflowStepInput {
  key: string;
}

export function WorkflowPanel({ workspaceId, skills }: WorkflowPanelProps) {
  const { data: workflows = [], isLoading } = useWorkflows(workspaceId);
  const createWorkflow = useCreateWorkflow(workspaceId);
  const updateWorkflow = useUpdateWorkflow(workspaceId);
  const deleteWorkflow = useDeleteWorkflow(workspaceId);
  const stream = useWorkflowStream();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [draftSteps, setDraftSteps] = useState<DraftStep[]>([]);
  const [builderError, setBuilderError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<WorkflowSummary | null>(null);
  const [runInput, setRunInput] = useState("");

  const { data: selectedDetail } = useWorkflowDetail(selectedId, Boolean(selectedId));
  const { data: editingDetail } = useWorkflowDetail(
    builderOpen ? editingId : null,
    builderOpen && Boolean(editingId),
  );

  useEffect(() => {
    if (!selectedId && workflows.length > 0) {
      setSelectedId(workflows[0].id);
    }
    if (selectedId && !workflows.some((workflow) => workflow.id === selectedId)) {
      setSelectedId(workflows[0]?.id ?? null);
    }
  }, [workflows, selectedId]);

  useEffect(() => {
    if (!builderOpen || !editingDetail) {
      return;
    }
    setName(editingDetail.name);
    setDescription(editingDetail.description);
    setDraftSteps(
      editingDetail.steps.map((step) => ({
        key: crypto.randomUUID(),
        instruction: step.instruction,
        skill: step.skill,
      })),
    );
  }, [builderOpen, editingDetail]);

  const selected = workflows.find((workflow) => workflow.id === selectedId);
  const busy = stream.status === "running";

  function openCreate() {
    setEditingId(null);
    setName("");
    setDescription("");
    setDraftSteps([{ key: crypto.randomUUID(), instruction: "", skill: null }]);
    setBuilderError(null);
    setBuilderOpen(true);
  }

  function openEdit(workflow: WorkflowSummary) {
    setSelectedId(workflow.id);
    setEditingId(workflow.id);
    setName(workflow.name);
    setDescription(workflow.description);
    setDraftSteps([]);
    setBuilderError(null);
    setBuilderOpen(true);
  }

  function closeBuilder() {
    setBuilderOpen(false);
    setEditingId(null);
    setBuilderError(null);
  }

  function updateStep(index: number, update: Partial<WorkflowStepInput>) {
    setDraftSteps((steps) =>
      steps.map((step, stepIndex) => (stepIndex === index ? { ...step, ...update } : step)),
    );
  }

  function moveStep(index: number, direction: -1 | 1) {
    setDraftSteps((steps) => {
      const target = index + direction;
      if (target < 0 || target >= steps.length) {
        return steps;
      }
      const next = [...steps];
      const [step] = next.splice(index, 1);
      next.splice(target, 0, step);
      return next;
    });
  }

  async function saveWorkflow() {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setBuilderError("Workflow name is required.");
      return;
    }
    if (draftSteps.length === 0) {
      setBuilderError("Add at least one step.");
      return;
    }
    if (draftSteps.some((step) => !step.instruction.trim())) {
      setBuilderError("Every step needs an instruction.");
      return;
    }

    setBuilderError(null);
    try {
      if (editingId) {
        await updateWorkflow.mutateAsync({
          workflowId: editingId,
          name: trimmedName,
          description: description.trim(),
          steps: draftSteps.map(({ instruction, skill }) => ({
            instruction,
            skill,
          })),
        });
        setSelectedId(editingId);
      } else {
        const created = await createWorkflow.mutateAsync({
          name: trimmedName,
          description: description.trim(),
          steps: draftSteps.map(({ instruction, skill }) => ({
            instruction,
            skill,
          })),
        });
        setSelectedId(created.id);
      }
      closeBuilder();
    } catch {
      setBuilderError("Could not save the workflow. Check the name and step skills.");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) {
      return;
    }
    try {
      await deleteWorkflow.mutateAsync(pendingDelete.id);
      if (selectedId === pendingDelete.id) {
        setSelectedId(null);
      }
      setPendingDelete(null);
    } catch {
      setPendingDelete(null);
    }
  }

  async function runWorkflow() {
    if (!selected) {
      return;
    }
    await stream.send(selected.id, runInput);
  }

  return (
    <>
      <div className={styles.grid}>
        <Card
          header={
            <div className={styles.headerRow}>
              <span>Workflows</span>
              <Button size="sm" variant="secondary" onClick={openCreate} disabled={!workspaceId}>
                New workflow
              </Button>
            </div>
          }
        >
          {isLoading ? (
            <p className={styles.muted}>Loading workflows…</p>
          ) : workflows.length === 0 ? (
            <p className={styles.muted}>No workflows yet. Create one to chain agent steps.</p>
          ) : (
            <div className={styles.list}>
              {workflows.map((workflow) => (
                <div
                  key={workflow.id}
                  className={`${styles.workflowRow} ${
                    workflow.id === selectedId ? styles.selected : ""
                  }`}
                >
                  <button
                    type="button"
                    className={styles.workflowSelect}
                    onClick={() => setSelectedId(workflow.id)}
                  >
                    <span className={styles.workflowName}>{workflow.name}</span>
                    <span className={styles.workflowMeta}>
                      {workflow.step_count} step
                      {workflow.step_count === 1 ? "" : "s"}
                    </span>
                  </button>
                  <span className={styles.rowActions}>
                    <button
                      type="button"
                      className={styles.rowAction}
                      aria-label={`Edit ${workflow.name}`}
                      onClick={() => openEdit(workflow)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className={`${styles.rowAction} ${styles.danger}`}
                      aria-label={`Delete ${workflow.name}`}
                      onClick={() => setPendingDelete(workflow)}
                    >
                      Delete
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          className={styles.runCard}
          header={
            <div className={styles.headerRow}>
              <span>{selected ? selected.name : "Run workflow"}</span>
              {selected ? (
                <span className={`${styles.status} ${styles[stream.status] ?? ""}`}>
                  {stream.status}
                </span>
              ) : null}
            </div>
          }
        >
          {!selected ? (
            <p className={styles.muted}>Select or create a workflow first.</p>
          ) : (
            <>
              {selected.description ? (
                <p className={styles.description}>{selected.description}</p>
              ) : null}

              <ol className={styles.stepPreview}>
                {(selectedDetail?.steps ?? []).map((step) => (
                  <li key={step.id}>
                    {step.instruction}
                    {step.skill ? <span className={styles.skillTag}>{step.skill}</span> : null}
                  </li>
                ))}
              </ol>

              <textarea
                className={styles.input}
                placeholder="Optional input for this run..."
                aria-label="Workflow input"
                value={runInput}
                onChange={(event) => setRunInput(event.target.value)}
                disabled={busy}
                rows={2}
              />

              <div className={styles.actions}>
                <Button loading={busy} onClick={runWorkflow}>
                  Run workflow
                </Button>
                {stream.status !== "idle" ? (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      stream.reset();
                      setRunInput("");
                    }}
                  >
                    Clear
                  </Button>
                ) : null}
              </div>

              {stream.steps.length > 0 ? (
                <div className={styles.streamSteps}>
                  {stream.steps.map((step) => (
                    <div key={step.index} className={styles.streamStep}>
                      <div className={styles.streamHeader}>
                        <span>Step {step.index + 1}</span>
                        <span className={`${styles.status} ${styles[step.status] ?? ""}`}>
                          {step.status}
                        </span>
                      </div>
                      <p className={styles.streamInstruction}>{step.instruction}</p>
                      {step.tools.map((tool) => (
                        <div key={tool.id} className={styles.tool}>
                          <span className={styles.toolName}>{tool.tool}</span>
                          <span className={tool.status === "completed" ? styles.ok : styles.fail}>
                            {tool.status}
                          </span>
                          <span className={styles.toolOutput}>{tool.output}</span>
                        </div>
                      ))}
                      {step.output ? <pre className={styles.output}>{step.output}</pre> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className={styles.muted}>No run yet.</p>
              )}

              {stream.runId ? <p className={styles.runId}>run {stream.runId}</p> : null}
              {stream.error ? <p className={styles.error}>{stream.error}</p> : null}
            </>
          )}
        </Card>
      </div>

      <Modal
        open={builderOpen}
        onClose={closeBuilder}
        title={editingId ? "Edit workflow" : "New workflow"}
        footer={
          <>
            <Button variant="ghost" onClick={closeBuilder}>
              Cancel
            </Button>
            <Button
              loading={createWorkflow.isPending || updateWorkflow.isPending}
              onClick={saveWorkflow}
            >
              Save workflow
            </Button>
          </>
        }
      >
        <div className={styles.form}>
          <label className={styles.field}>
            <span>Name</span>
            <input
              className={styles.textInput}
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
            />
          </label>

          <label className={styles.field}>
            <span>Description</span>
            <textarea
              className={styles.input}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={1000}
              rows={2}
            />
          </label>

          <div className={styles.stepsHeader}>
            <span>Steps</span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                setDraftSteps((steps) => [
                  ...steps,
                  { key: crypto.randomUUID(), instruction: "", skill: null },
                ])
              }
              disabled={draftSteps.length >= MAX_STEPS}
            >
              Add step
            </Button>
          </div>

          {draftSteps.map((step, index) => (
            <div key={step.key} className={styles.stepEditor}>
              <div className={styles.stepEditorHeader}>
                <span>Step {index + 1}</span>
                <span className={styles.stepButtons}>
                  <button
                    type="button"
                    className={styles.rowAction}
                    onClick={() => moveStep(index, -1)}
                    disabled={index === 0}
                  >
                    Up
                  </button>
                  <button
                    type="button"
                    className={styles.rowAction}
                    onClick={() => moveStep(index, 1)}
                    disabled={index === draftSteps.length - 1}
                  >
                    Down
                  </button>
                  <button
                    type="button"
                    className={`${styles.rowAction} ${styles.danger}`}
                    onClick={() =>
                      setDraftSteps((steps) => steps.filter((_, stepIndex) => stepIndex !== index))
                    }
                    disabled={draftSteps.length === 1}
                  >
                    Remove
                  </button>
                </span>
              </div>

              <textarea
                className={styles.input}
                placeholder="What should this step do?"
                aria-label={`Step ${index + 1} instruction`}
                value={step.instruction}
                onChange={(event) => updateStep(index, { instruction: event.target.value })}
                rows={3}
                maxLength={4000}
              />

              <Select
                label={`Step ${index + 1} skill`}
                value={step.skill ?? ""}
                onChange={(next) => updateStep(index, { skill: next || null })}
                options={[
                  { value: "", label: "Default tools" },
                  ...skills.map((skill) => ({
                    value: skill.name,
                    label: `${skill.name} — ${skill.description}`,
                  })),
                ]}
              />
            </div>
          ))}

          {builderError ? <p className={styles.error}>{builderError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        title="Delete workflow"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={deleteWorkflow.isPending} onClick={handleDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p>
          Delete <strong>{pendingDelete?.name}</strong>? This does not remove its past runs.
        </p>
      </Modal>
    </>
  );
}
