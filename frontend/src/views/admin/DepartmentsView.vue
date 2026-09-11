<script setup>
import { onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const departments = ref([]);
const formError = ref("");
const form = reactive({ id: null, name: "", description: "", is_active: true });

async function load() {
  const response = await run(() => client.get("/admin/departments/"));
  if (response) departments.value = response.data;
}

function resetForm() {
  Object.assign(form, { id: null, name: "", description: "", is_active: true });
  formError.value = "";
}

function editDepartment(department) {
  Object.assign(form, {
    id: department.id,
    name: department.name,
    description: department.description,
    is_active: department.is_active,
  });
  formError.value = "";
}

async function submitForm() {
  formError.value = "";
  try {
    if (form.id) {
      await client.patch(`/admin/departments/${form.id}/`, { ...form });
    } else {
      await client.post("/admin/departments/", { ...form });
    }
    resetForm();
    await load();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function deactivate(department) {
  if (!confirm(`"${department.name}" 부서를 비활성화하시겠습니까?`)) return;
  await run(() => client.delete(`/admin/departments/${department.id}/`));
  await load();
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">부서 관리</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div class="card mb-4">
      <div class="card-body">
        <h2 class="h5">{{ form.id ? "부서 수정" : "부서 추가" }}</h2>
        <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
        <form class="row g-2 align-items-end" @submit.prevent="submitForm">
          <div class="col-md-3">
            <label class="form-label">부서명</label>
            <input v-model="form.name" class="form-control" required />
          </div>
          <div class="col-md-4">
            <label class="form-label">설명</label>
            <input v-model="form.description" class="form-control" />
          </div>
          <div class="col-md-1 form-check ms-2">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="dept-active" />
            <label class="form-check-label" for="dept-active">활성</label>
          </div>
          <div class="col-md-3 d-flex gap-2">
            <button class="btn btn-primary">{{ form.id ? "수정" : "추가" }}</button>
            <button v-if="form.id" type="button" class="btn btn-secondary" @click="resetForm">취소</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="departments.length === 0" class="alert alert-info">부서가 없습니다.</div>
    <table v-else class="table align-middle">
      <thead>
        <tr>
          <th>부서명</th>
          <th>설명</th>
          <th>상태</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="department in departments" :key="department.id">
          <td>{{ department.name }}</td>
          <td>{{ department.description || "-" }}</td>
          <td>
            <span class="badge" :class="department.is_active ? 'bg-success' : 'bg-secondary'">
              {{ department.is_active ? "활성" : "비활성" }}
            </span>
          </td>
          <td class="text-end">
            <button class="btn btn-outline-primary btn-sm me-1" @click="editDepartment(department)">수정</button>
            <button v-if="department.is_active" class="btn btn-outline-danger btn-sm" @click="deactivate(department)">
              비활성화
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
