import { createRouter, createWebHistory } from "vue-router";

function isAuthenticated(): boolean {
  const token = localStorage.getItem("auth_token");
  return !!token;
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/Login.vue"),
      meta: { public: true },
    },
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
    {
      path: "/logs",
      name: "logs",
      component: () => import("@/views/Logs.vue"),
    },
  ],
});

router.beforeEach((to, _from, next) => {
  if (to.meta.public) {
    if (isAuthenticated() && to.name === "login") {
      next({ name: "dashboard" });
    } else {
      next();
    }
  } else {
    if (isAuthenticated()) {
      next();
    } else {
      next({ name: "login" });
    }
  }
});

export default router;
