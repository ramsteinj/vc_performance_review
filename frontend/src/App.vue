<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "./composables/auth";
import PasswordChangeModal from "./components/PasswordChangeModal.vue";

const router = useRouter();
const { state, logout } = useAuth();
const showPasswordModal = ref(false);

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
        <button class="btn btn-outline-primary btn-sm me-2" @click="showPasswordModal = true">
          패스워드 변경
        </button>
        <button class="btn btn-outline-primary btn-sm" @click="onLogout">
          로그아웃
        </button>
      </div>
    </div>
  </nav>
  <PasswordChangeModal v-if="showPasswordModal" @close="showPasswordModal = false" />
  <main class="container py-4">
    <router-view />
  </main>
</template>
