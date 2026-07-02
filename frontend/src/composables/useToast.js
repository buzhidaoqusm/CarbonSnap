import { ref } from "vue";

const DEFAULT_AUTO_DISMISS_MS = 2000;
const MAX_VISIBLE_TOASTS = 5;

export const toasts = ref([]);
const toastTimers = new Map();
let toastIdCounter = 0;

function normalizeToast(input) {
  toastIdCounter += 1;
  const now = new Date().toISOString();
  return {
    id: input.id ?? `toast-${Date.now()}-${toastIdCounter}`,
    kind: input.kind || "general",
    type: input.type || "info",
    title: input.title || "Update",
    body: input.body || "",
    icon: input.icon || "",
    created_at: input.created_at || now,
    autoDismissMs: input.autoDismissMs ?? DEFAULT_AUTO_DISMISS_MS,
    source_url: input.source_url || "",
    notification: input.notification || null,
    event_type: input.event_type || "",
  };
}

function normalizeToastId(toastOrId) {
  if (toastOrId && typeof toastOrId === "object") {
    return toastOrId.id ?? null;
  }
  return toastOrId ?? null;
}

function clearToastTimer(toastId) {
  const id = normalizeToastId(toastId);
  if (id === null || id === undefined) {
    return;
  }

  const timerId = toastTimers.get(String(id));
  if (timerId !== undefined) {
    window.clearTimeout(timerId);
    toastTimers.delete(String(id));
  }
}

function scheduleAutoDismiss(toast) {
  if (!toast.autoDismissMs || toast.autoDismissMs <= 0) {
    return;
  }

  clearToastTimer(toast.id);
  const timerId = window.setTimeout(() => {
    dismissToast(toast.id);
  }, toast.autoDismissMs);
  toastTimers.set(String(toast.id), timerId);
}

export function showToast(input) {
  const toast = normalizeToast(input);
  const existingIndex = toasts.value.findIndex((item) => String(item.id) === String(toast.id));

  if (existingIndex >= 0) {
    clearToastTimer(toast.id);
    toasts.value = [
      toast,
      ...toasts.value.filter((item) => String(item.id) !== String(toast.id)),
    ].slice(0, MAX_VISIBLE_TOASTS);
  } else {
    toasts.value = [toast, ...toasts.value].slice(0, MAX_VISIBLE_TOASTS);
  }

  scheduleAutoDismiss(toast);
  return toast.id;
}

export function showSuccessToast(title, body = "") {
  return showToast({ type: "success", title, body, icon: "check_circle" });
}

export function showErrorToast(title, body = "") {
  return showToast({ type: "error", title, body, icon: "error" });
}

export function dismissToast(toastId) {
  const id = normalizeToastId(toastId);
  if (id === null || id === undefined) {
    return;
  }

  clearToastTimer(id);
  toasts.value = toasts.value.filter((item) => String(item.id) !== String(id));
}

export function dismissToastsByKind(kind) {
  const toastsToDismiss = toasts.value.filter((item) => item.kind === kind);
  toastsToDismiss.forEach((toast) => clearToastTimer(toast.id));
  toasts.value = toasts.value.filter((item) => item.kind !== kind);
}

export function clearAllToasts() {
  for (const timerId of toastTimers.values()) {
    window.clearTimeout(timerId);
  }
  toastTimers.clear();
  toasts.value = [];
}

export function useToast() {
  return {
    toasts,
    showToast,
    showSuccessToast,
    showErrorToast,
    dismissToast,
    dismissToastsByKind,
    clearAllToasts,
  };
}
