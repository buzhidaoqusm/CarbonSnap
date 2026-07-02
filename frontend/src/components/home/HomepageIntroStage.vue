<script setup>
defineProps({
  playbackComplete: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["advance"]);
</script>

<template>
  <section class="home-stage intro-stage" data-home-stage="intro">
    <div class="intro-stage__atmosphere" aria-hidden="true">
      <span class="intro-stage__leaf intro-stage__leaf--one"></span>
      <span class="intro-stage__leaf intro-stage__leaf--two"></span>
      <span class="intro-stage__leaf intro-stage__leaf--three"></span>
    </div>
    <div class="home-stage__inner intro-stage__inner">
      <div class="intro-stage__visual">
        <span class="intro-stage__glow" aria-hidden="true"></span>
        <div class="intro-stage__frame">
          <div class="intro-stage__artboard" aria-hidden="true">
            <div class="intro-stage__sequence" data-intro-sequence>
              <span class="intro-stage__sequence-glow"></span>

              <div
                class="intro-stage__phase intro-stage__phase--sorting is-active"
                data-intro-phase="sorting"
              >
                <div class="intro-stage__object-card">
                  <span class="intro-stage__scan-frame"></span>
                  <span class="intro-stage__scan-line"></span>
                  <span class="intro-stage__recyclable-object"></span>
                  <span class="intro-stage__object-tag intro-stage__object-tag--material">
                    plastic
                  </span>
                  <span class="intro-stage__object-tag intro-stage__object-tag--status">
                    recyclable
                  </span>
                </div>
              </div>

              <div class="intro-stage__phase intro-stage__phase--map" data-intro-phase="map">
                <div class="intro-stage__map-card">
                  <span class="intro-stage__map-grid"></span>
                  <span class="intro-stage__map-pin intro-stage__map-pin--user"></span>
                  <span class="intro-stage__map-pin intro-stage__map-pin--target"></span>
                  <svg class="intro-stage__route" viewBox="0 0 240 140" aria-hidden="true">
                    <path
                      data-intro-route
                      d="M36 102 C78 84, 104 50, 148 60 S200 88, 204 42"
                    />
                  </svg>
                </div>
              </div>

              <div class="intro-stage__phase intro-stage__phase--score" data-intro-phase="score">
                <div class="intro-stage__score-card">
                  <div class="intro-stage__score-ring">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                      <circle
                        class="intro-stage__score-ring-track"
                        cx="60"
                        cy="60"
                        r="44"
                      />
                      <circle
                        class="intro-stage__score-ring-progress"
                        cx="60"
                        cy="60"
                        r="44"
                        data-intro-score-ring
                      />
                    </svg>
                    <span class="intro-stage__score-carbon" data-intro-carbon>-1.8 kg</span>
                  </div>
                  <div class="intro-stage__score-metrics">
                    <strong class="intro-stage__score-points" data-intro-points>+24 pts</strong>
                    <span class="intro-stage__score-caption">low-carbon progress</span>
                  </div>
                </div>
              </div>

              <div class="intro-stage__phase-labels" data-intro-phase-labels>
                <span data-intro-phase-label="sorting">AI SORTING</span>
                <span data-intro-phase-label="map">RECYCLE MAP</span>
                <span data-intro-phase-label="score">CARBON SCORE</span>
              </div>
            </div>
          </div>
        </div>
        <p class="intro-stage__microcopy" data-animate="intro">
          A short product story in motion
        </p>
      </div>

      <div class="intro-stage__copy">
        <p class="intro-stage__eyebrow" data-animate="intro">Why CarbonSnap</p>
        <h1 class="intro-stage__title" data-animate="intro">
          Reduce waste.
          <br />
          Reveal impact.
        </h1>
        <p class="intro-stage__body" data-animate="intro">
          CarbonSnap was built to make low-carbon action easier to understand,
          easier to continue, and more rewarding in everyday life.
        </p>

        <div class="intro-stage__story-window" data-animate="intro" data-intro-story-window>
          <div class="intro-stage__story-track" data-intro-story-track>
            <div class="intro-stage__lines" aria-hidden="true">
              <span class="intro-stage__line"></span>
              <span class="intro-stage__line"></span>
              <span class="intro-stage__line"></span>
            </div>

            <div class="intro-stage__story-paragraphs">
              <p class="intro-stage__story-paragraph">
                Many people want to recycle better, but they do not always know how
                to sort waste correctly, where to take special items, or how much
                impact their actions really create.
              </p>
              <p class="intro-stage__story-paragraph">
                CarbonSnap turns that uncertainty into clear guidance, nearby support,
                and measurable progress that users can see and continue building on.
              </p>
              <p class="intro-stage__story-paragraph">
                The platform combines intelligent assistance, practical recycling tools,
                and motivation systems so sustainable habits feel easier to start and
                easier to maintain.
              </p>
            </div>

            <div class="intro-stage__metrics">
              <article class="intro-stage__metric">
                <strong class="intro-stage__metric-value">AI</strong>
                <span class="intro-stage__metric-label">Upload a photo and receive waste classification, recycling suggestions, and practical next steps.</span>
              </article>
              <article class="intro-stage__metric">
                <strong class="intro-stage__metric-value">MAP</strong>
                <span class="intro-stage__metric-label">Find nearby recycling points and better disposal options based on the waste you need to handle.</span>
              </article>
              <article class="intro-stage__metric">
                <strong class="intro-stage__metric-value">CO2</strong>
                <span class="intro-stage__metric-label">Track carbon-related actions, earn points, explore forum knowledge, and stay engaged through visible progress.</span>
              </article>
            </div>
          </div>
        </div>

        <p
          class="intro-stage__unlock-hint"
          :class="{ 'intro-stage__unlock-hint--visible': playbackComplete }"
        >
          The story is complete.
        </p>

        <button
          class="intro-stage__arrow"
          :class="{ 'intro-stage__arrow--visible': playbackComplete }"
          type="button"
          :disabled="!playbackComplete"
          @click="$emit('advance')"
        >
          <svg
            class="intro-stage__arrow-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M12 5v14" />
            <path d="m6 13 6 6 6-6" />
          </svg>
        </button>
      </div>
    </div>
  </section>
</template>
