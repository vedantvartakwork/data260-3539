import React, { useState } from "react";


export default function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@example.edu");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onLogin(email, password);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <p className="eyebrow">Authorized staff</p>
      <h1>Sign in</h1>
      <p className="intro">Use your recall-management email and password.</p>
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={handleSubmit} className="record-form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <button className="primary full" disabled={submitting}>
          {submitting ? "Signing in..." : "Login"}
        </button>
      </form>
    </section>
  );
}
