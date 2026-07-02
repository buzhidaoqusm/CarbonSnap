<template>
  <section class="terms-page">
    <div class="terms-card">
      <RouterLink class="brand" to="/">CarbonSnap</RouterLink>
      <p class="card-eyebrow">Platform Terms</p>
      <h1>CarbonSnap Terms of Use</h1>
      <p class="card-copy">
        These terms explain how CarbonSnap accounts, AI guidance, community features, points, and uploaded content should be used.
      </p>

      <div class="terms-content">
        <section>
          <h2>1. Account Use</h2>
          <p>Create an account with accurate information and keep your sign-in credentials private. Activity under your account is your responsibility.</p>
        </section>
        <section>
          <h2>2. AI Recycling Guidance</h2>
          <p>AI responses are practical assistance, not a guarantee that every local recycling rule has been checked. Follow local disposal rules when they differ from CarbonSnap suggestions.</p>
        </section>
        <section>
          <h2>3. Points and Ledger</h2>
          <p>Carbon points represent in-app progress and rewards. They are not money, cannot be exchanged outside CarbonSnap, and may be adjusted if activity is fraudulent or duplicated.</p>
        </section>
        <section>
          <h2>4. Community Content</h2>
          <p>Posts, comments, project descriptions, and images should be lawful, respectful, and related to recycling or sustainability. CarbonSnap may remove harmful or irrelevant content.</p>
        </section>
        <section>
          <h2>5. Uploaded Images</h2>
          <p>Only upload images you have the right to share. Avoid sensitive personal information in photos used for AI chat, audit, forum, market, or project features.</p>
        </section>
        <section>
          <h2>6. Privacy</h2>
          <p>Profile details, uploaded assets, AI history, and ledger activity are used to operate CarbonSnap features. Do not use the platform for confidential or regulated data.</p>
        </section>
      </div>

      <div class="terms-actions">
        <RouterLink class="primary" to="/register">Back to Register</RouterLink>
        <RouterLink class="secondary" to="/login">Sign In</RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped src="../../styles/views/auth-view.css"></style>
