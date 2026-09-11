# 01. 시스템 개요

## 목표
직원 평가 응답을 수집하고 관리자가 평가 문항, 평가자, 응답 상태 및 점수를 관리할 수 있는 SPA 기반 시스템을 구축한다.

## 사용자 역할
- EMPLOYEE
- ADMIN

## 주요 기능
### 직원
1. 로그인
2. 평가 조회
3. 문항 응답
4. 임시 저장
5. 진행률 확인
6. 제출
7. 제출 후 수정 차단

### 관리자
1. 사용자 관리
2. 부서 관리
3. 평가 기간 관리
4. 문항 관리
5. 가중치 관리
6. 평가자 지정
7. 응답 모니터링
8. CSV export
9. 부서 성과 점수
10. 최종 점수 계산

## 아키텍처
```text
Vue 3 SPA
   ↓ HTTP/JSON
Django REST Framework
   ↓
Django Service / ORM
   ↓
PostgreSQL
```

## 인증 모델
Django `AbstractUser`를 상속한 `accounts.User` 하나만 사용한다.
Employee/Admin은 별도 테이블이 아니라 `User.role`로 구분한다.
