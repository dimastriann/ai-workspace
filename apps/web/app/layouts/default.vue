<template>
  <div class="app-layout">
    <AppHeader />
    <div class="app-body">
      <AppSidebar />
      <main class="app-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Default Layout
 *
 * Provides the global app shell with header, sidebar, and main content area.
 * All pages use this layout unless they specify a different one.
 */
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  padding-top: var(--header-height);
}

.app-main {
  flex: 1;
  padding: 24px;
  margin-left: var(--sidebar-width);
  overflow-y: auto;
  transition: margin-left var(--transition-normal);
}

@media (max-width: 768px) {
  .app-main {
    margin-left: 0;
    padding: 16px;
  }
}
</style>
