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
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
}
