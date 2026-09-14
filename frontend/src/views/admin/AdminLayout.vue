<template>
  <div class="row">
    <div class="col-md-2 mb-3">
      <nav class="sidebar-nexora">
        <router-link class="sidebar-link" to="/admin" exact-active-class="active">
          대시보드
        </router-link>
        <router-link class="sidebar-link" to="/admin/users" active-class="active">
          사용자
        </router-link>
        <router-link class="sidebar-link" to="/admin/departments" active-class="active">
          부서
        </router-link>
        <router-link class="sidebar-link" to="/admin/review-periods" active-class="active">
          평가 기간
        </router-link>
        <router-link class="sidebar-link" to="/admin/questions" active-class="active">
          문항
        </router-link>
        <router-link class="sidebar-link" to="/admin/evaluators" active-class="active">
          평가자
        </router-link>
        <router-link class="sidebar-link" to="/admin/monitoring" active-class="active">
          모니터링
        </router-link>
        <router-link class="sidebar-link" to="/admin/scores" active-class="active">
          점수
        </router-link>
      </nav>
    </div>
    <div class="col-md-10">
      <router-view />
    </div>
  </div>
</template>
