<template>
  <div class="page-container fade-in">
    <header class="page-header mb-6">
      <h1 class="text-3xl font-bold">Autonomous Agents</h1>
      <p class="text-secondary mt-2">Run agents to automate complex multi-step tasks.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <BaseCard class="lg:col-span-1">
        <template #header>New Task</template>
        <div class="flex flex-col gap-4">
          <textarea 
            placeholder="Describe the task for the agent..." 
            class="bg-tertiary border border-border rounded-md px-4 py-2 focus:ring-2 focus:ring-primary outline-none min-h-[120px]"
          ></textarea>
          <BaseButton>Execute Agent</BaseButton>
        </div>
      </BaseCard>

      <BaseCard class="lg:col-span-2">
        <template #header>Execution History</template>
        <div class="flex items-center justify-center h-48 text-secondary">
          No task history available.
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
/* Agents page stub */
</script>

<style scoped>
.bg-tertiary {
  background-color: var(--color-bg-tertiary);
}
.text-secondary {
  color: var(--color-text-secondary);
}
.border-border {
  border-color: var(--color-border);
}
</style>
