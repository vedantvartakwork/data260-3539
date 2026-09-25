import React, { useState } from "react";


const CATEGORIES = [
  "Produce",
  "Meat and Seafood",
  "Dairy and Refrigerated",
  "Packaged Foods",
];

const EMPTY_RECORD = {
  product_name: "",
  brand_name: "",
  submitter_email: "",
  category: "",
  recall_details: "",
  terms_accepted: false,
};


export default function RecordForm({ initialRecord = EMPTY_RECORD, submitLabel, onSubmit }) {
  const [record, setRecord] = useState({ ...EMPTY_RECORD, ...initialRecord });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    const { name, type, checked, value } = event.target;
    setRecord((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(record);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="record-form" onSubmit={handleSubmit}>
      {error && <div className="alert error">{error}</div>}
      <div className="form-grid">
        <label>
          Product name
          <input name="product_name" value={record.product_name} onChange={updateField} required />
        </label>
        <label>
          Brand or manufacturer
          <input name="brand_name" value={record.brand_name} onChange={updateField} required />
        </label>
        <label>
          Submitter email
          <input
            name="submitter_email"
            type="email"
            value={record.submitter_email}
            onChange={updateField}
            required
          />
        </label>
        <label>
          Product category
          <select name="category" value={record.category} onChange={updateField} required>
            <option value="">Select a category</option>
            {CATEGORIES.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
      </div>
      <label>
        Recall details
        <textarea
          name="recall_details"
          value={record.recall_details}
          onChange={updateField}
          minLength="26"
          required
        />
      </label>
      <label className="checkbox-row">
        <input
          name="terms_accepted"
          type="checkbox"
          checked={record.terms_accepted}
          onChange={updateField}
          required
        />
        I agree to the terms and conditions.
      </label>
      <button className="primary" disabled={submitting}>
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
