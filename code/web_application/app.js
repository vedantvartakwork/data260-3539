"use strict";

const API_URL = "/api/recalls";
const state = { mode: "create", query: "" };

const elements = {
  list: document.getElementById("recallList"),
  loading: document.getElementById("loadingState"),
  empty: document.getElementById("emptyState"),
  error: document.getElementById("errorState"),
  errorText: document.getElementById("errorText"),
  count: document.getElementById("recordCount"),
  form: document.getElementById("recallForm"),
  formStatus: document.getElementById("formStatus"),
  submit: document.getElementById("submitButton"),
  searchForm: document.getElementById("searchForm"),
  searchInput: document.getElementById("searchInput"),
};

function setListState(name, message = "") {
  elements.loading.hidden = name !== "loading";
  elements.empty.hidden = name !== "empty";
  elements.error.hidden = name !== "error";
  elements.list.hidden = name !== "ready";
  if (message) elements.errorText.textContent = message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderRecalls(records) {
  elements.count.textContent = `${records.length} ${records.length === 1 ? "record" : "records"}`;
  if (records.length === 0) {
    elements.list.replaceChildren();
    setListState("empty");
    return;
  }

  elements.list.innerHTML = records
    .map(
      (record) => `
        <article class="recall-card">
          <header>
            <h3>#${record.id} · ${escapeHtml(record.productName)}</h3>
            <span class="meta">${escapeHtml(record.category)}</span>
          </header>
          <p class="meta">${escapeHtml(record.brandName)}</p>
          <p>${escapeHtml(record.recallDetails)}</p>
        </article>`,
    )
    .join("");
  setListState("ready");
}

async function readError(response) {
  try {
    const body = await response.json();
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg).join("; ");
    }
    return body.detail || `Request failed with HTTP ${response.status}`;
  } catch {
    return `Request failed with HTTP ${response.status}`;
  }
}

async function loadRecalls(query = state.query) {
  state.query = query;
  setListState("loading");
  try {
    const url = query ? `${API_URL}?q=${encodeURIComponent(query)}` : API_URL;
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(await readError(response));
    renderRecalls(await response.json());
  } catch (error) {
    elements.count.textContent = "Unavailable";
    setListState("error", error.message);
  }
}

function formPayload() {
  return {
    productName: document.getElementById("productName").value.trim(),
    brandName: document.getElementById("brandName").value.trim(),
    submitterEmail: document.getElementById("submitterEmail").value.trim(),
    recallDetails: document.getElementById("recallDetails").value.trim(),
    category: document.getElementById("category").value,
    termsAccepted: document.getElementById("termsAccepted").checked,
  };
}

function setFormMessage(message, isError = false) {
  elements.formStatus.textContent = message;
  elements.formStatus.classList.toggle("error", isError);
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.form.checkValidity()) {
    elements.form.reportValidity();
    return;
  }

  const payload = formPayload();
  if (payload.recallDetails.length <= 25) {
    setFormMessage("Recall details must be longer than 25 characters.", true);
    return;
  }
  if (!payload.termsAccepted) {
    setFormMessage("You must agree to the terms and conditions.", true);
    return;
  }

  const updating = state.mode === "update";
  elements.submit.disabled = true;
  elements.submit.textContent = updating ? "Updating…" : "Adding…";
  setFormMessage("");

  try {
    const response = await fetch(updating ? `${API_URL}/1` : API_URL, {
      method: updating ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await readError(response));
    const record = await response.json();
    setFormMessage(`${updating ? "Updated" : "Added"} recall ID ${record.id} successfully.`);
    elements.form.reset();
    state.mode = "create";
    elements.submit.textContent = "Add recall notice";
    await loadRecalls("");
  } catch (error) {
    setFormMessage(error.message, true);
  } finally {
    elements.submit.disabled = false;
    if (state.mode === "create") elements.submit.textContent = "Add recall notice";
  }
});

document.getElementById("updateMode").addEventListener("click", async () => {
  setFormMessage("Loading recall ID 1…");
  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error(await readError(response));
    const record = (await response.json()).find((item) => item.id === 1);
    if (!record) throw new Error("Recall ID 1 was not found.");

    for (const field of ["productName", "brandName", "submitterEmail", "recallDetails", "category"]) {
      document.getElementById(field).value = record[field];
    }
    document.getElementById("termsAccepted").checked = record.termsAccepted;
    state.mode = "update";
    elements.submit.textContent = "Update recall ID 1";
    setFormMessage("Edit the values below, then update recall ID 1.");
    document.getElementById("productName").focus();
  } catch (error) {
    setFormMessage(error.message, true);
  }
});

document.getElementById("deleteHighest").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const response = await fetch(`${API_URL}/highest`, { method: "DELETE" });
    if (!response.ok) throw new Error(await readError(response));
    const body = await response.json();
    setFormMessage(`Deleted highest recall ID ${body.deleted.id}.`);
    await loadRecalls("");
  } catch (error) {
    setFormMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
});

elements.searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadRecalls(elements.searchInput.value.trim());
});

document.getElementById("clearSearch").addEventListener("click", () => {
  elements.searchInput.value = "";
  loadRecalls("");
});

const demoState = new URLSearchParams(window.location.search).get("demo");
if (demoState === "loading") {
  setListState("loading");
} else if (demoState === "error") {
  elements.count.textContent = "Unavailable";
  setListState("error", "The API request failed. Please try again.");
} else {
  if (demoState === "create") {
    document.getElementById("productName").value = "Crispy Oat Bars";
    document.getElementById("brandName").value = "Sunny Pantry";
    document.getElementById("submitterEmail").value = "safety@example.edu";
    document.getElementById("recallDetails").value =
      "Selected boxes may contain undeclared peanuts and should be returned for a refund.";
    document.getElementById("category").value = "Packaged Foods";
    document.getElementById("termsAccepted").checked = true;
  }

  if (demoState === "update") {
    document.getElementById("productName").value = "Valley Harvest Baby Spinach 8 oz";
    document.getElementById("brandName").value = "Valley Harvest Organics";
    document.getElementById("submitterEmail").value = "updates@example.edu";
    document.getElementById("recallDetails").value =
      "Updated notice: lot VH0826 may contain undeclared almonds and must be returned.";
    document.getElementById("category").value = "Produce";
    document.getElementById("termsAccepted").checked = true;
    state.mode = "update";
    elements.submit.textContent = "Update recall ID 1";
  }

  loadRecalls();
}
