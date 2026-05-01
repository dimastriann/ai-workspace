<template>
  <header class="app-header glass">
    <div class="header-left">
      <NuxtLink to="/" class="logo">
        <span class="logo-icon">🧠</span>
        <span class="logo-text gradient-text">AI Workspace</span>
      </NuxtLink>
    </div>

    <div class="header-center">
      <div class="search-bar">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          type="text"
          placeholder="Search workspace..."
          class="search-input"
        />
      </div>
    </div>

    <div class="header-right">
      <div class="status-indicator">
        <span class="status-dot pulse-dot" />
        <span class="status-text">Connected</span>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * AppHeader Component
 *
 * Global navigation header with logo, search bar, and status indicator.
 */
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  font-weight: 700;
  font-size: 1.2rem;
}

.logo-icon {
  font-size: 1.5rem;
}

.header-center {
  flex: 1;
  max-width: 480px;
  margin: 0 24px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  padding: 8px 16px;
  transition: border-color var(--transition-fast);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.search-icon {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.search-input {
  background: transparent;
  border: none;
  outline: none;
  color: var(--color-text-primary);
  font-size: 0.875rem;
  width: 100%;
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.header-right {
  display: flex;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}
</style>
