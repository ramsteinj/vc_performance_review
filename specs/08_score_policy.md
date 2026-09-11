# 08. 점수 정책

## 1. 개인 점수
각 점수를 0~100으로 normalize한 뒤 가중 평균한다.

```text
individual_score =
    SUM(normalized_question_score * question_weight)
    / SUM(question_weight)
```

문항 가중치 합계가 100이면:
```text
individual_score = SUM(normalized_score * weight) / 100
```

## 2. SCALE
기본 1~5:
```text
normalized = (answer - 1) / 4 * 100
```

## 3. TEXT
MVP에서는 자동 점수에서 제외한다.
향후 평가자 채점 기능을 추가할 수 있다.

## 4. 부서 성과
DepartmentPerformance.performance_score는 0~100.

## 5. 부서 조정
MVP 기본 예시:
```text
department_adjustment = (department_score - 70) * 0.20
```

예:
- 부서 70 → 0
- 부서 80 → +2
- 부서 60 → -2

## 6. 최종 점수
```text
final_score = individual_score + department_adjustment
final_score = max(0, min(100, final_score))
```

## 7. 중요
위 조정 기준 70과 20%는 예시 기본 정책이다.
실제 운영 전 회사의 평가 정책에 맞춰 configurable policy로 확정한다.

## 8. 구현
점수 계산은 View에 직접 구현하지 않는다.
예:
`scoring/services.py`
- calculate_individual_score()
- calculate_department_adjustment()
- calculate_final_score()
