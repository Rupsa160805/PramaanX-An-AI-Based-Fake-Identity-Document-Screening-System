import React from "react";

function Sidebar({ activePage, setActivePage, onLogout }) {
  return (
    <aside className="sidebar">

      <div className="sidebar-logo">
        <div className="brand-mark">PX</div>

        <div>
          <h2>PramaanX</h2>
          <p>Border Intelligence</p>
        </div>
      </div>

      <nav className="sidebar-nav">

        <button
          className={
            activePage === "dashboard"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() => setActivePage("dashboard")}
        >
          <span>🏠</span>
          Dashboard
        </button>

        <button
          className={
            activePage === "screening"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() => setActivePage("screening")}
        >
          <span>🔍</span>
          New Screening
        </button>

        <button
          className={
            activePage === "history"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() => setActivePage("history")}
        >
          <span>📋</span>
          Screening History
        </button>

        <button
          className={
            activePage === "settings"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() => setActivePage("settings")}
        >
          <span>⚙️</span>
          Settings
        </button>

      </nav>

      <div className="sidebar-bottom">

        <div className="sidebar-security">
          <span className="online-dot"></span>

          <div>
            <strong>System Online</strong>
            <small>Secure session</small>
          </div>
        </div>

        <button
          className="logout-button"
          onClick={onLogout}
        >
          <span>🚪</span>
          Logout
        </button>

      </div>

    </aside>
  );
}

export default Sidebar;