// Stylesheets load in this order, and among rules of equal specificity the later
// one wins. The old pages' fonts come first, where the Google Fonts stylesheet was.
import "./styles/legacy-fonts.css";

import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
// @font-face only: the browser downloads Archivo the first time an element uses it.
import "@fontsource-variable/archivo/wdth.css";
import "./styles/base.css";
import "./styles/tokens.css";
// Last, where the Tailwind CDN used to append its <style>.
import "./styles/tailwind.css";

createApp(App).use(router).mount("#app");
