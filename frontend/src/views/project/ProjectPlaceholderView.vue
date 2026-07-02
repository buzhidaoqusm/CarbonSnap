<template>
  <div class="project-view min-h-screen bg-surface font-body text-on-surface">
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-href="avatarHref"
      :avatar-url="avatarUrl"
      :points-label="pointsLabel"
    />

    <div class="flex min-h-screen pt-6">
      <main class="mx-auto flex-1 max-w-6xl space-y-12 p-6 md:p-10" data-project-main>
        <section class="space-y-4" data-project-header>
          <div class="flex items-end justify-between gap-6">
            <div>
              <h1 class="font-headline text-4xl font-black tracking-tight text-on-surface md:text-5xl">Community Projects</h1>
              <p class="mt-2 max-w-lg text-on-surface-variant">Direct your carbon credits to verified hyper-local initiatives. Track growth in real-time through decentralized proof-of-impact.</p>
            </div>
            <div class="hidden gap-4 lg:flex">
              <div class="rounded-2xl bg-surface-container-high px-6 py-4 text-center">
                <p class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Global Offset</p>
                <p class="font-headline text-2xl font-bold text-primary">12.4M Tons</p>
              </div>
            </div>
          </div>
        </section>

        <section class="grid grid-cols-1 gap-6 md:grid-cols-12" data-project-grid>
          <div class="group relative overflow-hidden rounded-[2.5rem] border border-outline-variant/10 bg-surface-container-lowest shadow-[0_8px_32px_rgba(43,48,47,0.04)] md:col-span-8" data-project-featured>
            <div class="aspect-[16/9] w-full overflow-hidden">
              <img class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" alt="vast field of young tree saplings stretching toward the horizon under a soft morning mist and rising sun" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCynoS-M5HSFII9jdOnvDNV07olcoj2HjRWer0kO_9O0IadKyVujlRDZvAb-_wJQnl51qlmdbuORl-CXwpczbzR5PSASPlh18_RgRlHIIeXZx98_ye7WS7ZLXZ04supixr14qmMGHt7mmZuK7jGgWByMo5-GDWqkBr699TZGkXIfur1ty3nDx6e3vQIo_x6T9J7Uf-7oxkxYLCdekze2ptvmvlKAjrNIj4AfqVNMEX0PqLrvRWIuVN2OU46BRov5CBeS7o02Bkk1dta" />
            </div>
            <div class="space-y-6 p-8">
              <div class="flex items-start justify-between">
                <div>
                  <span class="rounded-full bg-primary-container px-3 py-1 text-[10px] font-bold uppercase tracking-tighter text-on-primary-container">Active Priority</span>
                  <h2 class="mt-3 font-headline text-3xl font-bold text-on-surface">Local Reforestation: Amazon Edge</h2>
                </div>
                <div class="flex flex-col items-end">
                  <span class="font-headline text-2xl font-bold text-secondary">82%</span>
                  <span class="text-[10px] font-bold uppercase text-on-surface-variant">Funded</span>
                </div>
              </div>
              <div class="space-y-2">
                <div class="h-3 w-full overflow-hidden rounded-full bg-surface-container">
                  <div class="h-full w-[82%] rounded-full bg-primary shadow-[0_0_12px_rgba(38,104,41,0.3)]" />
                </div>
                <div class="flex justify-between text-xs font-bold text-on-surface-variant">
                  <span>Goal: 50,000 Trees</span>
                  <span>41,200/50,000 Planted</span>
                </div>
              </div>
              <div class="grid grid-cols-3 gap-4 border-y border-outline-variant/10 py-4">
                <div>
                  <p class="mb-1 text-[10px] uppercase tracking-widest text-on-surface-variant">Participants</p>
                  <p class="font-headline text-lg font-bold">12,450</p>
                </div>
                <div>
                  <p class="mb-1 text-[10px] uppercase tracking-widest text-on-surface-variant">Credits Target</p>
                  <p class="font-headline text-lg font-bold">850k CO2</p>
                </div>
                <div>
                  <p class="mb-1 text-[10px] uppercase tracking-widest text-on-surface-variant">My Status</p>
                  <p class="font-headline text-lg font-bold text-secondary">Active</p>
                </div>
              </div>
              <div class="flex gap-4">
                <button type="button" class="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-secondary-fixed py-4 font-headline font-bold text-on-secondary-fixed transition-all hover:opacity-90" data-project-contribute-button>
                  <span class="material-symbols-outlined" data-icon="payments">payments</span>
                  Contribute Carbon Credits
                </button>
                <button type="button" class="rounded-2xl bg-surface-container px-6 py-4 text-on-surface-variant transition-colors hover:bg-surface-container-high" data-project-share-button>
                  <span class="material-symbols-outlined" data-icon="share">share</span>
                </button>
              </div>
            </div>
          </div>

          <div class="flex flex-col justify-between rounded-[2.5rem] border border-outline-variant/10 bg-surface-container-low p-8 md:col-span-4" data-project-secondary>
            <div>
              <span class="rounded-full bg-tertiary-container px-3 py-1 text-[10px] font-bold uppercase tracking-tighter text-on-tertiary-container">Ocean Health</span>
              <h3 class="mt-4 font-headline text-2xl font-bold leading-tight text-on-surface">Ocean Plastic Cleanup: Great Pacific</h3>
              <p class="mt-4 text-sm text-on-surface-variant">Removing micro-plastics using autonomous drone swarms. Powered by community validation.</p>
            </div>
            <div class="mt-8 space-y-6">
              <div class="relative mx-auto h-32 w-32">
                <svg class="h-full w-full -rotate-90 transform">
                  <circle class="text-surface-variant" cx="64" cy="64" fill="transparent" r="58" stroke="currentColor" stroke-width="8" />
                  <circle class="text-tertiary" cx="64" cy="64" fill="transparent" r="58" stroke="currentColor" stroke-dasharray="364.4" stroke-dashoffset="145.7" stroke-width="8" />
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span class="font-headline text-2xl font-bold text-tertiary">60%</span>
                  <span class="text-[8px] font-bold uppercase tracking-widest text-on-surface-variant">Goal Reach</span>
                </div>
              </div>
              <div class="space-y-2">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-on-surface-variant">Total Collected</span>
                  <span class="font-bold">4.2 Tons</span>
                </div>
                <div class="flex items-center justify-between text-xs">
                  <span class="text-on-surface-variant">My Contribution</span>
                  <span class="font-bold text-tertiary">120kg</span>
                </div>
              </div>
              <button type="button" class="w-full rounded-2xl bg-tertiary py-4 font-headline font-bold text-on-tertiary transition-all hover:opacity-90" data-project-join-button>
                Join Project
              </button>
            </div>
          </div>

          <div class="rounded-[2.5rem] border border-outline-variant/10 bg-surface-container-lowest p-8 md:col-span-5" data-project-timeline>
            <div class="mb-8 flex items-center justify-between">
              <h3 class="font-headline text-xl font-bold">Project Updates</h3>
              <span class="material-symbols-outlined text-on-surface-variant">history</span>
            </div>
            <div class="relative space-y-8">
              <div class="absolute bottom-2 top-2 left-[11px] w-px bg-outline-variant/20" />
              <div class="relative pl-8">
                <div class="absolute left-0 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-secondary-fixed ring-4 ring-surface-container-lowest">
                  <span class="material-symbols-outlined text-[14px] font-bold" data-icon="check">check</span>
                </div>
                <p class="mb-1 text-[10px] font-bold uppercase text-on-surface-variant">2 hours ago</p>
                <h4 class="text-sm font-bold text-on-surface">Drone swarm #4 launched</h4>
                <p class="mt-1 text-xs text-on-surface-variant">Satellite confirmation of 400kg plastic collection in Sector 4B.</p>
              </div>
              <div class="relative pl-8 opacity-60">
                <div class="absolute left-0 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-surface-container ring-4 ring-surface-container-lowest">
                  <span class="material-symbols-outlined text-[14px]" data-icon="schedule">schedule</span>
                </div>
                <p class="mb-1 text-[10px] font-bold uppercase text-on-surface-variant">YESTERDAY</p>
                <h4 class="text-sm font-bold text-on-surface">Milestone: 10,000th Contributor</h4>
                <p class="mt-1 text-xs text-on-surface-variant">Community growth target reached 1 month ahead of schedule.</p>
              </div>
              <div class="relative pl-8 opacity-60">
                <div class="absolute left-0 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-surface-container ring-4 ring-surface-container-lowest">
                  <span class="material-symbols-outlined text-[14px]" data-icon="schedule">schedule</span>
                </div>
                <p class="mb-1 text-[10px] font-bold uppercase text-on-surface-variant">Oct 12, 2023</p>
                <h4 class="text-sm font-bold text-on-surface">Phase 2: Reforestation expansion</h4>
                <p class="mt-1 text-xs text-on-surface-variant">Secured rights for an additional 400 hectares of buffer zone.</p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-6 md:col-span-7 sm:grid-cols-2">
            <div class="flex flex-col justify-between rounded-[2.5rem] bg-primary p-8 text-on-primary">
              <div>
                <span class="material-symbols-outlined text-4xl" data-icon="eco">eco</span>
                <h3 class="mt-4 font-headline text-2xl font-bold">Verified Impact</h3>
                <p class="mt-2 text-sm text-on-primary/70">All contributions are locked in the blockchain and verified via multisig environmental sensors.</p>
              </div>
              <div class="mt-8 flex items-end justify-between">
                <span class="font-headline text-4xl font-black">99.9%</span>
                <span class="text-xs uppercase font-bold tracking-widest opacity-60">Transparency Rating</span>
              </div>
            </div>
            <div class="rounded-[2.5rem] border border-outline-variant/10 bg-surface-container p-8">
              <div class="flex items-start justify-between">
                <h3 class="font-headline text-xl font-bold text-on-surface">Upcoming Projects</h3>
                <button type="button" class="rounded-full bg-surface-container-lowest p-2" data-project-upcoming-arrow>
                  <span class="material-symbols-outlined text-primary" data-icon="arrow_forward">arrow_forward</span>
                </button>
              </div>
              <div class="mt-6 space-y-4">
                <div class="flex items-center gap-4 rounded-2xl bg-surface-container-lowest p-3">
                  <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary-container text-on-secondary-container">
                    <span class="material-symbols-outlined">wind_power</span>
                  </div>
                  <div>
                    <p class="text-sm font-bold">Offshore Wind #12</p>
                    <p class="text-[10px] font-bold uppercase text-on-surface-variant">Opens in 2 days</p>
                  </div>
                </div>
                <div class="flex items-center gap-4 rounded-2xl bg-surface-container-lowest p-3">
                  <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-tertiary-container text-on-tertiary-container">
                    <span class="material-symbols-outlined">solar_power</span>
                  </div>
                  <div>
                    <p class="text-sm font-bold">Urban Solar Grid</p>
                    <p class="text-[10px] font-bold uppercase text-on-surface-variant">Funding Stage</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <nav class="fixed bottom-0 left-0 z-50 flex w-full items-end justify-around rounded-t-3xl bg-surface/80 px-4 pb-4 shadow-[0_-4px_20px_rgba(0,0,0,0.04)] backdrop-blur-lg md:hidden" data-project-bottom-nav>
      <RouterLink class="flex flex-col items-center justify-center p-2 text-on-surface-variant" to="/ledger" data-project-bottom-ledger-link>
        <span class="material-symbols-outlined" data-icon="receipt_long">receipt_long</span>
        <span class="mt-1 font-body text-[10px] font-bold uppercase tracking-widest">Ledger</span>
      </RouterLink>
      <RouterLink class="mb-2 flex scale-110 flex-col items-center justify-center rounded-full bg-secondary-fixed p-3 text-on-secondary-fixed shadow-lg" to="/project" data-project-bottom-project-link>
        <span class="material-symbols-outlined" data-icon="assignment">assignment</span>
        <span class="hidden">Projects</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center p-2 text-on-surface-variant" to="/ai" data-project-bottom-ai-link>
        <span class="material-symbols-outlined" data-icon="photo_camera">photo_camera</span>
        <span class="mt-1 font-body text-[10px] font-bold uppercase tracking-widest">Snap</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center p-2 text-on-surface-variant" to="/forum" data-project-bottom-forum-link>
        <span class="material-symbols-outlined" data-icon="groups">groups</span>
        <span class="mt-1 font-body text-[10px] font-bold uppercase tracking-widest">Forum</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center p-2 text-on-surface-variant" to="/market" data-project-bottom-market-link>
        <span class="material-symbols-outlined" data-icon="storefront">storefront</span>
        <span class="mt-1 font-body text-[10px] font-bold uppercase tracking-widest">Market</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import AppHeader from "../../components/common/AppHeader.vue";
import { useAuth } from "../../composables/useAuth.js";

const { isLoggedIn, user } = useAuth();
const avatarAlt = computed(() => user.value?.username || "Profile");
const avatarHref = computed(() => (isLoggedIn.value ? "/profile" : "/login"));
const avatarUrl = computed(() => user.value?.avatar_url || "");
const pointsLabel = computed(() => `${Number(user.value?.current_points ?? 0).toLocaleString("en-US")} pts`);
</script>

<style src="../../styles/views/project-view.css"></style>
