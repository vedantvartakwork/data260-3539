import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function makeElement(initial = {}) {
  const listeners = {};
  const classes = new Set();
  return {
    value: "",
    checked: false,
    disabled: false,
    hidden: false,
    textContent: "",
    innerHTML: "",
    ...initial,
    addEventListener(name, handler) {
      listeners[name] = handler;
    },
    listener(name) {
      return listeners[name];
    },
    classList: {
      toggle(name, enabled) {
        if (enabled) classes.add(name);
        else classes.delete(name);
      },
      contains(name) {
        return classes.has(name);
      },
    },
    replaceChildren() {
      this.innerHTML = "";
    },
    focus() {},
  };
}

const elements = {
  recallList: makeElement(),
  loadingState: makeElement(),
  emptyState: makeElement(),
  errorState: makeElement(),
  errorText: makeElement(),
  recordCount: makeElement(),
  formStatus: makeElement(),
  submitButton: makeElement({ textContent: "Add recall notice" }),
  searchForm: makeElement(),
  searchInput: makeElement(),
  updateMode: makeElement(),
  deleteHighest: makeElement(),
  clearSearch: makeElement(),
  productName: makeElement({ value: "Garden Fresh Spinach 10 oz" }),
  brandName: makeElement({ value: "Valley Harvest" }),
  submitterEmail: makeElement({ value: "recalls@example.edu" }),
  recallDetails: makeElement({ value: "short" }),
  category: makeElement({ value: "Produce" }),
  termsAccepted: makeElement({ checked: false }),
};

const form = makeElement();
form.checkValidity = () => true;
form.reportValidity = () => {};
form.reset = () => {
  for (const id of ["productName", "brandName", "submitterEmail", "recallDetails", "category"]) {
    elements[id].value = "";
  }
  elements.termsAccepted.checked = false;
};
elements.recallForm = form;

const document = {
  getElementById(id) {
    return elements[id];
  },
};

const fetchCalls = [];
const responses = [];
async function fetch(url, options = {}) {
  fetchCalls.push({ url, options });
  const response = responses.shift();
  assert.ok(response, `Unexpected fetch request: ${url}`);
  return response;
}

function jsonResponse(body) {
  return {
    ok: true,
    status: 200,
    async json() {
      return body;
    },
  };
}

const context = {
  document,
  fetch,
  URLSearchParams,
  window: { location: { search: "?demo=loading" } },
  console,
  encodeURIComponent,
};
vm.runInNewContext(fs.readFileSync("app.js", "utf8"), context);

const submit = () => form.listener("submit")({ preventDefault() {}, currentTarget: form });

await submit();
assert.equal(elements.formStatus.textContent, "Recall details must be longer than 25 characters.");
assert.equal(elements.formStatus.classList.contains("error"), true);
assert.equal(fetchCalls.length, 0, "short content must not reach the API");

elements.recallDetails.value =
  "Affected bags may contain undeclared almonds and should be returned.";
await submit();
assert.equal(elements.formStatus.textContent, "You must agree to the terms and conditions.");
assert.equal(elements.formStatus.classList.contains("error"), true);
assert.equal(fetchCalls.length, 0, "unchecked terms must not reach the API");

elements.termsAccepted.checked = true;
const createdRecord = {
  id: 3,
  productName: elements.productName.value,
  brandName: elements.brandName.value,
  submitterEmail: elements.submitterEmail.value,
  recallDetails: elements.recallDetails.value,
  category: elements.category.value,
  termsAccepted: true,
};
responses.push(jsonResponse(createdRecord), jsonResponse([createdRecord]));
await submit();

assert.equal(fetchCalls.length, 2);
assert.equal(fetchCalls[0].url, "/api/recalls");
assert.equal(fetchCalls[0].options.method, "POST");
assert.equal(JSON.parse(fetchCalls[0].options.body).productName, "Garden Fresh Spinach 10 oz");
assert.equal(elements.formStatus.textContent, "Added recall ID 3 successfully.");
assert.equal(elements.formStatus.classList.contains("error"), false);
assert.equal(elements.recordCount.textContent, "1 record");
assert.match(elements.recallList.innerHTML, /Garden Fresh Spinach 10 oz/);

console.log("JavaScript form tests passed: short content, unchecked terms, and valid API submission.");
