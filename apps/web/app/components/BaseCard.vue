<template>
  <div :class="['base-card', { hoverable }]">
    <div v-if="$slots.header" class="card-header">
      <slot name="header" />
    </div>
    <div class="card-body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * BaseCard Component
 *
 * Versatile card container with optional header/footer slots
 * and hover animation support.
 */

interface Props {
  hoverable?: boolean;
}

withDefaults(defineProps<Props>(), {
  hoverable: false,
});
</script>

<style scoped>
.base-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.base-card.hoverable:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.card-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}
</style>
