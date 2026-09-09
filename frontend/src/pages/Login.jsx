import React, { useState } from "react";
import { loginOfficer } from "../services/api";

function Login({ onLogin }) {
  const [officerId, setOfficerId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!officerId || !password) {
      setError("Please provide both Officer ID and Password.");
      return;
    }

    setIsLoading(true);

    try {
      const result = await loginOfficer(officerId, password);
      // Store token/role if needed, for now just succeed
      console.log("Logged in successfully:", result);
      onLogin(result.officer_id);
    } catch (err) {
      setError(err.message || "Failed to connect to backend");
    } finally {
      setIsLoading(false);
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
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label>Password</label>

            <input
              type="password"
              placeholder="Enter Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
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
            disabled={isLoading}
          >
            {isLoading ? "Authenticating..." : "Login"}
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