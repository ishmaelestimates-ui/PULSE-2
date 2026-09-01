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

export default createRouter({
  history: createWebHistory(),
  routes,
});
