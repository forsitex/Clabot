import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/views/Dashboard.vue"),
    },
    {
      path: "/teams",
      name: "teams",
      component: () => import("@/views/Teams.vue"),
    },
    {
      path: "/history",
      name: "history",
      component: () => import("@/views/History.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/Settings.vue"),
    },
  ],
});

export default router;
