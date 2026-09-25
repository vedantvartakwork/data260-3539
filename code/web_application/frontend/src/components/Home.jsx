import React, { useState } from "react";
import { Link } from "react-router-dom";


export default function Home({ records, loading, error, onSearch, user, notice }) {
  const [query, setQuery] = useState("");

  function handleSearch(event) {
    event.preventDefault();
    onSearch(query);
  }

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">DATA 260 - Homework 4</p>
          <h1>Grocery Recall Manager</h1>
          <p className="intro">Signed in as {user?.name}. Review and maintain current grocery safety notices.</p>
        </div>
        <Link className="primary button-link" to="/create">Add recall notice</Link>
      </section>

      <section className="panel">
        {notice && <div className="alert success">{notice}</div>}
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Current records</p>
            <h2>Recall notices</h2>
          </div>
          <span className="count-pill">{records.length} shown</span>
        </div>

        <form className="search-row" onSubmit={handleSearch}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search product or brand"
          />
          <button className="secondary">Search</button>
          <button type="button" className="plain" onClick={() => { setQuery(""); onSearch(""); }}>
            Clear
          </button>
        </form>

        {loading && <div className="state-card">Loading recall notices...</div>}
        {error && <div className="alert error">{error}</div>}
        {!loading && !error && records.length === 0 && (
          <div className="state-card">No recall notices found.</div>
        )}

        {!loading && !error && records.length > 0 && (
          <div className="record-grid">
            {records.map((record) => (
              <article className="record-card" key={record.id}>
                <div className="record-title-row">
                  <div>
                    <span className="record-id">#{record.id}</span>
                    <h3>{record.product_name}</h3>
                  </div>
                  <span className="category-pill">{record.category}</span>
                </div>
                <p className="brand">{record.brand_name}</p>
                <p>{record.recall_details}</p>
                <p className="related-count">Related events: {record.events.length}</p>
                <div className="actions">
                  <Link className="secondary button-link" to={`/update/${record.id}`}>Update</Link>
                  <Link className="danger button-link" to={`/delete/${record.id}`}>Delete</Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
