<template>
  <section class="auth-page">
    <div class="auth-hero">
      <RouterLink class="brand" to="/">CarbonSnap</RouterLink>
      <p class="eyebrow">{{ isRegisterMode ? t("auth.newMemberAccess") : t("auth.accountAccess") }}</p>
      <h1>{{ isRegisterMode ? t("auth.heroTitleRegister") : t("auth.heroTitleLogin") }}</h1>
      <p class="hero-copy">
        {{ isRegisterMode ? t("auth.heroCopyRegister") : t("auth.heroCopyLogin") }}
      </p>

      <div class="stage" :class="{ 'stage--celebrate': isCelebrating, 'stage--peek': password.length > 0 && showPassword, 'stage--failing': isFailing }" aria-hidden="true">
        <div ref="leafRef" class="actor actor--leaf" :style="leafStyle">
          <div class="eyes" :style="leafEyesStyle">
            <div class="eye" :style="eyeStyle(isPurpleBlinking)"><div class="pupil" :style="leafPupilStyle"></div></div>
            <div class="eye" :style="eyeStyle(isPurpleBlinking)"><div class="pupil" :style="leafPupilStyle"></div></div>
          </div>
        </div>
        <div ref="botRef" class="actor actor--bot" :style="botStyle">
          <div class="eyes" :style="botEyesStyle">
            <div class="eye eye--sm" :style="eyeStyle(isBlackBlinking, true)"><div class="pupil pupil--sm" :style="botPupilStyle"></div></div>
            <div class="eye eye--sm" :style="eyeStyle(isBlackBlinking, true)"><div class="pupil pupil--sm" :style="botPupilStyle"></div></div>
          </div>
        </div>
        <div ref="stoneRef" class="actor actor--stone" :style="stoneStyle">
          <div class="dots" :style="stoneEyesStyle"><div class="dot" :style="stonePupilStyle"></div><div class="dot" :style="stonePupilStyle"></div></div>
        </div>
        <div ref="sproutRef" class="actor actor--sprout" :style="sproutStyle">
          <div class="dots" :style="sproutEyesStyle"><div class="dot" :style="sproutPupilStyle"></div><div class="dot" :style="sproutPupilStyle"></div></div>
          <div class="mouth" :style="sproutMouthStyle"></div>
        </div>
      </div>
    </div>

    <div class="auth-panel">
      <div class="auth-card">
        <p class="card-eyebrow">{{ isRegisterMode ? t("auth.createProfile") : t("auth.accountAccess") }}</p>
        <h2>{{ isRegisterMode ? t("auth.createAccount") : t("auth.welcomeBack") }}</h2>
        <p class="card-copy">
          {{ isRegisterMode ? t("auth.cardCopyRegister") : t("auth.cardCopyLogin") }}
        </p>

        <form class="form" @submit.prevent="handleSubmit">
          <label v-if="isRegisterMode" class="field">
            <span>{{ t("auth.displayName") }}</span>
            <input v-model="displayName" type="text" placeholder="Anna Green" @focus="isTyping = true" @blur="isTyping = false" required />
          </label>

          <label class="field">
            <span>{{ t("auth.email") }}</span>
            <input v-model="email" type="email" placeholder="anna@carbonsnap.app" @focus="isTyping = true" @blur="isTyping = false" required />
          </label>

          <label class="field">
            <span>{{ t("auth.password") }}</span>
            <div class="password-wrap">
              <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="********" :autocomplete="isRegisterMode ? 'new-password' : 'current-password'" required />
              <button type="button" class="toggle" @click="showPassword = !showPassword">{{ showPassword ? t("auth.hide") : t("auth.show") }}</button>
            </div>
          </label>

          <div v-if="isRegisterMode && password.length > 0" class="pwd-strength">
            <div class="pwd-strength__top">
              <div class="pwd-bars" :data-score="strengthScore">
                <div class="pwd-bar" :class="{ 'pwd-bar--active': strengthScore >= 1 }"></div>
                <div class="pwd-bar" :class="{ 'pwd-bar--active': strengthScore >= 2 }"></div>
                <div class="pwd-bar" :class="{ 'pwd-bar--active': strengthScore >= 3 }"></div>
              </div>
              <span class="pwd-label" :class="`pwd-label--${strengthScore}`">{{ strengthLabel }}</span>
            </div>
            <ul class="pwd-rules">
              <li :class="{ 'pwd-rule--met': hasMinLength }">{{ t("auth.atLeastEight") }}</li>
              <li :class="{ 'pwd-rule--met': hasUppercase }">{{ t("auth.atLeastOneUppercase") }}</li>
              <li :class="{ 'pwd-rule--met': hasSpecial }">{{ t("auth.atLeastOneSpecial") }}</li>
            </ul>
          </div>

          <label v-if="isRegisterMode" class="field">
            <span>{{ t("auth.confirmPassword") }}</span>
            <div class="password-wrap">
              <input v-model="confirmPassword" :type="showConfirmPassword ? 'text' : 'password'" placeholder="********" autocomplete="new-password" required />
              <button type="button" class="toggle" @click="showConfirmPassword = !showConfirmPassword">{{ showConfirmPassword ? t("auth.hide") : t("auth.show") }}</button>
            </div>
          </label>

          <div class="meta">
            <label class="check"><input v-model="rememberMe" type="checkbox" /><span>{{ isRegisterMode ? t("auth.agreeTerms") : t("auth.keepSignedIn") }}</span></label>
            <RouterLink v-if="isRegisterMode" to="/terms">{{ t("auth.readTerms") }}</RouterLink>
          </div>

          <p v-if="error" class="message message--error">{{ error }}</p>
          <p v-else-if="successMessage" class="message message--success">{{ successMessage }}</p>

          <button class="primary" type="submit" :disabled="isLoading">
            {{ isRegisterMode ? (isLoading ? t("auth.createAccountBusy") : t("auth.createAccount")) : (isLoading ? t("auth.loginBusy") : t("auth.login")) }}
          </button>
        </form>

        <footer class="footer">
          <span>{{ isRegisterMode ? t("auth.alreadyHaveAccount") : t("auth.newToCarbonSnap") }}</span>
          <RouterLink :to="isRegisterMode ? '/login' : '/register'">{{ isRegisterMode ? t("auth.signIn") : t("auth.createAccount") }}</RouterLink>
        </footer>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast } from "../../composables/useToast.js";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({ mode: { type: String, default: "login" } });
const isRegisterMode = computed(() => props.mode === "register");

const router = useRouter();
const { register, login } = useAuth();
const { t } = useI18n();

const displayName = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const rememberMe = ref(false);
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const isLoading = ref(false);
const error = ref("");
const successMessage = ref("");

// Password strength
const hasMinLength = computed(() => password.value.length >= 8);
const hasUppercase = computed(() => /[A-Z]/.test(password.value));
const hasSpecial = computed(() => /[^a-zA-Z0-9]/.test(password.value));
const strengthScore = computed(() => [hasMinLength.value, hasUppercase.value, hasSpecial.value].filter(Boolean).length);
const strengthLabel = computed(() => ["", t("auth.weak"), t("auth.fair"), t("auth.strong")][strengthScore.value] ?? "");
const isTyping = ref(false);
const isLookingAtEachOther = ref(false);
const isPurpleBlinking = ref(false);
const isBlackBlinking = ref(false);
const isPurplePeeking = ref(false);
const isCelebrating = ref(false);
const isFailing = ref(false);
const mouseX = ref(0);
const mouseY = ref(0);

const leafRef = ref(null);
const botRef = ref(null);
const stoneRef = ref(null);
const sproutRef = ref(null);

let purpleBlinkTimeout;
let purpleBlinkDurationTimeout;
let blackBlinkTimeout;
let blackBlinkDurationTimeout;
let typingResetTimeout;
let purplePeekTimeout;
let purplePeekDurationTimeout;
let celebrateTimeout;
let failTimeout;

function onMouseMove(event) {
  mouseX.value = event.clientX;
  mouseY.value = event.clientY;
}

function startBlinkLoop(setter, timeoutStore, durationStore) {
  const schedule = () => {
    timeoutStore.id = window.setTimeout(() => {
      setter(true);
      durationStore.id = window.setTimeout(() => {
        setter(false);
        schedule();
      }, 150);
    }, Math.random() * 4000 + 3000);
  };
  schedule();
}

function calculateTracking(elementRef, faceXLimit = 15, faceYLimit = 10, bodySkewLimit = 6) {
  if (!elementRef.value) return { faceX: 0, faceY: 0, bodySkew: 0 };
  const rect = elementRef.value.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 3;
  const deltaX = mouseX.value - centerX;
  const deltaY = mouseY.value - centerY;
  return {
    faceX: Math.max(-faceXLimit, Math.min(faceXLimit, deltaX / 20)),
    faceY: Math.max(-faceYLimit, Math.min(faceYLimit, deltaY / 30)),
    bodySkew: Math.max(-bodySkewLimit, Math.min(bodySkewLimit, -deltaX / 120)),
  };
}

function calcPupilTransform(elementRef, maxDistance, forceLookX, forceLookY) {
  if (forceLookX !== undefined && forceLookY !== undefined) return { transform: `translate(${forceLookX}px, ${forceLookY}px)` };
  if (!elementRef.value) return { transform: "translate(0px, 0px)" };
  const rect = elementRef.value.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const deltaX = mouseX.value - centerX;
  const deltaY = mouseY.value - centerY;
  const angle = Math.atan2(deltaY, deltaX);
  const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);
  return { transform: `translate(${Math.cos(angle) * distance}px, ${Math.sin(angle) * distance}px)` };
}

function eyeStyle(isBlinking, small = false) {
  return { height: isBlinking ? "2px" : `${small ? 16 : 18}px` };
}

const leafTrack = computed(() => calculateTracking(leafRef));
const botTrack = computed(() => calculateTracking(botRef));
const stoneTrack = computed(() => calculateTracking(stoneRef));
const sproutTrack = computed(() => calculateTracking(sproutRef));
const passwordPeek = computed(() => password.value.length > 0 && showPassword.value);

const leafStyle = computed(() => ({ transform: passwordPeek.value ? "skewX(0deg)" : `skewX(${leafTrack.value.bodySkew - (isTyping.value ? 10 : 0)}deg)`, height: isTyping.value ? "350px" : "332px" }));
const botStyle = computed(() => ({ transform: passwordPeek.value ? "skewX(0deg)" : isLookingAtEachOther.value ? `skewX(${botTrack.value.bodySkew + 8}deg) translateX(14px)` : `skewX(${botTrack.value.bodySkew}deg)` }));
const stoneStyle = computed(() => ({ transform: passwordPeek.value ? "skewX(0deg)" : `skewX(${stoneTrack.value.bodySkew}deg)` }));
const sproutStyle = computed(() => ({ transform: passwordPeek.value ? "skewX(0deg)" : `skewX(${sproutTrack.value.bodySkew}deg)` }));

const leafEyesStyle = computed(() => ({ left: passwordPeek.value ? "28px" : isLookingAtEachOther.value ? "50px" : `${42 + leafTrack.value.faceX}px`, top: passwordPeek.value ? "72px" : `${92 + leafTrack.value.faceY}px` }));
const botEyesStyle = computed(() => ({ left: passwordPeek.value ? "26px" : isLookingAtEachOther.value ? "48px" : `${38 + botTrack.value.faceX}px`, top: passwordPeek.value ? "88px" : `${92 + botTrack.value.faceY}px` }));
const stoneEyesStyle = computed(() => ({ left: passwordPeek.value ? "58px" : `${86 + stoneTrack.value.faceX}px`, top: passwordPeek.value ? "78px" : `${82 + stoneTrack.value.faceY}px` }));
const sproutEyesStyle = computed(() => ({ left: passwordPeek.value ? "26px" : `${58 + sproutTrack.value.faceX}px`, top: passwordPeek.value ? "82px" : `${86 + sproutTrack.value.faceY}px` }));
const sproutMouthStyle = computed(() => ({ left: passwordPeek.value ? "22px" : `${52 + sproutTrack.value.faceX}px`, top: passwordPeek.value ? "134px" : `${142 + sproutTrack.value.faceY}px` }));

const leafPupilStyle = computed(() => calcPupilTransform(leafRef, 5, passwordPeek.value ? (isPurplePeeking.value ? 4 : -4) : isLookingAtEachOther.value ? 3 : undefined, passwordPeek.value ? (isPurplePeeking.value ? 5 : -4) : isLookingAtEachOther.value ? 4 : undefined));
const botPupilStyle = computed(() => calcPupilTransform(botRef, 4, passwordPeek.value ? -4 : isLookingAtEachOther.value ? 0 : undefined, passwordPeek.value ? -4 : isLookingAtEachOther.value ? -4 : undefined));
const stonePupilStyle = computed(() => calcPupilTransform(stoneRef, 5, passwordPeek.value ? -5 : undefined, passwordPeek.value ? -4 : undefined));
const sproutPupilStyle = computed(() => calcPupilTransform(sproutRef, 5, passwordPeek.value ? -5 : undefined, passwordPeek.value ? -4 : undefined));

watch(isTyping, (value) => {
  window.clearTimeout(typingResetTimeout);
  if (value) {
    isLookingAtEachOther.value = true;
    typingResetTimeout = window.setTimeout(() => {
      isLookingAtEachOther.value = false;
    }, 800);
    return;
  }
  isLookingAtEachOther.value = false;
});

watch([password, showPassword], ([newPassword, newShowPassword]) => {
  window.clearTimeout(purplePeekTimeout);
  window.clearTimeout(purplePeekDurationTimeout);
  isPurplePeeking.value = false;
  if (!(newPassword.length > 0 && newShowPassword)) return;
  const schedule = () => {
    purplePeekTimeout = window.setTimeout(() => {
      isPurplePeeking.value = true;
      purplePeekDurationTimeout = window.setTimeout(() => {
        isPurplePeeking.value = false;
        schedule();
      }, 800);
    }, Math.random() * 3000 + 2000);
  };
  schedule();
});

function celebrate() {
  isCelebrating.value = true;
  window.clearTimeout(celebrateTimeout);
  celebrateTimeout = window.setTimeout(() => {
    isCelebrating.value = false;
  }, 1800);
}

function failReact() {
  isFailing.value = true;
  isLookingAtEachOther.value = true;
  window.clearTimeout(failTimeout);
  failTimeout = window.setTimeout(() => {
    isFailing.value = false;
    isLookingAtEachOther.value = false;
  }, 1100);
}

async function handleSubmit() {
  error.value = "";
  successMessage.value = "";

  // Client-side validation before hitting the network
  if (isRegisterMode.value) {
    if (!displayName.value.trim()) {
      error.value = t("auth.errorDisplayName");
      return failReact();
    }
    if (!hasMinLength.value) {
      error.value = t("auth.errorMinLength");
      return failReact();
    }
    if (!hasUppercase.value) {
      error.value = t("auth.errorUppercase");
      return failReact();
    }
    if (!hasSpecial.value) {
      error.value = t("auth.errorSpecial");
      return failReact();
    }
    if (password.value !== confirmPassword.value) {
      error.value = t("auth.errorMismatch");
      return failReact();
    }
    if (!rememberMe.value) {
      error.value = t("auth.errorTerms");
      return failReact();
    }
  } else {
    if (!email.value.trim() || !password.value) {
      error.value = t("auth.errorEmailPassword");
      return failReact();
    }
  }

  isLoading.value = true;
  try {
    if (isRegisterMode.value) {
      await register(displayName.value.trim(), email.value.trim(), password.value);
      celebrate();
      // Brief pause so the user sees the celebrate animation before redirect
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      router.push("/");
    } else {
      await login(email.value.trim(), password.value);
      celebrate();
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      router.push("/");
    }
  } catch (err) {
    error.value = err.message || t("auth.errorGeneric");
    showErrorToast(isRegisterMode.value ? "Registration failed" : "Sign in failed", error.value);
    failReact();
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  window.addEventListener("mousemove", onMouseMove);
  purpleBlinkTimeout = { id: undefined };
  purpleBlinkDurationTimeout = { id: undefined };
  blackBlinkTimeout = { id: undefined };
  blackBlinkDurationTimeout = { id: undefined };
  startBlinkLoop((value) => { isPurpleBlinking.value = value; }, purpleBlinkTimeout, purpleBlinkDurationTimeout);
  startBlinkLoop((value) => { isBlackBlinking.value = value; }, blackBlinkTimeout, blackBlinkDurationTimeout);
});

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onMouseMove);
  [purpleBlinkTimeout, purpleBlinkDurationTimeout, blackBlinkTimeout, blackBlinkDurationTimeout].forEach((item) => item && window.clearTimeout(item.id));
  [typingResetTimeout, purplePeekTimeout, purplePeekDurationTimeout, celebrateTimeout, failTimeout].forEach((item) => window.clearTimeout(item));
});
</script>

<style scoped src="../../styles/views/auth-view.css"></style>
