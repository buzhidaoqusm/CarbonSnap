<template>
  <div
    class="notification-toast-stack"
    aria-live="polite"
    aria-relevant="additions removals"
    data-notification-toast-stack
  >
    <TransitionGroup name="notification-toast" tag="div" class="notification-toast-stack__items">
      <article
        v-for="toast in toasts"
        :key="toast.id"
        class="notification-toast"
        :class="`notification-toast--${toastType(toast)}`"
        data-notification-toast
      >
        <button
          class="notification-toast__body"
          type="button"
          :data-notification-toast-open="toast.id"
          @click="$emit('open', toast)"
        >
          <span class="notification-toast__icon material-symbols-outlined" aria-hidden="true">
            {{ toastIcon(toast) }}
          </span>

          <span class="notification-toast__content">
            <span class="notification-toast__title">{{ toast.title || "Update" }}</span>
            <span v-if="toast.body" class="notification-toast__body-copy">{{ toast.body }}</span>
            <span class="notification-toast__meta">{{ formatRelativeTime(toast.created_at) }}</span>
          </span>
        </button>

        <button
          class="notification-toast__dismiss"
          type="button"
          :aria-label="`Dismiss ${toast.title || 'notification'}`"
          :data-notification-toast-dismiss="toast.id"
          @click="$emit('dismiss', toast.id)"
        >
          <span class="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
      </article>
    </TransitionGroup>
  </div>
</template>

<script setup>
defineProps({
  toasts: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["dismiss", "open"]);

function toastIcon(toast) {
  if (toast?.icon) {
    return toast.icon;
  }

  const type = toastType(toast);
  if (type === "success") {
    return "check_circle";
  }
  if (type === "error") {
    return "error";
  }
  if (type === "warning") {
    return "warning";
  }

  const eventType = String(toast?.event_type || "").toLowerCase();
  if (eventType.includes("project")) {
    return "forest";
  }
  if (eventType.includes("order") || eventType.includes("purchase")) {
    return "package_2";
  }
  if (eventType.includes("comment")) {
    return "forum";
  }
  if (eventType.includes("post")) {
    return "notifications_active";
  }
  return "notifications";
}

function toastType(toast) {
  const type = String(toast?.type || "").toLowerCase();
  return ["success", "error", "warning", "info"].includes(type) ? type : "info";
}

function formatRelativeTime(value) {
  const timestamp = Date.parse(value || "");
  if (Number.isNaN(timestamp)) {
    return "";
  }

  const diffMinutes = Math.round((Date.now() - timestamp) / 60000);
  if (diffMinutes < 1) {
    return "Just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}
</script>

<style scoped>
.notification-toast-stack {
  position: fixed;
  right: 18px;
  top: 96px;
  z-index: 110;
  pointer-events: none;
}

.notification-toast-stack__items {
  display: grid;
  gap: 10px;
  width: min(360px, calc(100vw - 24px));
}

.notification-toast {
  align-items: stretch;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  border: 1px solid rgba(170, 174, 172, 0.36);
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 248, 0.95)),
    radial-gradient(circle at top left, rgba(185, 246, 0, 0.15), transparent 40%);
  box-shadow: 0 18px 42px rgba(43, 48, 47, 0.12);
  pointer-events: auto;
  overflow: hidden;
}

.notification-toast__body {
  align-items: center;
  appearance: none;
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 12px;
  grid-template-columns: 44px minmax(0, 1fr);
  padding: 14px 14px 14px 16px;
  text-align: left;
}

.notification-toast__icon {
  align-items: center;
  background: var(--cs-primary);
  border-radius: 14px;
  color: #d1ffc8;
  display: inline-flex;
  height: 44px;
  justify-content: center;
  width: 44px;
}

.notification-toast--success .notification-toast__icon {
  background: #127e69;
  color: #eafff8;
}

.notification-toast--error .notification-toast__icon {
  background: #b31b25;
  color: #ffefee;
}

.notification-toast--warning .notification-toast__icon {
  background: #b45309;
  color: #fff7ed;
}

.notification-toast__content {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.notification-toast__title {
  color: var(--cs-text);
  font-weight: 800;
  line-height: 1.35;
}

.notification-toast__body-copy,
.notification-toast__meta {
  color: var(--cs-text-muted);
  font-size: 0.88rem;
  line-height: 1.45;
}

.notification-toast__body-copy {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.notification-toast__dismiss {
  align-self: flex-start;
  appearance: none;
  background: transparent;
  border: 0;
  color: var(--cs-text-muted);
  cursor: pointer;
  padding: 12px 12px 0 0;
}

.notification-toast__dismiss:hover,
.notification-toast__dismiss:focus-visible {
  color: var(--cs-primary);
  outline: none;
}

.notification-toast-enter-active,
.notification-toast-leave-active {
  transition: opacity 180ms ease, transform 220ms ease;
}

.notification-toast-enter-from,
.notification-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

@media (max-width: 640px) {
  .notification-toast-stack {
    left: 12px;
    right: 12px;
    top: 84px;
  }

  .notification-toast-stack__items {
    width: 100%;
  }
}
</style>
