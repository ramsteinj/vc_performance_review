<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import client from "../api/client";
import { useApi } from "../composables/useApi";

const route = useRoute();
const { loading, error, run } = useApi();

const review = ref(null);
const questions = ref([]);
const answers = reactive({});
const progress = ref(0);
const saving = ref(false);
const saveMessage = ref("");
const saveError = ref("");
const submitError = ref("");

const typeLabels = {
  TEXT: "서술형",
  SINGLE_CHOICE: "단일 선택",
  MULTIPLE_CHOICE: "복수 선택",
  SCALE: "점수형 (1~5)",
};

const submitted = computed(() => review.value?.status === "SUBMITTED");

onMounted(load);

async function load() {
  const myList = await run(() => client.get("/reviews/my/"));
  if (!myList) return;
  const requestedId = route.query.review;
  const target = requestedId
    ? myList.data.find((r) => String(r.id) === String(requestedId))
    : myList.data[0];
  if (!target) {
    error.value = "평가를 찾을 수 없습니다.";
    return;
  }
  const detail = await run(() => client.get(`/reviews/${target.id}/`));
  if (!detail) return;
  review.value = detail.data;
  questions.value = detail.data.questions;
  progress.value = detail.data.progress;
  for (const question of questions.value) {
    const existing = detail.data.answers.find((a) => a.question === question.id);
    answers[question.id] = {
      answer_text: existing?.answer_text || "",
      score: existing?.score ?? null,
      choice_ids: existing ? existing.selected_choices.map((c) => c.id) : [],
    };
  }
}

function toggleChoice(question, choiceId) {
  const current = answers[question.id].choice_ids;
  if (question.question_type === "SINGLE_CHOICE") {
    answers[question.id].choice_ids = [choiceId];
    return;
  }
  const index = current.indexOf(choiceId);
  if (index >= 0) {
    current.splice(index, 1);
  } else {
    current.push(choiceId);
  }
}

function choiceTexts(question) {
  const ids = answers[question.id]?.choice_ids || [];
  return question.choices
    .filter((c) => ids.includes(c.id))
    .map((c) => c.text)
    .join(", ") || "-";
}

async function saveDraft() {
  saving.value = true;
  saveMessage.value = "";
  saveError.value = "";
  try {
    const payload = {
      answers: questions.value.map((question) => ({
        question: question.id,
        answer_text: answers[question.id].answer_text,
        score: answers[question.id].score,
        choice_ids: answers[question.id].choice_ids,
      })),
    };
    const response = await client.put(
      `/reviews/${review.value.id}/answers/`,
      payload
    );
    progress.value = response.data.progress;
    review.value.status = response.data.status;
    saveMessage.value = "임시 저장되었습니다.";
  } catch (err) {
    saveError.value = err.response?.data?.detail || "저장에 실패했습니다.";
  } finally {
    saving.value = false;
  }
}

async function submitReview() {
  submitError.value = "";
  if (!confirm("제출하면 수정할 수 없습니다. 제출하시겠습니까?")) return;
  try {
    const response = await client.post(
      `/reviews/${review.value.id}/submit/`
    );
    review.value.status = response.data.status;
    review.value.submitted_at = response.data.submitted_at;
  } catch (err) {
    submitError.value = err.response?.data?.detail || "제출에 실패했습니다.";
  }
}
</script>

<template>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else-if="review">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h1 class="h3 mb-0">{{ review.review_period.name }}</h1>
      <span
        class="badge"
        :class="submitted ? 'bg-success' : 'bg-warning text-dark'"
      >
        {{ submitted ? "제출 완료" : "작성 중" }}
      </span>
    </div>
    <p class="text-muted">
      기간: {{ review.review_period.start_date }} ~
      {{ review.review_period.end_date }}
    </p>

    <div class="progress mb-4" style="height: 24px">
      <div class="progress-bar" :style="{ width: progress + '%' }">
        {{ progress }}%
      </div>
    </div>

    <div v-if="submitted" class="alert alert-success">
      제출이 완료되었습니다. 제출 후에는 수정할 수 없습니다.
    </div>
    <template v-else>
      <div v-if="saveMessage" class="alert alert-success">{{ saveMessage }}</div>
      <div v-if="saveError" class="alert alert-danger">{{ saveError }}</div>
    </template>
    <div v-if="submitError" class="alert alert-danger">{{ submitError }}</div>

    <div class="alert alert-info py-2">
      각 문항은 <strong>1~5점</strong>으로 평가합니다. 문항별 가중치가 높을수록
      최종 점수에 더 크게 반영됩니다 (가중 평균).
    </div>

    <div v-for="question in questions" :key="question.id" class="card mb-3">
      <div class="card-body">
        <h2 class="h6">
          {{ question.text }}
          <span v-if="question.required" class="badge bg-danger">필수</span>
          <span class="badge bg-secondary">{{ typeLabels[question.question_type] }}</span>
          <span
            class="badge bg-primary"
            :title="'가중치가 높을수록 최종 점수 반영 비율이 커집니다'"
          >가중치 {{ question.weight }}</span>
        </h2>
        <p v-if="question.description" class="text-muted small mb-2">
          {{ question.description }}
        </p>

        <template v-if="!submitted">
          <textarea
            v-if="question.question_type === 'TEXT'"
            v-model="answers[question.id].answer_text"
            class="form-control"
            rows="3"
          ></textarea>

          <div
            v-else-if="question.question_type === 'SCALE'"
            class="btn-group"
            role="group"
          >
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              class="btn"
              :class="answers[question.id].score === n ? 'btn-primary' : 'btn-outline-primary'"
              @click="answers[question.id].score = n"
            >
              {{ n }}
            </button>
          </div>

          <div v-else>
            <div
              v-for="choice in question.choices"
              :key="choice.id"
              class="form-check"
            >
              <input
                class="form-check-input"
                :type="question.question_type === 'SINGLE_CHOICE' ? 'radio' : 'checkbox'"
                :name="`question-${question.id}`"
                :id="`choice-${choice.id}`"
                :checked="answers[question.id].choice_ids.includes(choice.id)"
                @change="toggleChoice(question, choice.id)"
              />
              <label class="form-check-label" :for="`choice-${choice.id}`">
                {{ choice.text }}
              </label>
            </div>
          </div>
        </template>

        <div v-else class="border rounded p-2 bg-light">
          <p v-if="question.question_type === 'TEXT'" class="mb-0">
            {{ answers[question.id].answer_text || "-" }}
          </p>
          <p v-else-if="question.question_type === 'SCALE'" class="mb-0">
            선택: {{ answers[question.id].score ?? "-" }} / 5
          </p>
          <p v-else class="mb-0">{{ choiceTexts(question) }}</p>
        </div>
      </div>
    </div>

    <div v-if="!submitted" class="d-flex gap-2 mb-5">
      <button class="btn btn-secondary" :disabled="saving" @click="saveDraft">
        {{ saving ? "저장 중..." : "임시 저장" }}
      </button>
      <button class="btn btn-primary" :disabled="saving" @click="submitReview">
        제출
      </button>
    </div>
  </template>
</template>
