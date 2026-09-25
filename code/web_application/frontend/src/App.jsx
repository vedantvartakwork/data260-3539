import React, { useCallback, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { authApi, recallsApi } from "./api.js";
import Login from "./components/Login.jsx";
import Home from "./components/Home.jsx";
import CreateRecord from "./components/CreateRecord.jsx";
import UpdateRecord from "./components/UpdateRecord.jsx";
import DeleteRecord from "./components/DeleteRecord.jsx";


function ProtectedRoute({ user, checkingSession, children }) {
  if (checkingSession) {
    return <div className="state-card">Checking your session...</div>;
  }
  return user ? children : <Navigate to="/login" replace />;
}


export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRecords = useCallback(async (query = "") => {
    setLoading(true);
    setError("");
    try {
      setRecords(await recallsApi.list(query));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    if (user) loadRecords();
    else setRecords([]);
  }, [user, loadRecords]);

  async function handleLogin(email, password) {
    const loggedInUser = await authApi.login(email, password);
    setUser(loggedInUser);
    navigate("/");
  }

  async function handleLogout() {
    await authApi.logout();
    setUser(null);
    navigate("/login");
  }

  async function handleCreate(payload) {
    const created = await recallsApi.create(payload);
    await loadRecords();
    setNotice(`Added recall ID ${created.id} successfully.`);
    navigate("/");
  }

  async function handleUpdate(id, payload) {
    await recallsApi.update(id, payload);
    await loadRecords();
    setNotice(`Updated recall ID ${id} successfully.`);
    navigate("/");
  }

  async function handleDelete(id) {
    await recallsApi.remove(id);
    await loadRecords();
    setNotice(`Deleted recall ID ${id} successfully.`);
    navigate("/");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">Grocery Recall Manager</Link>
        <nav>
          {user ? (
            <>
              <Link to="/">Recall records</Link>
              <Link to="/create">Add record</Link>
              <button className="link-button" onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <Link to="/login">Login</Link>
          )}
        </nav>
      </header>

      <main>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />}
          />
          <Route
            path="/"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <Home
                  records={records}
                  loading={loading}
                  error={error}
                  onSearch={loadRecords}
                  user={user}
                  notice={notice}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <CreateRecord onCreate={handleCreate} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/update/:id"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <UpdateRecord onUpdate={handleUpdate} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/delete/:id"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <DeleteRecord onDelete={handleDelete} />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
