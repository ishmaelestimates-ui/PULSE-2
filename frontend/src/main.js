import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./assets/styles.css";
import "./styles/animations.css";

createApp(App).use(router).mount("#app");
