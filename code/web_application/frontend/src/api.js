import axios from "axios";


export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

async function request(path, options = {}) {
  try {
    const response = await apiClient.request({ url: path, ...options });
    return response.status === 204 ? null : response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join("; "));
    }
    throw new Error(detail || error.message || "Request failed");
  }
}

export const authApi = {
  login(email, password) {
    return request("/auth/login", {
      method: "POST",
      data: { email, password },
    });
  },
  me() {
    return request("/auth/me");
  },
  logout() {
    return request("/auth/logout", { method: "POST" });
  },
};

export const recallsApi = {
  async list(query = "") {
    const params = new URLSearchParams({ page_size: "50" });
    if (query.trim()) params.set("q", query.trim());
    const body = await request(`/recalls?${params.toString()}`);
    return body.records;
  },
  get(id) {
    return request(`/recalls/${id}`);
  },
  create(payload) {
    return request("/recalls", {
      method: "POST",
      data: payload,
    });
  },
  update(id, payload) {
    return request(`/recalls/${id}`, {
      method: "PUT",
      data: payload,
    });
  },
  remove(id) {
    return request(`/recalls/${id}`, { method: "DELETE" });
  },
};

export const manufacturersApi = {
  list() {
    return request("/manufacturers?skip=0&limit=200");
  },
};
