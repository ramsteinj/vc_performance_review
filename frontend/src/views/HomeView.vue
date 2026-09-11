<script setup>
import { onMounted, ref } from "vue";
import client from "../api/client";
import { useApi } from "../composables/useApi";

const { loading, error, run } = useApi();
const reviews = ref([]);

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

onMounted(async () => {
  const response = await run(() => client.get("/reviews/my/"));
  if (response) {
    reviews.value = response.data;
  }
});
</script>

<template>
  <h1 class="h3 mb-4">내 평가</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <div v-else-if="reviews.length === 0" class="alert alert-info">
    진행 중인 평가가 없습니다.
  </div>
  <table v-else class="table align-middle">
    <thead>
      <tr>
        <th>평가 기간</th>
        <th>기간</th>
        <th>상태</th>
        <th style="width: 30%">진행률</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="review in reviews" :key="review.id">
        <td>{{ review.review_period.name }}</td>
        <td>
          {{ review.review_period.start_date }} ~
          {{ review.review_period.end_date }}
        </td>
        <td>
          <span class="badge" :class="statusClasses[review.status]">
            {{ statusLabels[review.status] || review.status }}
          </span>
        </td>
        <td>
          <div class="progress">
            <div
              class="progress-bar"
              :style="{ width: review.progress + '%' }"
            >
              {{ review.progress }}%
            </div>
          </div>
        </td>
        <td class="text-end">
          <router-link
            class="btn btn-primary btn-sm"
            :to="`/review?review=${review.id}`"
          >
            {{ review.status === "SUBMITTED" ? "제출 내용 보기" : "평가하기" }}
          </router-link>
        </td>
      </tr>
    </tbody>
  </table>
</template>
