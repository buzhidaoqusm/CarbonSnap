<template>
  <AppLayout
    :is-authenticated="isAuthenticated"
    :avatar-url="avatarUrl"
    :avatar-alt="avatarAlt"
    :avatar-href="avatarHref"
    :user="user"
    :show-sidebar="false"
    :show-footer="false"
  >
    <slot />
  </AppLayout>
</template>

<script setup>
import AppLayout from "./AppLayout.vue";

defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  avatarUrl: {
    type: String,
    default: "",
  },
  avatarAlt: {
    type: String,
    default: "User avatar",
  },
  avatarHref: {
    type: String,
    default: "/profile",
  },
  user: {
    type: Object,
    default: null,
  },
});
</script>
