<script setup>
import { useRouter } from "vue-router";
import { useAuth } from "./composables/auth";

const router = useRouter();
const { state, logout } = useAuth();

const adminLinks = [
  { to: "/admin", label: "대시보드" },
  { to: "/admin/users", label: "사용자" },
  { to: "/admin/departments", label: "부서" },
  { to: "/admin/review-periods", label: "평가 기간" },
  { to: "/admin/questions", label: "문항" },
  { to: "/admin/evaluators", label: "평가자" },
  { to: "/admin/monitoring", label: "모니터링" },
  { to: "/admin/scores", label: "점수" },
];

async function onLogout() {
  await logout();
  router.push("/login");
}
</script>

<template>
  <nav v-if="state.user" class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <router-link class="navbar-brand" to="/">인사평가</router-link>
      <div class="navbar-nav flex-row flex-wrap" v-if="state.user.role === 'ADMIN'">
        <router-link
          v-for="link in adminLinks"
          :key="link.to"
          class="nav-link me-2"
          :to="link.to"
        >
          {{ link.label }}
        </router-link>
      </div>
      <div class="navbar-nav ms-auto align-items-center">
        <span class="navbar-text me-3">
          {{ state.user.name }} ({{ state.user.employee_number }})
        </span>
        <button class="btn btn-outline-light btn-sm" @click="onLogout">
          로그아웃
        </button>
      </div>
    </div>
  </nav>
  <main class="container py-4">
    <router-view />
  </main>
</template>
