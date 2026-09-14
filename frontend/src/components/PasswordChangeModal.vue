<script setup>
import { reactive, ref } from "vue";
import client, { formatError } from "../api/client";

const emit = defineEmits(["close"]);

const form = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
});
const error = ref("");
const success = ref("");
const saving = ref(false);

async function onSubmit() {
  error.value = "";
  success.value = "";
  if (form.new_password !== form.confirm_password) {
    error.value = "새 비밀번호가 일치하지 않습니다.";
    return;
  }
  saving.value = true;
  try {
    await client.post("/auth/password/change/", {
      current_password: form.current_password,
      new_password: form.new_password,
    });
    success.value = "비밀번호가 변경되었습니다.";
    setTimeout(() => emit("close"), 1200);
  } catch (err) {
    error.value = formatError(err);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="modal fade show d-block" tabindex="-1" @click.self="emit('close')">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h2 class="modal-title h5">패스워드 변경</h2>
          <button type="button" class="btn-close" @click="emit('close')"></button>
        </div>
        <form @submit.prevent="onSubmit">
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div v-if="success" class="alert alert-success py-2">{{ success }}</div>
            <div class="mb-3">
              <label class="form-label">현재 비밀번호</label>
              <input
                v-model="form.current_password"
                type="password"
                class="form-control"
                required
              />
            </div>
            <div class="mb-3">
              <label class="form-label">새 비밀번호</label>
              <input
                v-model="form.new_password"
                type="password"
                class="form-control"
                required
              />
              <div class="form-text">8자 이상, 숫자만으로 구성할 수 없습니다.</div>
            </div>
            <div class="mb-1">
              <label class="form-label">새 비밀번호 확인</label>
              <input
                v-model="form.confirm_password"
                type="password"
                class="form-control"
                required
              />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="emit('close')">
              취소
            </button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? "변경 중..." : "변경" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
  <div class="modal-backdrop fade show"></div>
</template>
