<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../composables/auth";
import { useApi } from "../composables/useApi";

const router = useRouter();
const { login } = useAuth();
const { loading, error, run } = useApi();
const form = reactive({ name: "", employee_number: "", password: "" });

async function onSubmit() {
  const user = await run(() => login({ ...form }));
  if (user) {
    router.push(user.role === "ADMIN" ? "/admin" : "/");
  }
}
</script>

<template>
  <div class="row justify-content-center">
    <div class="col-md-4">
      <h1 class="h3 mb-3 text-center">인사평가 시스템</h1>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <form @submit.prevent="onSubmit">
        <div class="mb-3">
          <label class="form-label">이름</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">사번</label>
          <input v-model="form.employee_number" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">비밀번호</label>
          <input
            v-model="form.password"
            type="password"
            class="form-control"
            required
          />
        </div>
        <button class="btn btn-primary w-100" :disabled="loading">
          {{ loading ? "로그인 중..." : "로그인" }}
        </button>
      </form>
    </div>
  </div>
</template>
