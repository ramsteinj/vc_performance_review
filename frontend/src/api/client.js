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

export function formatError(err) {
  const data = err.response?.data;
  if (!data) return err.message || "요청에 실패했습니다.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
    .join("\n");
}

export default client;
