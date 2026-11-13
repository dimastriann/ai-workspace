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
  folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FolderRecord {
  id: string;
  workspace_id: string;
  parent_id: string | null;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface FolderTree extends FolderRecord {
  children: FolderTree[];
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

export interface Skill {
  name: string;
  description: string;
  permissions: string[];
  version: string;
}

export interface AgentToolEvent {
  id: string;
  tool: string;
  status: string;
  output: string;
}

export interface AgentRunSummary {
  id: string;
  instruction: string;
  skill: string | null;
  status: string;
  created_at: string;
}

export interface AgentStep {
  ordinal: number;
  kind: string;
  tool_name: string | null;
  input: string | null;
  output: string | null;
  status: string;
}

export interface AgentRunDetail extends AgentRunSummary {
  result: string | null;
  error: string | null;
  steps: AgentStep[];
}

export type ConversionFormat = "markdown" | "json" | "both";

export interface Conversion {
  id: string;
  document_id: string;
  status: string;
  format: ConversionFormat;
  include_images: boolean;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResult {
  document_id: string;
  filename: string;
  document_type: string;
  chunk_count: number;
  message: string;
}
