import React, { useState } from "react";

function Login({ onLogin }) {
  const [officerId, setOfficerId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    // Temporary demo login
    if (officerId === "OFFICER001" && password === "PramaanX@123") {
      setError("");
      onLogin();
    } else {
      setError("Invalid Officer ID or Password");
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">

        <h1>PramaanX</h1>

        <p className="login-subtitle">
          AI-Powered Border Document Intelligence
        </p>

        <form onSubmit={handleSubmit}>

          <div className="form-group">
            <label>Officer ID</label>

            <input
              type="text"
              placeholder="Enter Officer ID"
              value={officerId}
              onChange={(e) => setOfficerId(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Password</label>

            <input
              type="password"
              placeholder="Enter Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <p className="login-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="login-button"
          >
            Login
          </button>

        </form>

        <p className="login-info">
          Authorized personnel only
        </p>

      </div>
    </div>
  );
}

export default Login;