<template>
  <button
    :class="['base-button', `variant-${variant}`, `size-${size}`]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="spinner" />
    <slot />
  </button>
</template>

<script setup lang="ts">
/**
 * BaseButton Component
 *
 * Reusable button with multiple variants, sizes, and loading state.
 */

interface Props {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
}

withDefaults(defineProps<Props>(), {
  variant: "primary",
  size: "md",
  disabled: false,
  loading: false,
});

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: var(--radius-md);
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.base-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sizes */
.size-sm { padding: 6px 12px; font-size: 0.8rem; }
.size-md { padding: 10px 20px; font-size: 0.875rem; }
.size-lg { padding: 12px 28px; font-size: 1rem; }

/* Variants */
.variant-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  box-shadow: var(--shadow-sm);
}
.variant-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.variant-secondary {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}
.variant-secondary:hover:not(:disabled) {
  background: var(--color-border);
  border-color: var(--color-border-light);
}

.variant-ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.variant-ghost:hover:not(:disabled) {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.variant-danger {
  background: var(--color-error);
  color: white;
}
.variant-danger:hover:not(:disabled) {
  background: #dc2626;
  transform: translateY(-1px);
}

/* Loading spinner */
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
