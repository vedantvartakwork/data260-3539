import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { recallsApi } from "../api.js";
import RecordForm from "./RecordForm.jsx";


export default function UpdateRecord({ onUpdate }) {
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
      <p className="eyebrow">Update</p>
      <h1>Update recall #{id}</h1>
      <p className="intro">Edit the record and save it back to MySQL.</p>
      <RecordForm
        initialRecord={record}
        submitLabel="Update recall notice"
        onSubmit={(payload) => onUpdate(Number(id), payload)}
      />
    </section>
  );
}
