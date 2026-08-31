import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const elements = {
  productName: { value: "Garden Fresh Spinach 10 oz" },
  brandName: { value: "Valley Harvest" },
  submitterEmail: { value: "recalls@example.edu" },
  recallDetails: { value: "short" },
  category: { value: "Produce" },
  termsAccepted: { checked: false },
  statusMessage: { textContent: "" },
};

let submitHandler;
const form = {
  checkValidity: () => true,
  reportValidity: () => {},
  addEventListener: (name, handler) => {
    assert.equal(name, "submit");
    submitHandler = handler;
  },
};

const alerts = [];
const logs = [];
const document = {
  getElementById(id) {
    if (id === "recallForm") return form;
    return elements[id];
  },
};

class FakeFormData {
  *entries() {
    yield ["productName", elements.productName.value];
    yield ["brandName", elements.brandName.value];
    yield ["submitterEmail", elements.submitterEmail.value];
    yield ["recallDetails", elements.recallDetails.value];
    yield ["category", elements.category.value];
  }
}

const context = {
  document,
  FormData: FakeFormData,
  alert: (message) => alerts.push(message),
  console: { log: (...values) => logs.push(values) },
};
vm.runInNewContext(fs.readFileSync("app.js", "utf8"), context);

const submit = () => submitHandler({ preventDefault() {}, currentTarget: form });

submit();
assert.deepEqual(alerts, ["Recall details must be longer than 25 characters."]);
assert.equal(logs.length, 0, "short content must not reach successful submission logs");

elements.recallDetails.value = "Affected bags may contain undeclared almonds and should be returned.";
submit();
assert.equal(alerts.at(-1), "You must agree to the terms and conditions.");
assert.equal(logs.length, 0, "unchecked terms must not increment or log a submission");

elements.termsAccepted.checked = true;
submit();
assert.equal(logs.find((entry) => entry[0] === "Successful submission count:")[1], 1);
assert.match(elements.statusMessage.textContent, /Submission #1/);
assert.ok(logs.some((entry) => entry[0] === "Submission JSON:"));
assert.ok(logs.some((entry) => entry[0] === "Updated submission:" && entry[1].submissionDate));

console.log("JavaScript form tests passed: short content, unchecked terms, and valid submission.");

