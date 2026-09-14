<script setup>
import { useRouter } from "vue-router";
import { useAuth } from "./composables/auth";

const router = useRouter();
const { state, logout } = useAuth();

async function onLogout() {
  await logout();
  router.push("/login");
}
</script>

<template>
  <nav v-if="state.user" class="navbar navbar-expand-lg navbar-nexora">
    <div class="container-fluid">
      <router-link class="navbar-brand navbar-brand-custom" to="/">
        인사<span>평가</span>
      </router-link>
      <div class="navbar-nav ms-auto align-items-center">
        <span class="navbar-user-name me-3">
          {{ state.user.name }} ({{ state.user.employee_number }})
        </span>
        <button class="btn btn-outline-primary btn-sm" @click="onLogout">
          로그아웃
        </button>
      </div>
    </div>
  </nav>
  <main class="container py-4">
    <router-view />
  </main>
</template>
