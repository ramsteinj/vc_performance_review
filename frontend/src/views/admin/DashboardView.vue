<script setup>
import { onMounted, ref } from "vue";
import client from "../../api/client";
import { useApi } from "../../composables/useApi";

const { loading, error, run } = useApi();
const summary = ref(null);

onMounted(async () => {
  const response = await run(() => client.get("/admin/monitoring/summary/"));
  if (response) {
    summary.value = response.data;
  }
});
</script>

<template>
  <h1 class="h3 mb-4">대시보드</h1>
  <div v-if="loading" class="text-muted">불러오는 중...</div>
  <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
  <template v-else-if="summary">
    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="fs-3">{{ summary.total }}</div>
            <div class="text-muted">전체 대상자</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="fs-3">{{ summary.not_started }}</div>
            <div class="text-muted">미응답</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="fs-3">{{ summary.in_progress }}</div>
            <div class="text-muted">작성 중</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="fs-3">{{ summary.submitted }}</div>
            <div class="text-muted">제출 완료</div>
          </div>
        </div>
      </div>
    </div>
    <div class="alert alert-primary">전체 응답률: {{ summary.response_rate }}%</div>

    <h2 class="h5">부서별 응답률</h2>
    <table v-if="summary.by_department.length" class="table">
      <thead>
        <tr>
          <th>부서</th>
          <th>대상자</th>
          <th>제출</th>
          <th>응답률</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in summary.by_department" :key="row.department_id">
          <td>{{ row.department || "(부서 없음)" }}</td>
          <td>{{ row.total }}</td>
          <td>{{ row.submitted }}</td>
          <td>{{ row.response_rate }}%</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="text-muted">데이터가 없습니다.</div>
  </template>
</template>
