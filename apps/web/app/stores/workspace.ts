import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<any[]>([])
  const currentWorkspaceId = ref<string | null>(null)
  const isLoading = ref(false)

  const currentWorkspace = computed(() => 
    workspaces.value.find(ws => ws.id === currentWorkspaceId.value) || null
  )

  async function fetchWorkspaces() {
    isLoading.value = true
    try {
      const { data } = await useFetch('/api/workspaces')
      if (data.value) {
        workspaces.value = data.value as any[]
        // Auto-select first workspace if none selected
        if (!currentWorkspaceId.value && workspaces.value.length > 0) {
          currentWorkspaceId.value = workspaces.value[0].id
        }
      }
    } finally {
      isLoading.value = false
    }
  }

  async function createWorkspace(name: string, description: string = '') {
    try {
      const { data, error } = await useFetch('/api/workspaces', {
        method: 'POST',
        body: { name, description }
      })
      if (data.value) {
        await fetchWorkspaces()
        currentWorkspaceId.value = (data.value as any).id
      }
    } catch (err) {
      console.error('Failed to create workspace', err)
    }
  }

  function setWorkspace(id: string) {
    currentWorkspaceId.value = id
  }

  return {
    workspaces,
    currentWorkspaceId,
    currentWorkspace,
    isLoading,
    fetchWorkspaces,
    createWorkspace,
    setWorkspace
  }
})
