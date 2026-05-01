<template>
  <div class="page-container fade-in">
    <header class="page-header">
      <h1 class="text-3xl font-bold">Dashboard</h1>
      <p class="text-secondary mt-2">Welcome to your AI Workspace. Here is an overview of your active projects.</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
      <BaseCard hoverable>
        <template #header>Active Chats</template>
        <div class="text-4xl font-bold gradient-text">0</div>
        <template #footer>
          <BaseButton variant="ghost" size="sm" @click="navigateTo('/chat')">View Chats</BaseButton>
        </template>
      </BaseCard>

      <BaseCard hoverable>
        <template #header>Documents</template>
        <div class="text-4xl font-bold gradient-text">0</div>
        <template #footer>
          <BaseButton variant="ghost" size="sm" @click="navigateTo('/documents')">Manage Docs</BaseButton>
        </template>
      </BaseCard>

      <BaseCard hoverable>
        <template #header>Agent Tasks</template>
        <div class="text-4xl font-bold gradient-text">0</div>
        <template #footer>
          <BaseButton variant="ghost" size="sm" @click="navigateTo('/agents')">Run Task</BaseButton>
        </template>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
/* Dashboard page stub */
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
}
.text-secondary {
  color: var(--color-text-secondary);
}
</style>
