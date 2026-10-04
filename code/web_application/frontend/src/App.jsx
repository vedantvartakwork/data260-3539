import React, { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";

import { authApi } from "./api.js";
import { fetchRecalls } from "./features/recalls/recallsSlice.js";
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
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    if (user) dispatch(fetchRecalls());
  }, [user, dispatch]);

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
                <Home user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <CreateRecord />
              </ProtectedRoute>
            }
          />
          <Route
            path="/update/:id"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <UpdateRecord />
              </ProtectedRoute>
            }
          />
          <Route
            path="/delete/:id"
            element={
              <ProtectedRoute user={user} checkingSession={checkingSession}>
                <DeleteRecord />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
