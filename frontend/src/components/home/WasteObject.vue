<template>
  <div class="waste-object" :class="item.objectClass" :data-waste-object="item.id" aria-hidden="true">
    <img :src="item.asset" :alt="item.name" draggable="false" />
  </div>
</template>

<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
});
</script>
