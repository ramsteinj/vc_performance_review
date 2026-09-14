<script setup>
import { onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { periodStatusLabels } from "../../utils/labels";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const periods = ref([]);
const users = ref([]);
const reviews = ref([]);
const selectedPeriodId = ref("");
const formError = ref("");

const createForm = reactive({
  employee: "",
  primary_evaluator: "",
  secondary_evaluator: "",
});

const statusLabels = {
  NOT_STARTED: "미시작",
  IN_PROGRESS: "작성 중",
  SUBMITTED: "제출 완료",
};

async function load() {
  const [periodsResponse, usersResponse] = await Promise.all([
    run(() => client.get("/admin/review-periods/")),
    run(() => client.get("/admin/users/")),
  ]);
  if (periodsResponse) {
    periods.value = periodsResponse.data;
    if (!selectedPeriodId.value && periods.value.length) {
      selectedPeriodId.value = String(periods.value[0].id);
    }
  }
  if (usersResponse) users.value = usersResponse.data;
  if (selectedPeriodId.value) {
    await loadReviews();
  }
}

async function loadReviews() {
  const response = await run(() =>
    client.get("/admin/reviews/", {
      params: { review_period: selectedPeriodId.value },
    })
  );
  if (response) reviews.value = response.data;
}

function resetCreateForm() {
  Object.assign(createForm, {
    employee: "",
    primary_evaluator: "",
    secondary_evaluator: "",
  });
  formError.value = "";
}

async function createReview() {
  formError.value = "";
  try {
    await client.post("/admin/reviews/", {
      review_period: Number(selectedPeriodId.value),
      employee: Number(createForm.employee),
      primary_evaluator: Number(createForm.primary_evaluator),
      secondary_evaluator: createForm.secondary_evaluator
        ? Number(createForm.secondary_evaluator)
        : null,
    });
    resetCreateForm();
    await loadReviews();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function saveEvaluators(review) {
  formError.value = "";
  try {
    await client.post(`/admin/reviews/${review.id}/evaluators/`, {
      primary_evaluator: Number(review.primary_evaluator?.id ?? ""),
      secondary_evaluator: review.secondary_evaluator?.id ?? null,
    });
    await loadReviews();
  } catch (err) {
    formError.value = formatError(err);
  }
}

function editableCopy(review) {
  return {
    ...review,
    _primary: review.primary_evaluator?.id ?? "",
    _secondary: review.secondary_evaluator?.id ?? "",
  };
}

function isEditable(review) {
  return review.status !== "SUBMITTED";
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">평가자 지정</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div v-if="formError" class="alert alert-danger">{{ formError }}</div>

    <div class="row mb-3">
      <div class="col-md-4">
        <label class="form-label">평가 기간</label>
        <select v-model="selectedPeriodId" class="form-select" @change="loadReviews">
          <option v-for="period in periods" :key="period.id" :value="String(period.id)">
            {{ period.name }} ({{ periodStatusLabels[period.status] || period.status }})
          </option>
        </select>
      </div>
    </div>

    <div v-if="selectedPeriodId" class="card mb-4">
      <div class="card-body">
        <h2 class="h5">평가 대상자 추가</h2>
        <form class="row g-2 align-items-end" @submit.prevent="createReview">
          <div class="col-md-3">
            <label class="form-label">대상 직원</label>
            <select v-model="createForm.employee" class="form-select" required>
              <option value="" disabled>선택</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }} ({{ user.employee_number }})
              </option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label">1차 평가자</label>
            <select v-model="createForm.primary_evaluator" class="form-select" required>
              <option value="" disabled>선택</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }} ({{ user.employee_number }})
              </option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label">2차 평가자 (선택)</label>
            <select v-model="createForm.secondary_evaluator" class="form-select">
              <option value="">없음</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }} ({{ user.employee_number }})
              </option>
            </select>
          </div>
          <div class="col-md-2">
            <button class="btn btn-primary">추가</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="selectedPeriodId && reviews.length === 0" class="alert alert-info">
      이 기간에 등록된 평가가 없습니다.
    </div>
    <table v-if="selectedPeriodId && reviews.length" class="table align-middle">
      <thead>
        <tr>
          <th>대상 직원</th>
          <th>1차 평가자</th>
          <th>2차 평가자</th>
          <th>상태</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="review in reviews.map(editableCopy)" :key="review.id">
          <td>{{ review.employee.name }} ({{ review.employee.employee_number }})</td>
          <td>
            <select v-model="review._primary" class="form-select form-select-sm" :disabled="!isEditable(review)">
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }}
              </option>
            </select>
          </td>
          <td>
            <select v-model="review._secondary" class="form-select form-select-sm" :disabled="!isEditable(review)">
              <option value="">없음</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }}
              </option>
            </select>
          </td>
          <td>{{ statusLabels[review.status] }}</td>
          <td class="text-end">
            <button
              v-if="isEditable(review)"
              class="btn btn-outline-primary btn-sm"
              @click="saveEvaluators({ ...review, primary_evaluator: { id: review._primary }, secondary_evaluator: review._secondary ? { id: review._secondary } : null })"
            >
              평가자 저장
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
