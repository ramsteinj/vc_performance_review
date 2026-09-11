<script setup>
import { onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const users = ref([]);
const departments = ref([]);
const formError = ref("");
const form = reactive({
  id: null,
  employee_number: "",
  name: "",
  role: "EMPLOYEE",
  department: "",
  password: "",
  is_active: true,
});

async function load() {
  const [usersResponse, departmentsResponse] = await Promise.all([
    run(() => client.get("/admin/users/")),
    run(() => client.get("/admin/departments/")),
  ]);
  if (usersResponse) users.value = usersResponse.data;
  if (departmentsResponse) departments.value = departmentsResponse.data;
}

function resetForm() {
  Object.assign(form, {
    id: null,
    employee_number: "",
    name: "",
    role: "EMPLOYEE",
    department: "",
    password: "",
    is_active: true,
  });
  formError.value = "";
}

function editUser(user) {
  Object.assign(form, {
    id: user.id,
    employee_number: user.employee_number,
    name: user.name,
    role: user.role,
    department: user.department || "",
    password: "",
    is_active: user.is_active,
  });
  formError.value = "";
}

async function submitForm() {
  formError.value = "";
  const payload = {
    employee_number: form.employee_number,
    name: form.name,
    role: form.role,
    is_active: form.is_active,
  };
  if (form.department) payload.department = Number(form.department);
  if (form.password) payload.password = form.password;
  try {
    if (form.id) {
      await client.patch(`/admin/users/${form.id}/`, payload);
    } else {
      await client.post("/admin/users/", payload);
    }
    resetForm();
    await load();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function deactivate(user) {
  if (!confirm(`${user.name} 사용자를 비활성화하시겠습니까?`)) return;
  await run(() => client.delete(`/admin/users/${user.id}/`));
  await load();
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">사용자 관리</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div class="card mb-4">
      <div class="card-body">
        <h2 class="h5">{{ form.id ? "사용자 수정" : "사용자 추가" }}</h2>
        <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
        <form class="row g-2 align-items-end" @submit.prevent="submitForm">
          <div class="col-md-2">
            <label class="form-label">사번</label>
            <input v-model="form.employee_number" class="form-control" required />
          </div>
          <div class="col-md-2">
            <label class="form-label">이름</label>
            <input v-model="form.name" class="form-control" required />
          </div>
          <div class="col-md-2">
            <label class="form-label">권한</label>
            <select v-model="form.role" class="form-select">
              <option value="EMPLOYEE">직원</option>
              <option value="ADMIN">관리자</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">부서</label>
            <select v-model="form.department" class="form-select">
              <option value="">없음</option>
              <option v-for="department in departments" :key="department.id" :value="department.id">
                {{ department.name }}
              </option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">비밀번호{{ form.id ? " (변경 시)" : "" }}</label>
            <input v-model="form.password" type="password" class="form-control" :required="!form.id" />
          </div>
          <div class="col-md-1 form-check ms-2">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="user-active" />
            <label class="form-check-label" for="user-active">활성</label>
          </div>
          <div class="col-md-2 d-flex gap-2">
            <button class="btn btn-primary">{{ form.id ? "수정" : "추가" }}</button>
            <button v-if="form.id" type="button" class="btn btn-secondary" @click="resetForm">취소</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="users.length === 0" class="alert alert-info">사용자가 없습니다.</div>
    <table v-else class="table align-middle">
      <thead>
        <tr>
          <th>사번</th>
          <th>이름</th>
          <th>권한</th>
          <th>부서</th>
          <th>상태</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.employee_number }}</td>
          <td>{{ user.name }}</td>
          <td>{{ user.role === "ADMIN" ? "관리자" : "직원" }}</td>
          <td>{{ user.department_detail?.name || "-" }}</td>
          <td>
            <span class="badge" :class="user.is_active ? 'bg-success' : 'bg-secondary'">
              {{ user.is_active ? "활성" : "비활성" }}
            </span>
          </td>
          <td class="text-end">
            <button class="btn btn-outline-primary btn-sm me-1" @click="editUser(user)">수정</button>
            <button v-if="user.is_active" class="btn btn-outline-danger btn-sm" @click="deactivate(user)">
              비활성화
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
