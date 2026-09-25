const API_ROOT = "/api/v1";

async function request(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }
  return body;
}

export const authApi = {
  login(email, password) {
    return request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
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
      body: JSON.stringify(payload),
    });
  },
  update(id, payload) {
    return request(`/recalls/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  remove(id) {
    return request(`/recalls/${id}`, { method: "DELETE" });
  },
};
