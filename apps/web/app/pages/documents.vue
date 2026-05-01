<template>
  <div class="page-container fade-in">
    <header class="page-header mb-6">
      <h1 class="text-3xl font-bold">Document Intelligence</h1>
      <p class="text-secondary mt-2">Upload and manage documents for Retrieval-Augmented Generation.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Upload area -->
      <BaseCard class="lg:col-span-1">
        <template #header>Upload Document</template>
        <div 
          class="upload-zone"
          :class="{ dragging: isDragging, processing: isUploading }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="($refs.fileInput as HTMLInputElement).click()"
        >
          <input 
            ref="fileInput" 
            type="file" 
            class="hidden" 
            @change="handleFileSelect"
            accept=".pdf,.md,.csv,.txt,.py,.js,.ts,.rs"
          />
          <div v-if="!isUploading" class="upload-content">
            <span class="icon text-3xl">📥</span>
            <p class="text-sm mt-2">Click or drag & drop</p>
            <p class="text-xs text-muted mt-1">PDF, MD, CSV, Code</p>
          </div>
          <div v-else class="upload-content">
            <div class="spinner mb-2"></div>
            <p class="text-sm">Uploading...</p>
          </div>
        </div>
        
        <div v-if="uploadStatus" :class="['status-msg', uploadStatus.type]">
          {{ uploadStatus.text }}
        </div>
      </BaseCard>

      <!-- Document List -->
      <BaseCard class="lg:col-span-3">
        <template #header>
          <div class="flex justify-between items-center w-full">
            <span>Knowledge Base</span>
            <BaseButton variant="ghost" size="sm" @click="fetchDocuments">Refresh</BaseButton>
          </div>
        </template>
        
        <div class="document-list">
          <div v-if="isLoading" class="flex justify-center py-12">
            <div class="spinner"></div>
          </div>
          <div v-else-if="documents.length === 0" class="empty-state py-12">
            No documents in this workspace.
          </div>
          <table v-else class="doc-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in documents" :key="doc.id">
                <td class="font-medium">{{ doc.filename }}</td>
                <td><span class="badge">{{ doc.document_type }}</span></td>
                <td>{{ formatSize(doc.size_bytes) }}</td>
                <td>
                  <span :class="['status-badge', doc.status]">
                    {{ doc.status }}
                  </span>
                </td>
                <td>{{ formatDate(doc.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Documents Page — File Management & Upload
 */

const isDragging = ref(false);
const isUploading = ref(false);
const isLoading = ref(false);
const uploadStatus = ref<{ type: 'success' | 'error', text: string } | null>(null);
const documents = ref<any[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);

const workspaceStore = useWorkspaceStore();

onMounted(() => {
  // Ensure we have at least one workspace to upload to
  // For Phase 2, we expect the user to have run migrations and potentially created a workspace via API
  fetchDocuments();
});

async function fetchDocuments() {
  isLoading.value = true;
  try {
    // In actual use, we'd get the WS ID from a store
    const res = await fetch(`/api/documents/${workspaceStore.currentWorkspaceId}`);
    if (res.ok) {
      documents.value = await res.json();
    }
  } finally {
    isLoading.value = false;
  }
}

async function handleFileSelect(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) uploadFile(file);
}

async function handleDrop(event: DragEvent) {
  isDragging.value = false;
  const file = event.dataTransfer?.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file: File) {
  isUploading.value = true;
  uploadStatus.value = null;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`/api/documents/upload/${workspaceStore.currentWorkspaceId}`, {
      method: 'POST',
      body: formData
    });

    if (res.ok) {
      uploadStatus.value = { type: 'success', text: 'Upload successful! Processing started.' };
      fetchDocuments();
    } else {
      throw new Error('Upload failed');
    }
  } catch (err) {
    uploadStatus.value = { type: 'error', text: 'Error uploading file.' };
  } finally {
    isUploading.value = false;
  }
}

function formatSize(bytes: number) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString();
}
</script>

<style scoped>
.upload-zone {
  border: 2px border-dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.02);
}

.upload-zone:hover, .upload-zone.dragging {
  border-color: var(--color-primary);
  background: rgba(99, 102, 241, 0.05);
}

.upload-zone.processing {
  cursor: wait;
  opacity: 0.7;
}

.status-msg {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
}

.status-msg.success { background: rgba(16, 185, 129, 0.1); color: var(--color-success); }
.status-msg.error { background: rgba(239, 68, 68, 0.1); color: var(--color-error); }

.doc-table {
  width: 100%;
  border-collapse: collapse;
}

.doc-table th {
  text-align: left;
  padding: 12px;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  border-bottom: 1px solid var(--color-border);
}

.doc-table td {
  padding: 12px;
  font-size: 0.9rem;
  border-bottom: 1px solid var(--color-border);
}

.badge {
  background: var(--color-bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  text-transform: uppercase;
}

.status-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.status-badge.processing { background: rgba(245, 158, 11, 0.1); color: var(--color-warning); }
.status-badge.completed { background: rgba(16, 185, 129, 0.1); color: var(--color-success); }
.status-badge.error { background: rgba(239, 68, 68, 0.1); color: var(--color-error); }

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
