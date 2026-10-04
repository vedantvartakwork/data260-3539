import React from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";

import { createRecall } from "../features/recalls/recallsSlice.js";
import RecordForm from "./RecordForm.jsx";


export default function CreateRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  async function handleCreate(payload) {
    await dispatch(createRecall(payload)).unwrap();
    navigate("/");
  }
  return (
    <section className="panel narrow">
      <p className="eyebrow">Create</p>
      <h1>Add a recall notice</h1>
      <p className="intro">Enter the affected product and recall information.</p>
      <RecordForm submitLabel="Add recall notice" onSubmit={handleCreate} />
    </section>
  );
}
