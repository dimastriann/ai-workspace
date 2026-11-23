export const RUNTIME_WORKSPACE_ROOT = "/home/coder/workspace";

/**
 * Build a runtime service URL that opens the active workspace directory.
 * Runtime services mount the uploads volume at RUNTIME_WORKSPACE_ROOT with
 * one subdirectory per workspace (named by workspace id).
 */
export function buildRuntimeUrl(baseUrl: string, workspaceId?: string | null): string {
  if (!workspaceId) return baseUrl;
  const folder = `${RUNTIME_WORKSPACE_ROOT}/${workspaceId}`;
  const sep = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${sep}folder=${encodeURIComponent(folder)}`;
}
