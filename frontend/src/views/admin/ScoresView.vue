<script setup>
import { onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const periods = ref([]);
const departments = ref([]);
const performances = ref([]);
const reviews = ref([]);
const selectedPeriodId = ref("");
const formError = ref("");

const performanceForm = reactive({
  id: null,
  department: "",
  performance_score: "",
});

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
  await loadData();
}

async function loadData() {
  if (!selectedPeriodId.value) return;
  const params = { review_period: selectedPeriodId.value };
  const [performanceResponse, reviewsResponse] = await Promise.all([
    run(() => client.get("/admin/department-performances/", { params })),
    run(() => client.get("/admin/reviews/", { params: { ...params, status: "SUBMITTED" } })),
  ]);
  if (performanceResponse) performances.value = performanceResponse.data;
  if (reviewsResponse) reviews.value = reviewsResponse.data;
}

function resetPerformanceForm() {
  Object.assign(performanceForm, { id: null, department: "", performance_score: "" });
  formError.value = "";
}

function editPerformance(performance) {
  Object.assign(performanceForm, {
    id: performance.id,
    department: performance.department,
    performance_score: performance.performance_score,
  });
  formError.value = "";
}

async function submitPerformance() {
  formError.value = "";
  try {
    const payload = {
      review_period: Number(selectedPeriodId.value),
      department: Number(performanceForm.department),
      performance_score: performanceForm.performance_score,
    };
    if (performanceForm.id) {
      await client.patch(
        `/admin/department-performances/${performanceForm.id}/`,
        payload
      );
    } else {
      await client.post("/admin/department-performances/", payload);
    }
    resetPerformanceForm();
    await loadData();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function calculateScore(review) {
  formError.value = "";
  try {
    await client.post(`/admin/reviews/${review.id}/calculate-score/`);
    await loadData();
  } catch (err) {
    formError.value = formatError(err);
  }
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">점수 관리</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div v-if="formError" class="alert alert-danger">{{ formError }}</div>

    <div class="row mb-3">
      <div class="col-md-4">
        <label class="form-label">평가 기간</label>
        <select v-model="selectedPeriodId" class="form-select" @change="loadData">
          <option v-for="period in periods" :key="period.id" :value="String(period.id)">
            {{ period.name }} ({{ period.status }})
          </option>
        </select>
      </div>
    </div>

    <div v-if="!selectedPeriodId" class="alert alert-info">평가 기간을 선택하세요.</div>
    <template v-else>
      <h2 class="h5">부서 성과 점수</h2>
      <div class="card mb-4">
        <div class="card-body">
          <form class="row g-2 align-items-end" @submit.prevent="submitPerformance">
            <div class="col-md-3">
              <label class="form-label">부서</label>
              <select v-model="performanceForm.department" class="form-select" required>
                <option value="" disabled>선택</option>
                <option v-for="department in departments" :key="department.id" :value="department.id">
                  {{ department.name }}
                </option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">성과 점수 (0~100)</label>
              <input
                v-model="performanceForm.performance_score"
                type="number"
                min="0"
                max="100"
                step="0.01"
                class="form-control"
                required
              />
            </div>
            <div class="col-md-3 d-flex gap-2">
              <button class="btn btn-primary">{{ performanceForm.id ? "수정" : "추가" }}</button>
              <button
                v-if="performanceForm.id"
                type="button"
                class="btn btn-secondary"
                @click="resetPerformanceForm"
              >
                취소
              </button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="performances.length === 0" class="alert alert-info mb-4">
        이 기간에 입력된 부서 성과 점수가 없습니다.
      </div>
      <table v-else class="table align-middle mb-4">
        <thead>
          <tr>
            <th>부서</th>
            <th>성과 점수</th>
            <th>조정 예시 ((점수-70)×0.2)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="performance in performances" :key="performance.id">
            <td>{{ departments.find((d) => d.id === performance.department)?.name || "-" }}</td>
            <td>{{ performance.performance_score }}</td>
            <td>{{ (performance.performance_score - 70) * 0.2 >= 0 ? "+" : "" }}{{ ((performance.performance_score - 70) * 0.2).toFixed(2) }}</td>
            <td class="text-end">
              <button class="btn btn-outline-primary btn-sm" @click="editPerformance(performance)">수정</button>
            </td>
          </tr>
        </tbody>
      </table>

      <h2 class="h5">제출 완료 평가 점수</h2>
      <div v-if="reviews.length === 0" class="alert alert-info">
        제출 완료된 평가가 없습니다.
      </div>
      <table v-else class="table align-middle">
        <thead>
          <tr>
            <th>사번</th>
            <th>이름</th>
            <th>개인 점수</th>
            <th>부서 점수</th>
            <th>부서 조정</th>
            <th>최종 점수</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="review in reviews" :key="review.id">
            <td>{{ review.employee.employee_number }}</td>
            <td>{{ review.employee.name }}</td>
            <td>{{ review.final_score?.individual_score ?? "-" }}</td>
            <td>{{ review.final_score?.department_score ?? "-" }}</td>
            <td>{{ review.final_score?.department_adjustment ?? "-" }}</td>
            <td>
              <strong>{{ review.final_score?.final_score ?? "-" }}</strong>
            </td>
            <td class="text-end">
              <button class="btn btn-outline-primary btn-sm" @click="calculateScore(review)">
                {{ review.final_score ? "재계산" : "점수 계산" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </template>
</template>
