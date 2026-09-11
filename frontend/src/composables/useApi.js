import { ref } from "vue";
import { formatError } from "../api/client";

export function useApi() {
  const loading = ref(false);
  const error = ref("");

  async function run(request) {
    loading.value = true;
    error.value = "";
    try {
      return await request();
    } catch (err) {
      error.value = formatError(err);
      return null;
    } finally {
      loading.value = false;
    }
  }

  return { loading, error, run };
}
