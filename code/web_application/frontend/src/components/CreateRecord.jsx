import React from "react";
import RecordForm from "./RecordForm.jsx";


export default function CreateRecord({ onCreate }) {
  return (
    <section className="panel narrow">
      <p className="eyebrow">Create</p>
      <h1>Add a recall notice</h1>
      <p className="intro">Enter the affected product and recall information.</p>
      <RecordForm submitLabel="Add recall notice" onSubmit={onCreate} />
    </section>
  );
}
