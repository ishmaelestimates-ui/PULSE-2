import { createRouter, createWebHistory } from "vue-router";
import EpisodeListView from "../views/EpisodeListView.vue";
import EpisodeDetailView from "../views/EpisodeDetailView.vue";
import BrandSettingsView from "../views/BrandSettingsView.vue";
import UserManagementView from "../views/UserManagementView.vue";
import LoginView from "../views/LoginView.vue";
import FeatureListView from "../views/FeatureListView.vue";

const routes = [
  { path: "/", name: "episodes", component: EpisodeListView },
  {
    path: "/episodes/:id",
    name: "episode-detail",
    component: EpisodeDetailView,
    props: (route) => ({ id: Number(route.params.id) }),
  },
  { path: "/settings", name: "brand-settings", component: BrandSettingsView },
  { path: "/settings/users", name: "user-management", component: UserManagementView },
  { path: "/login", name: "login", component: LoginView },
  { path: "/accept-invite", name: "accept-invite", component: LoginView },
  { path: "/magic-link", name: "magic-link", component: LoginView },
  { path: "/features", name: "features", component: FeatureListView },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to) => {
  const token = localStorage.getItem("pulse_token");
  const publicPaths = new Set(["/login", "/accept-invite", "/magic-link"]);

  if (!token && !publicPaths.has(to.path)) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (token && to.name === "login") {
    return { name: "episodes" };
  }

  return true;
});

export default router;
