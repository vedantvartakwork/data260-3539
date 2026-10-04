import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";

import { recallsApi } from "../api.js";
import { deleteRecall } from "../features/recalls/recallsSlice.js";


export default function DeleteRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    recallsApi.get(id).then(setRecord).catch((loadError) => setError(loadError.message));
  }, [id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!record) return <div className="state-card">Loading recall notice...</div>;

  async function handleDelete() {
    await dispatch(deleteRecall(Number(id))).unwrap();
    navigate("/");
  }

  return (
    <section className="panel narrow">
      <p className="eyebrow">Delete</p>
      <h1>Delete recall #{id}</h1>
      <p className="intro">
        Remove <strong>{record.product_name}</strong> by {record.brand_name} from MySQL?
      </p>
      <div className="actions">
        <button className="danger" onClick={handleDelete}>Delete recall notice</button>
        <Link className="secondary button-link" to="/">Cancel</Link>
      </div>
    </section>
  );
}
