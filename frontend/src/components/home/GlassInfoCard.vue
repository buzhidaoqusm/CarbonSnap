<template>
  <article class="glass-info-card" :class="item.cardClass" :data-impact-card="item.id">
    <p class="glass-info-card__eyebrow">{{ item.material }}</p>
    <h3>{{ item.name }}</h3>
    <div class="glass-info-card__value">{{ item.cardValue }}</div>
    <p class="glass-info-card__meta">{{ item.points }} carbon reward</p>
  </article>
</template>

<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
});
</script>
