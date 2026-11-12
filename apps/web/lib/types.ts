export interface Workspace {
  id: string;
  name: string;
  description: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  document_type: string;
  size_bytes: number;
  chunk_count: number;
  status: string;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export type ChatRole = "user" | "assistant";

export interface Source {
  document_id: string;
  filename: string;
  ordinal: number;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  sources?: Source[];
}

export type Role = "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export type SettingValue = boolean | number | string;
