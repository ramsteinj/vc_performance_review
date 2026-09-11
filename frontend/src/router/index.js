import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "../composables/auth";
import LoginView from "../views/LoginView.vue";
import HomeView from "../views/HomeView.vue";
import ReviewView from "../views/ReviewView.vue";
import AdminLayout from "../views/admin/AdminLayout.vue";
import DashboardView from "../views/admin/DashboardView.vue";
import UsersView from "../views/admin/UsersView.vue";
import DepartmentsView from "../views/admin/DepartmentsView.vue";
import ReviewPeriodsView from "../views/admin/ReviewPeriodsView.vue";
import QuestionsView from "../views/admin/QuestionsView.vue";
import EvaluatorsView from "../views/admin/EvaluatorsView.vue";
import MonitoringView from "../views/admin/MonitoringView.vue";
import ScoresView from "../views/admin/ScoresView.vue";

const routes = [
  { path: "/login", name: "login", component: LoginView },
  { path: "/", name: "home", component: HomeView },
  { path: "/review", name: "review", component: ReviewView },
  {
    path: "/admin",
    component: AdminLayout,
    meta: { admin: true },
    children: [
      { path: "", name: "admin-dashboard", component: DashboardView },
      { path: "users", name: "admin-users", component: UsersView },
      { path: "departments", name: "admin-departments", component: DepartmentsView },
      { path: "review-periods", name: "admin-review-periods", component: ReviewPeriodsView },
      { path: "questions", name: "admin-questions", component: QuestionsView },
      { path: "evaluators", name: "admin-evaluators", component: EvaluatorsView },
      { path: "monitoring", name: "admin-monitoring", component: MonitoringView },
      { path: "scores", name: "admin-scores", component: ScoresView },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

function homePathFor(user) {
  return user && user.role === "ADMIN" ? "/admin" : "/";
}

router.beforeEach(async (to) => {
  const { state, fetchMe } = useAuth();
  if (!state.loaded) {
    await fetchMe();
  }
  const isAuthed = Boolean(state.user);
  if (to.path === "/login") {
    return isAuthed ? homePathFor(state.user) : true;
  }
  if (!isAuthed) {
    return { path: "/login" };
  }
  if (to.meta.admin && state.user.role !== "ADMIN") {
    return { path: "/" };
  }
  if (to.path === "/" && state.user.role === "ADMIN") {
    return { path: "/admin" };
  }
  return true;
});

export default router;
