<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import client, { formatError } from "../../api/client";
import { periodStatusLabels } from "../../utils/labels";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const periods = ref([]);
const questions = ref([]);
const selectedPeriodId = ref("");
const formError = ref("");
const choiceInput = reactive({ questionId: null, text: "", score: "" });

const form = reactive({
  id: null,
  text: "",
  description: "",
  question_type: "SCALE",
  weight: 10,
  display_order: 0,
  required: true,
});

const typeLabels = {
  TEXT: "서술형",
  SINGLE_CHOICE: "단일 선택",
  MULTIPLE_CHOICE: "복수 선택",
  SCALE: "점수형",
};

const selectedPeriod = computed(() =>
  periods.value.find((p) => String(p.id) === String(selectedPeriodId.value))
);

const periodQuestions = computed(() =>
  questions.value.filter(
    (q) => String(q.review_period) === String(selectedPeriodId.value)
  )
);

const activeWeightTotal = computed(() =>
  periodQuestions.value
    .filter((q) => q.is_active)
    .reduce((sum, q) => sum + q.weight, 0)
);

async function load() {
  const [periodsResponse, questionsResponse] = await Promise.all([
    run(() => client.get("/admin/review-periods/")),
    run(() => client.get("/admin/questions/")),
  ]);
  if (periodsResponse) {
    periods.value = periodsResponse.data;
    if (!selectedPeriodId.value && periods.value.length) {
      selectedPeriodId.value = String(periods.value[0].id);
    }
  }
  if (questionsResponse) questions.value = questionsResponse.data;
}

function resetForm() {
  Object.assign(form, {
    id: null,
    text: "",
    description: "",
    question_type: "SCALE",
    weight: 10,
    display_order: periodQuestions.value.length + 1,
    required: true,
  });
  formError.value = "";
}

function editQuestion(question) {
  Object.assign(form, {
    id: question.id,
    text: question.text,
    description: question.description,
    question_type: question.question_type,
    weight: question.weight,
    display_order: question.display_order,
    required: question.required,
  });
  formError.value = "";
}

async function submitForm() {
  formError.value = "";
  const payload = { ...form, review_period: Number(selectedPeriodId.value) };
  try {
    if (form.id) {
      await client.patch(`/admin/questions/${form.id}/`, payload);
    } else {
      await client.post("/admin/questions/", payload);
    }
    resetForm();
    await load();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function deactivateQuestion(question) {
  if (!confirm("문항을 비활성화하시겠습니까?")) return;
  await run(() =>
    client.patch(`/admin/questions/${question.id}/`, { is_active: false })
  );
  await load();
}

async function activateQuestion(question) {
  if (!confirm("문항을 활성화하시겠습니까?")) return;
  await run(() =>
    client.patch(`/admin/questions/${question.id}/`, { is_active: true })
  );
  await load();
}

async function deleteQuestion(question) {
  if (!confirm("문항을 삭제하시겠습니까? 삭제한 문항은 복구할 수 없습니다.")) return;
  await run(() => client.delete(`/admin/questions/${question.id}/`));
  await load();
}

function isChoiceType(question) {
  return ["SINGLE_CHOICE", "MULTIPLE_CHOICE"].includes(question.question_type);
}

async function addChoice(question) {
  formError.value = "";
  try {
    await client.post(`/admin/questions/${question.id}/choices/`, {
      text: choiceInput.text,
      score: choiceInput.score === "" ? null : Number(choiceInput.score),
    });
    choiceInput.questionId = null;
    choiceInput.text = "";
    choiceInput.score = "";
    await load();
  } catch (err) {
    formError.value = formatError(err);
  }
}

async function deleteChoice(question, choice) {
  if (!confirm(`선택지 "${choice.text}"를 삭제하시겠습니까?`)) return;
  await run(() =>
    client.delete(`/admin/questions/${question.id}/choices/${choice.id}/`)
  );
  await load();
}

onMounted(load);
</script>

<template>
  <h1 class="h3 mb-4">문항 관리</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else>
    <div class="row mb-3">
      <div class="col-md-4">
        <label class="form-label">평가 기간</label>
        <select v-model="selectedPeriodId" class="form-select">
          <option v-for="period in periods" :key="period.id" :value="String(period.id)">
            {{ period.name }} ({{ periodStatusLabels[period.status] || period.status }})
          </option>
        </select>
      </div>
      <div class="col-md-4 d-flex align-items-end">
        <div class="alert py-2 mb-0" :class="activeWeightTotal === 100 ? 'alert-success' : 'alert-warning'">
          활성 가중치 합계: {{ activeWeightTotal }} / 100
          <span v-if="selectedPeriod && selectedPeriod.status !== 'DRAFT'" class="d-block small">
            ({{ periodStatusLabels[selectedPeriod.status] || selectedPeriod.status }} 기간은 문항 수정이 제한됩니다)
          </span>
        </div>
      </div>
    </div>

    <div v-if="!selectedPeriodId" class="alert alert-info">평가 기간을 선택하세요.</div>
    <template v-else>
      <div class="card mb-4">
        <div class="card-body">
          <h2 class="h5">{{ form.id ? "문항 수정" : "문항 추가" }}</h2>
          <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
          <form class="row g-2" @submit.prevent="submitForm">
            <div class="col-md-6">
              <label class="form-label">문항 내용</label>
              <input v-model="form.text" class="form-control" required />
            </div>
            <div class="col-md-6">
              <label class="form-label">설명</label>
              <input v-model="form.description" class="form-control" />
            </div>
            <div class="col-md-2">
              <label class="form-label">유형</label>
              <select v-model="form.question_type" class="form-select">
                <option value="SCALE">점수형</option>
                <option value="TEXT">서술형</option>
                <option value="SINGLE_CHOICE">단일 선택</option>
                <option value="MULTIPLE_CHOICE">복수 선택</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">가중치</label>
              <input v-model.number="form.weight" type="number" min="0" class="form-control" required />
            </div>
            <div class="col-md-2">
              <label class="form-label">순서</label>
              <input v-model.number="form.display_order" type="number" min="0" class="form-control" />
            </div>
            <div class="col-md-2 form-check ms-2 align-self-end">
              <input v-model="form.required" class="form-check-input" type="checkbox" id="question-required" />
              <label class="form-check-label" for="question-required">필수</label>
            </div>
            <div class="col-md-3 d-flex gap-2 align-self-end">
              <button class="btn btn-primary">{{ form.id ? "수정" : "추가" }}</button>
              <button v-if="form.id" type="button" class="btn btn-secondary" @click="resetForm">취소</button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="periodQuestions.length === 0" class="alert alert-info">
        이 기간에 등록된 문항이 없습니다.
      </div>
      <div v-for="question in periodQuestions" :key="question.id" class="card mb-2">
        <div class="card-body py-3">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <strong>{{ question.text }}</strong>
              <span class="badge bg-secondary ms-2">{{ typeLabels[question.question_type] }}</span>
              <span v-if="question.required" class="badge bg-danger ms-1">필수</span>
              <span v-if="!question.is_active" class="badge bg-dark ms-1">비활성</span>
              <span class="text-muted small ms-2">
                가중치 {{ question.weight }} · 순서 {{ question.display_order }}
              </span>
            </div>
            <div v-if="selectedPeriod.status === 'DRAFT'">
              <button class="btn btn-outline-primary btn-sm me-1" @click="editQuestion(question)">수정</button>
              <button v-if="question.is_active" class="btn btn-outline-secondary btn-sm me-1" @click="deactivateQuestion(question)">
                비활성화
              </button>
              <button v-else class="btn btn-outline-success btn-sm me-1" @click="activateQuestion(question)">
                활성화
              </button>
              <button class="btn btn-outline-danger btn-sm" @click="deleteQuestion(question)">
                삭제
              </button>
            </div>
          </div>
          <p v-if="question.description" class="text-muted small mb-1">{{ question.description }}</p>

          <div v-if="isChoiceType(question)" class="mt-2">
            <span
              v-for="choice in question.choices"
              :key="choice.id"
              class="badge bg-light text-dark border me-1"
            >
              {{ choice.text }}
              <span v-if="choice.score !== null">({{ choice.score }})</span>
              <button
                v-if="selectedPeriod.status === 'DRAFT'"
                class="btn btn-link btn-sm p-0 text-danger ms-1"
                @click="deleteChoice(question, choice)"
              >✕</button>
            </span>
            <form
              v-if="selectedPeriod.status === 'DRAFT'"
              class="d-flex gap-1 align-items-center mt-2"
              @submit.prevent="addChoice(question)"
            >
              <input
                v-model="choiceInput.text"
                class="form-control form-control-sm"
                style="max-width: 200px"
                placeholder="선택지"
                required
              />
              <input
                v-model="choiceInput.score"
                class="form-control form-control-sm"
                style="max-width: 80px"
                type="number"
                placeholder="점수"
              />
              <button class="btn btn-outline-secondary btn-sm">선택지 추가</button>
            </form>
          </div>
        </div>
      </div>
    </template>
  </template>
</template>
