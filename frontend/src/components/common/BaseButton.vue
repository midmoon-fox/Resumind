<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost';
    size?: 'normal' | 'small';
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
    loading?: boolean;
  }>(),
  { variant: 'primary', size: 'normal', type: 'button', disabled: false, loading: false },
);
</script>

<template>
  <ElButton
    :native-type="type"
    :type="variant === 'primary' ? 'primary' : undefined"
    :text="variant === 'ghost'"
    :size="size === 'small' ? 'small' : 'default'"
    :disabled="disabled"
    :loading="loading"
    :aria-busy="loading || undefined"
    class="base-button"
    :class="[`button-${variant}`, `button-${size}`]"
  >
    <span class="button-hover-dot" aria-hidden="true" />
    <span class="button-content">
      <slot />
    </span>
    <svg class="button-hover-arrow" aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 12h14m-6-6 6 6-6 6"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </ElButton>
</template>

<style>
/* Preserve the slot's direction icon instead of adding a second hover arrow. */
.base-button:has(.button-content svg:is([class*='arrow-'], [class*='chevron-']))
  .button-hover-arrow {
  display: none;
}
</style>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.base-button {
  min-width: 0;
  --color-accent: #4f9cf9;
  --color-accent-ink: #ffffff;
}
</style>

<style scoped>
.base-button:not(.button-ghost)::after {
  content: '';
  opacity: 1;
  transform: none;
  animation: none !important;
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: var(--color-accent);
  border-radius: inherit;
  clip-path: circle(0 at 19px 50%);
  transition: clip-path 440ms cubic-bezier(0.22, 1, 0.36, 1);
}
.base-button:not(.button-ghost):not(:disabled):is(:hover, :focus-visible)::after {
  clip-path: circle(150% at 19px 50%);
}
.base-button:not(.button-ghost) .button-hover-dot {
  transform: none !important;
  transition: opacity 0.2s;
}
.base-button:not(.button-ghost):not(:disabled):is(:hover, :focus-visible) .button-hover-dot {
  opacity: 0;
}
.base-button:not(.button-ghost):not(:disabled):focus-visible {
  color: var(--color-accent-ink);
}
@media (prefers-reduced-motion: reduce) {
  .base-button:not(.button-ghost)::after {
    transition: none;
  }
}
</style>

<style scoped>
.base-button:not(.button-ghost) {
  color: var(--color-ink, #292337);
  background: var(--color-paper, #fff);
}
.base-button:not(.button-ghost) .button-content {
  animation: none !important;
  opacity: 1 !important;
}
.base-button:not(.button-ghost):not(:disabled):is(:hover, :focus-visible) {
  color: var(--color-accent-ink, #fff);
}
.base-button:not(.button-ghost):focus:not(:focus-visible):not(:hover) {
  color: var(--color-ink, #292337);
}
.base-button:not(.button-ghost):not(:disabled):focus-visible .button-hover-arrow {
  opacity: 1;
  transform: translateX(0);
}
</style>
