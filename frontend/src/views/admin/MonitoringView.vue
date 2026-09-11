<script setup>
import { onMounted, ref } from "vue";
import client from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const periods = ref([]);
const departments = ref([]);
const reviews = ref([]);
const summary = ref(null);
const selectedPeriodId = ref("");
const selectedStatus = ref("");
const selectedDepartmentId = ref("");

const statusLabels = {
  NOT_STARTED: "미시작",
  IN_PROGRESS: "작성 중",
  SUBMITTED: "제출 완료",
};

const statusClasses = {
  NOT_STARTED: "bg-secondary",
  IN_PROGRESS: "bg-warning text-dark",
  SUBMITTED: "bg-success",
};

async function load() {
  const [periodsResponse, departmentsResponse] = await Promise.all([
    run(() => client.get("/admin/review-periods/")),
    run(() => client.get("/admin/departments/")),
  ]);
  if (periodsResponse) {
    periods.value = periodsResponse.data;
    if (!selectedPeriodId.value && periods.value.length) {
      selectedPeriodId.value = String(periods.value[0].id);
    }
  }
  if (departmentsResponse) departments.value = departmentsResponse.data;
  await loadMonitoring();
}

async function loadMonitoring() {
  const params = {};
  if (selectedPeriodId.value) params.review_period = selectedPeriodId.value;
  if (selectedDepartmentId.value) params.department = selectedDepartmentId.value;
  if (selectedStatus.value) params.status = selectedStatus.value;

  const [summaryResponse, reviewsResponse] = await Promise.all([
    run(() => client.get("/admin/monitoring/summary/", { params })),
    run(() => client.get("/admin/reviews/", { params })),
  ]);
  if (summaryResponse) summary.value = summaryResponse.data;
  if (reviewsResponse) reviews.value = reviewsResponse.data;
}

function csvUrl() {
  const params = new URLSearchParams();
  if (selectedPeriodId.value) params.set("review_period", selectedPeriodId.value);
  if (selectedDepartmentId.value) params.set("department", selectedDepartmentId.value);
  if (selectedStatus.value) params.set("status", selectedStatus.value);
  const query = params.toString();
  return `/api/admin/monitoring/export/${query ? `?${query}` : ""}`;
}

onMounted(load);
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h1 class="h3 mb-0">응답 모니터링</h1>
    <a class="btn btn-success" :href="csvUrl()">CSV 다운로드</a>
  </div>

  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div class="row g-2 mb-3">
      <div class="col-md-3">
        <label class="form-label">평가 기간</label>
        <select v-model="selectedPeriodId" class="form-select" @change="loadMonitoring">
          <option value="">전체</option>
          <option v-for="period in periods" :key="period.id" :value="String(period.id)">
            {{ period.name }}
          </option>
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">부서</label>
        <select v-model="selectedDepartmentId" class="form-select" @change="loadMonitoring">
          <option value="">전체</option>
          <option v-for="department in departments" :key="department.id" :value="String(department.id)">
            {{ department.name }}
          </option>
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">상태</label>
        <select v-model="selectedStatus" class="form-select" @change="loadMonitoring">
          <option value="">전체</option>
          <option value="NOT_STARTED">미시작</option>
          <option value="IN_PROGRESS">작성 중</option>
          <option value="SUBMITTED">제출 완료</option>
        </select>
      </div>
    </div>

    <div v-if="summary" class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="card text-center"><div class="card-body">
          <div class="fs-4">{{ summary.total }}</div>
          <div class="text-muted">전체 대상자</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card text-center"><div class="card-body">
          <div class="fs-4">{{ summary.not_started }}</div>
          <div class="text-muted">미응답</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card text-center"><div class="card-body">
          <div class="fs-4">{{ summary.in_progress }}</div>
          <div class="text-muted">작성 중</div>
        </div></div>
      </div>
      <div class="col-md-3">
        <div class="card text-center"><div class="card-body">
          <div class="fs-4">{{ summary.submitted }}</div>
          <div class="text-muted">제출 완료 ({{ summary.response_rate }}%)</div>
        </div></div>
      </div>
    </div>

    <div v-if="reviews.length === 0" class="alert alert-info">조건에 맞는 평가가 없습니다.</div>
    <table v-else class="table align-middle">
      <thead>
        <tr>
          <th>사번</th>
          <th>이름</th>
          <th>부서</th>
          <th>상태</th>
          <th>1차 평가자</th>
          <th>2차 평가자</th>
          <th>제출일시</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="review in reviews" :key="review.id">
          <td>{{ review.employee.employee_number }}</td>
          <td>{{ review.employee.name }}</td>
          <td>{{ review.employee.department?.name || "-" }}</td>
          <td>
            <span class="badge" :class="statusClasses[review.status]">
              {{ statusLabels[review.status] }}
            </span>
          </td>
          <td>{{ review.primary_evaluator?.name || "-" }}</td>
          <td>{{ review.secondary_evaluator?.name || "-" }}</td>
          <td>{{ review.submitted_at || "-" }}</td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
