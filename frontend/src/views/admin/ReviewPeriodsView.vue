<script setup>
import { onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const periods = ref([]);
const formError = ref("");
const actionError = ref("");
const form = reactive({
  id: null,
  name: "",
  description: "",
  start_date: "",
  end_date: "",
});

const statusLabels = { DRAFT: "준비", OPEN: "진행 중", CLOSED: "종료" };
const statusClasses = { DRAFT: "bg-secondary", OPEN: "bg-success", CLOSED: "bg-dark" };

async function load() {
  const response = await run(() => client.get("/admin/review-periods/"));
  if (response) periods.value = response.data;
}

function resetForm() {
  Object.assign(form, { id: null, name: "", description: "", start_date: "", end_date: "" });
  formError.value = "";
}

function editPeriod(period) {
  Object.assign(form, {
    id: period.id,
    name: period.name,
    description: period.description,
    start_date: period.start_date,
    end_date: period.end_date,
  });
  formError.value = "";
}

async function submitForm() {
  formError.value = "";
  try {
    if (form.id) {
      await client.patch(`/admin/review-periods/${form.id}/`, { ...form });
    } else {
      await client.post("/admin/review-periods/", { ...form });
    }
    resetForm();
    await load();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function changeStatus(period, status) {
  actionError.value = "";
  try {
    await client.post(`/admin/review-periods/${period.id}/status/`, { status });
    await load();
  } catch (err) {
    actionError.value = formatError(err);
  }
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">평가 기간 관리</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div v-if="actionError" class="alert alert-danger">{{ actionError }}</div>

    <div class="card mb-4">
      <div class="card-body">
        <h2 class="h5">{{ form.id ? "평가 기간 수정" : "평가 기간 추가" }}</h2>
        <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
        <form class="row g-2 align-items-end" @submit.prevent="submitForm">
          <div class="col-md-3">
            <label class="form-label">이름</label>
            <input v-model="form.name" class="form-control" required />
          </div>
          <div class="col-md-3">
            <label class="form-label">설명</label>
            <input v-model="form.description" class="form-control" />
          </div>
          <div class="col-md-2">
            <label class="form-label">시작일</label>
            <input v-model="form.start_date" type="date" class="form-control" required />
          </div>
          <div class="col-md-2">
            <label class="form-label">종료일</label>
            <input v-model="form.end_date" type="date" class="form-control" required />
          </div>
          <div class="col-md-2 d-flex gap-2">
            <button class="btn btn-primary">{{ form.id ? "수정" : "추가" }}</button>
            <button v-if="form.id" type="button" class="btn btn-secondary" @click="resetForm">취소</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="periods.length === 0" class="alert alert-info">평가 기간이 없습니다.</div>
    <table v-else class="table align-middle">
      <thead>
        <tr>
          <th>이름</th>
          <th>기간</th>
          <th>상태</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="period in periods" :key="period.id">
          <td>{{ period.name }}</td>
          <td>{{ period.start_date }} ~ {{ period.end_date }}</td>
          <td>
            <span class="badge" :class="statusClasses[period.status]">
              {{ statusLabels[period.status] }}
            </span>
          </td>
          <td class="text-end">
            <button
              v-if="period.status === 'DRAFT'"
              class="btn btn-success btn-sm me-1"
              @click="changeStatus(period, 'OPEN')"
            >
              OPEN
            </button>
            <button
              v-if="period.status === 'OPEN'"
              class="btn btn-dark btn-sm me-1"
              @click="changeStatus(period, 'CLOSED')"
            >
              CLOSED
            </button>
            <button class="btn btn-outline-primary btn-sm" @click="editPeriod(period)">수정</button>
          </td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
