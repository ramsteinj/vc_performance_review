import { reactive } from "vue";
import client from "../api/client";

const state = reactive({ user: null, loaded: false });

export function useAuth() {
  async function fetchMe() {
    try {
      const response = await client.get("/auth/me/");
      state.user = response.data;
    } catch {
      state.user = null;
    } finally {
      state.loaded = true;
    }
    return state.user;
  }

  async function login(payload) {
    const response = await client.post("/auth/login/", payload);
    state.user = response.data;
    return state.user;
  }

  async function logout() {
    try {
      await client.post("/auth/logout/");
    } finally {
      state.user = null;
    }
  }

  return { state, fetchMe, login, logout };
}
