"use client";

import { create } from "zustand";

interface WorkspaceState {
  currentWorkspaceId: string | null;
  currentProjectId: string | null;
  setWorkspace: (id: string | null) => void;
  setProject: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  currentWorkspaceId: null,
  currentProjectId: null,
  setWorkspace: (id) => set({ currentWorkspaceId: id, currentProjectId: null }),
  setProject: (id) => set({ currentProjectId: id }),
}));
