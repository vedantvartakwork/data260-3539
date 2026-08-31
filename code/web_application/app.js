"use strict";

const createSubmissionCounter = () => {
  let count = 0;
  return () => {
    count += 1;
    return count;
  };
};

const countSuccessfulSubmission = createSubmissionCounter();

const validateForm = () => {
  const details = document.getElementById("recallDetails").value.trim();
  const termsAccepted = document.getElementById("termsAccepted").checked;

  if (details.length <= 25) {
    alert("Recall details must be longer than 25 characters.");
    return false;
  }

  if (!termsAccepted) {
    alert("You must agree to the terms and conditions.");
    return false;
  }

  return true;
};

document.getElementById("recallForm").addEventListener("submit", (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  if (!validateForm()) return;

  const formData = new FormData(form);
  const submission = Object.fromEntries(formData.entries());
  submission.termsAccepted = document.getElementById("termsAccepted").checked;

  const jsonString = JSON.stringify(submission);
  console.log("Submission JSON:", jsonString);

  const parsedSubmission = JSON.parse(jsonString);
  const { productName, submitterEmail } = parsedSubmission;
  console.log("Product name:", productName);
  console.log("Submitter email:", submitterEmail);

  const updatedSubmission = {
    ...parsedSubmission,
    submissionDate: new Date().toISOString(),
  };
  console.log("Updated submission:", updatedSubmission);

  const submissionCount = countSuccessfulSubmission();
  console.log("Successful submission count:", submissionCount);
  document.getElementById("statusMessage").textContent =
    `Recall notice submitted successfully. Submission #${submissionCount}.`;
});

