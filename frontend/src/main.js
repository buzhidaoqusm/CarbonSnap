import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
// @font-face only: the browser downloads Archivo the first time an element uses it.
import "@fontsource-variable/archivo/wdth.css";
import "./styles/base.css";
import "./styles/tokens.css";

createApp(App).use(router).mount("#app");
