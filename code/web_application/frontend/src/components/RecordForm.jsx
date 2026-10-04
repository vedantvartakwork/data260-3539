import React, { useEffect, useState } from "react";

import { manufacturersApi } from "../api.js";


const CATEGORIES = [
  "Produce",
  "Meat and Seafood",
  "Dairy and Refrigerated",
  "Packaged Foods",
];

const EMPTY_RECORD = {
  product_name: "",
  recall_code: "",
  units_affected: 0,
  manufacturer_id: 0,
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
  const [manufacturers, setManufacturers] = useState([]);

  useEffect(() => {
    manufacturersApi.list()
      .then((rows) => {
        setManufacturers(rows);
        if (!record.manufacturer_id && rows.length) {
          setRecord((current) => ({
            ...current,
            manufacturer_id: rows[0].id,
            brand_name: current.brand_name || rows[0].name,
          }));
        }
      })
      .catch((loadError) => setError(loadError.message));
  }, []);

  function updateField(event) {
    const { name, type, checked, value } = event.target;
    setRecord((current) => {
      const nextValue = type === "checkbox" ? checked : value;
      const next = {
        ...current,
        [name]: ["units_affected", "manufacturer_id"].includes(name)
          ? Number(nextValue)
          : nextValue,
      };
      if (name === "manufacturer_id") {
        const manufacturer = manufacturers.find((item) => item.id === Number(value));
        if (manufacturer) next.brand_name = manufacturer.name;
      }
      return next;
    });
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
          Recall code (unique)
          <input
            name="recall_code"
            value={record.recall_code}
            onChange={updateField}
            placeholder="REC-3539-001"
            pattern="REC-[A-Za-z0-9][A-Za-z0-9-]{2,23}"
            required
          />
        </label>
        <label>
          Units affected
          <input
            name="units_affected"
            type="number"
            min="0"
            value={record.units_affected}
            onChange={updateField}
            required
          />
        </label>
        <label>
          Manufacturer
          <select
            name="manufacturer_id"
            value={record.manufacturer_id}
            onChange={updateField}
            required
          >
            <option value="0">Select a manufacturer</option>
            {manufacturers.map((manufacturer) => (
              <option key={manufacturer.id} value={manufacturer.id}>
                {manufacturer.name}
              </option>
            ))}
          </select>
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
