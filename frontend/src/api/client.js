import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

function getCookie(name) {
  const match = document.cookie.match(
    new RegExp("(^|;\\s*)" + name + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[2]) : null;
}

client.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const token = getCookie("csrftoken");
    if (token) {
      config.headers["X-CSRFToken"] = token;
    }
  }
  return config;
});

const periodStatusLabels = {
  DRAFT: "준비",
  OPEN: "진행 중",
  CLOSED: "종료",
};

const fieldLabels = {
  employee_number: "사번",
  name: "이름",
  username: "아이디",
  password: "비밀번호",
  department: "부서",
  role: "권한",
  is_active: "활성 여부",
  review_period: "평가 기간",
  employee: "직원",
  primary_evaluator: "1차 평가자",
  secondary_evaluator: "2차 평가자",
  start_date: "시작일",
  end_date: "종료일",
  status: "상태",
  text: "문항 내용",
  description: "설명",
  question_type: "문항 유형",
  weight: "가중치",
  display_order: "순서",
  required: "필수 여부",
  question: "문항",
  answers: "답변",
  score: "점수",
  performance_score: "부서 성과 점수",
  detail: "내용",
};

const exactMessages = {
  "invalid credentials": "이름, 사번 또는 비밀번호가 올바르지 않습니다.",
  "inactive user": "비활성화된 계정입니다. 관리자에게 문의하세요.",
  "start_date must be on or before end_date": "시작일은 종료일 이전이어야 합니다.",
  "review_period cannot be changed": "평가 기간은 변경할 수 없습니다.",
  "review already exists": "이미 등록된 평가입니다.",
  "submitted review cannot be modified": "제출된 평가는 수정할 수 없습니다.",
  "review period is not open": "평가 기간이 진행 중이 아니어서 저장할 수 없습니다.",
  "question does not belong to this review period": "이 평가 기간의 문항이 아닙니다.",
  "question is not active": "비활성화된 문항은 응답할 수 없습니다.",
  "all required questions must be answered": "필수 문항에 모두 응답해야 제출할 수 있습니다.",
  "review is already submitted": "이미 제출된 평가입니다.",
  "choices must belong to the question": "선택지가 해당 문항에 속하지 않습니다.",
  "only one choice is allowed for SINGLE_CHOICE": "단일 선택 문항은 하나의 선택지만 고를 수 있습니다.",
  "choices are only allowed for choice-type questions": "선택지는 선택형 문항에만 추가할 수 있습니다.",
  "no scorable answers for this review": "채점 가능한 답변이 없습니다.",
  "department performance score is not entered": "부서 성과 점수가 입력되지 않아 점수를 계산할 수 없습니다.",
  "evaluator must be an active user": "평가자는 활성 상태인 사용자여야 합니다.",
  "employee cannot be their own evaluator": "본인을 평가자로 지정할 수 없습니다.",
  "primary_evaluator is required": "1차 평가자는 필수입니다.",
  "cannot change evaluators after submission": "제출 후에는 평가자를 변경할 수 없습니다.",
  "This field is required.": "이 필드는 필수입니다.",
  "This field may not be blank.": "이 필드는 비워 둘 수 없습니다.",
  "This field may not be null.": "이 필드는 필수입니다.",
  "A valid integer is required.": "정수를 입력해 주세요.",
  "A valid number is required.": "숫자를 입력해 주세요.",
  "Enter a valid value.": "올바른 값을 입력해 주세요.",
  "Network Error": "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
};

const patternMessages = [
  {
    test: /^questions can only be modified while the period is DRAFT \(current status: (\w+)\)$/,
    translate: (m) =>
      `문항은 평가 기간이 준비 상태일 때만 수정할 수 있습니다. (현재 상태: ${periodStatusLabels[m[1]] || m[1]})`,
  },
  {
    test: /^cannot change status from (\w+) to (\w+)$/,
    translate: (m) =>
      `평가 기간 상태를 ${periodStatusLabels[m[1]] || m[1]}에서 ${periodStatusLabels[m[2]] || m[2]}(으)로 변경할 수 없습니다.`,
  },
  {
    test: /^active question weight total must be (\d+), got (\d+)$/,
    translate: (m) => `활성 문항 가중치 합계는 ${m[1]}이어야 합니다. (현재: ${m[2]})`,
  },
  {
    test: /^unknown question fields: (.+)$/,
    translate: () => "문항에 알 수 없는 필드가 포함되어 있습니다.",
  },
  {
    test: /^Invalid pk "?.*"? - object does not exist\.$/,
    translate: () => "존재하지 않는 항목이 지정되었습니다.",
  },
  {
    test: /^Date has wrong format\..*$/,
    translate: () => "올바른 날짜 형식이 아닙니다.",
  },
  {
    test: /^Ensure this value .+$/,
    translate: () => "값의 범위가 올바르지 않습니다.",
  },
  {
    test: /^Request failed with status code (\d+)$/,
    translate: (m) => `요청이 실패했습니다. (오류 코드 ${m[1]})`,
  },
];

function translateMessage(message) {
  if (typeof message !== "string") return message;
  if (exactMessages[message]) return exactMessages[message];
  for (const { test, translate } of patternMessages) {
    const match = message.match(test);
    if (match) return translate(match);
  }
  return message;
}

function translateValue(value) {
  if (Array.isArray(value)) return value.map(translateValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, translateValue(item)])
    );
  }
  return translateMessage(value);
}

export function formatError(err) {
  const data = err.response?.data;
  if (!data) return translateMessage(err.message) || "요청에 실패했습니다.";
  if (typeof data === "string") return translateMessage(data);
  if (data.detail) return translateValue(data.detail);
  return Object.entries(data)
    .map(([key, value]) => {
      const label = fieldLabels[key] || key;
      const translated = translateValue(value);
      return `${label}: ${Array.isArray(translated) ? translated.join(", ") : translated}`;
    })
    .join("\n");
}

export default client;
