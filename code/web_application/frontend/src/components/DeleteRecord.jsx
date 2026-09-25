import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { recallsApi } from "../api.js";


export default function DeleteRecord({ onDelete }) {
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    recallsApi.get(id).then(setRecord).catch((loadError) => setError(loadError.message));
  }, [id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!record) return <div className="state-card">Loading recall notice...</div>;

  return (
    <section className="panel narrow">
      <p className="eyebrow">Delete</p>
      <h1>Delete recall #{id}</h1>
      <p className="intro">
        Remove <strong>{record.product_name}</strong> by {record.brand_name} from MySQL?
      </p>
      <div className="actions">
        <button className="danger" onClick={() => onDelete(Number(id))}>Delete recall notice</button>
        <Link className="secondary button-link" to="/">Cancel</Link>
      </div>
    </section>
  );
}
