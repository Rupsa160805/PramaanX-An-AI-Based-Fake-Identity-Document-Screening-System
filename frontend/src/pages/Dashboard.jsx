import React, { useState } from "react";
import Screening from "./Screening";
import Sidebar from "../components/Sidebar";

function Dashboard({ onLogout }) {
  const [activePage, setActivePage] = useState("dashboard");

  const [document, setDocument] = useState(null);
  const [documentName, setDocumentName] = useState("");
  const [notes, setNotes] = useState("");

  const [settings, setSettings] = useState({
    notifications: true,
    autoAnalysis: true,
    darkMode: false,
  });

  // =========================================================
  // DOCUMENT UPLOAD
  // =========================================================

  const handleDocumentUpload = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setDocumentName(file.name);

    if (file.type.startsWith("image/")) {
      setDocument(URL.createObjectURL(file));
    } else {
      setDocument(null);
    }
  };

  // =========================================================
  // OFFICER ACTION
  // =========================================================

  const handleOfficerAction = (action) => {
    alert(`${action} selected`);
  };

  // =========================================================
  // DASHBOARD
  // =========================================================

  const renderDashboard = () => {
    return (
      <>
        {/* HEADER */}
        <header className="dashboard-header">
          <div>
            <div className="header-label">OFFICER CONSOLE</div>

            <h1>PramaanX</h1>

            <p>
              Border Document Intelligence & Verification
            </p>
          </div>

          <div className="officer-info">
            <div className="officer-status">
              <span className="online-dot"></span>
              System Online
            </div>

            <div className="officer-profile">
              <span className="officer-avatar">👮</span>

              <div>
                <strong>OFFICER001</strong>
                <small>Authorized Officer</small>
              </div>
            </div>

            <button
              className="header-logout"
              onClick={onLogout}
            >
              Logout
            </button>
          </div>
        </header>

        <main className="dashboard-content">

          {/* WELCOME */}
          <section className="welcome-banner">
            <div>
              <span>SECURE SCREENING ENVIRONMENT</span>

              <h2>Welcome to the PramaanX Officer Console</h2>

              <p>
                Review identity documents, verification signals,
                risk indicators and AI-generated evidence from one
                unified workspace.
              </p>
            </div>

            <button
              className="welcome-button"
              onClick={() => setActivePage("screening")}
            >
              + New Screening
            </button>
          </section>

          {/* STATISTICS */}
          <section className="dashboard-stats">

            <div className="stat-card">
              <div className="stat-icon blue">📄</div>

              <div>
                <span>Total Screenings</span>
                <strong>0</strong>
                <small>No records yet</small>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon green">✓</div>

              <div>
                <span>Verified</span>
                <strong>0</strong>
                <small>Awaiting analysis</small>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon orange">⚠</div>

              <div>
                <span>Flagged</span>
                <strong>0</strong>
                <small>Requires review</small>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon red">!</div>

              <div>
                <span>High Risk</span>
                <strong>0</strong>
                <small>No cases available</small>
              </div>
            </div>

          </section>

          {/* QUICK ACTIONS */}
          <section className="dashboard-card">
            <div className="section-heading">
              <div>
                <h2>Quick Actions</h2>
                <p>Start common officer workflows.</p>
              </div>
            </div>

            <div className="quick-actions">

              <button
                onClick={() => setActivePage("screening")}
              >
                <span>🔍</span>

                <div>
                  <strong>New Screening</strong>
                  <small>
                    Upload and analyse a document
                  </small>
                </div>
              </button>

              <button
                onClick={() => setActivePage("history")}
              >
                <span>📋</span>

                <div>
                  <strong>Screening History</strong>
                  <small>
                    Review previous screening records
                  </small>
                </div>
              </button>

              <button
                onClick={() => setActivePage("settings")}
              >
                <span>⚙️</span>

                <div>
                  <strong>System Settings</strong>
                  <small>
                    Configure officer preferences
                  </small>
                </div>
              </button>

            </div>
          </section>

          {/* VERIFICATION PIPELINE */}
          <section className="dashboard-card">

            <div className="section-heading">
              <div>
                <h2>PramaanX Verification Pipeline</h2>

                <p>
                  Independent evidence sources are combined
                  to support officer decision-making.
                </p>
              </div>
            </div>

            <div className="verification-pipeline">

              <div className="verification-stage">
                <div>01</div>
                <strong>Document</strong>
                <span>Capture</span>
              </div>

              <div className="pipeline-arrow">→</div>

              <div className="verification-stage">
                <div>02</div>
                <strong>OCR / MRZ</strong>
                <span>Extraction</span>
              </div>

              <div className="pipeline-arrow">→</div>

              <div className="verification-stage">
                <div>03</div>
                <strong>Tampering</strong>
                <span>Detection</span>
              </div>

              <div className="pipeline-arrow">→</div>

              <div className="verification-stage">
                <div>04</div>
                <strong>Face</strong>
                <span>Verification</span>
              </div>

              <div className="pipeline-arrow">→</div>

              <div className="verification-stage">
                <div>05</div>
                <strong>Risk</strong>
                <span>Assessment</span>
              </div>

            </div>

          </section>

          {/* IDENTITY EVIDENCE */}
          <section className="dashboard-card">

            <div className="section-heading">
              <div>
                <h2>Identity Evidence Triangle</h2>

                <p>
                  PramaanX compares three independent evidence
                  sources before generating a risk assessment.
                </p>
              </div>
            </div>

            <div className="evidence-grid">

              <div className="evidence-card">
                <div className="evidence-number">01</div>

                <h3>Visual Evidence</h3>

                <p>
                  Visible document information and photograph.
                </p>
              </div>

              <div className="evidence-card">
                <div className="evidence-number">02</div>

                <h3>Machine Evidence</h3>

                <p>
                  OCR, MRZ, document rules and authenticity signals.
                </p>
              </div>

              <div className="evidence-card">
                <div className="evidence-number">03</div>

                <h3>Live Evidence</h3>

                <p>
                  Face verification and liveness information.
                </p>
              </div>

            </div>

          </section>

          {/* RECENT ACTIVITY */}
          <section className="dashboard-card">

            <div className="section-heading">
              <div>
                <h2>Recent Activity</h2>

                <p>
                  Latest officer screening activity.
                </p>
              </div>
            </div>

            <div className="empty-activity">

              <div className="empty-icon">📋</div>

              <h3>No screening activity yet</h3>

              <p>
                Start your first document screening to see
                verification activity here.
              </p>

              <button
                onClick={() => setActivePage("screening")}
              >
                Start First Screening
              </button>

            </div>

          </section>

        </main>

        <footer className="dashboard-footer">
          <p>
            PramaanX • AI-Powered Border Document Intelligence
          </p>

          <span>
            Decision-support system for authorized officers
          </span>
        </footer>
      </>
    );
  };

  // =========================================================
  // HISTORY
  // =========================================================

  const renderHistory = () => {
    return (
      <div className="inner-page">

        <header className="page-header">
          <div>
            <span className="header-label">
              RECORD MANAGEMENT
            </span>

            <h1>Screening History</h1>

            <p>
              Review previously processed screening records.
            </p>
          </div>

          <button
            className="primary-action"
            onClick={() => setActivePage("screening")}
          >
            + New Screening
          </button>
        </header>

        <div className="history-stats">

          <div className="history-stat-card">
            <span>📋</span>

            <div>
              <small>Total Cases</small>
              <strong>0</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span>✓</span>

            <div>
              <small>Approved</small>
              <strong>0</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span>⚠</span>

            <div>
              <small>Flagged</small>
              <strong>0</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span>⏱</span>

            <div>
              <small>Pending</small>
              <strong>0</strong>
            </div>
          </div>

        </div>

        <section className="dashboard-card">

          <div className="history-toolbar">

            <div className="search-box">
              🔎
              <input
                type="text"
                placeholder="Search screening records..."
              />
            </div>

            <select>
              <option>All Status</option>
              <option>Approved</option>
              <option>Flagged</option>
              <option>Pending</option>
            </select>

          </div>

          <div className="empty-activity">

            <div className="empty-icon">📂</div>

            <h3>No screening records</h3>

            <p>
              Screening records will appear here after
              the backend and database are connected.
            </p>

            <button
              onClick={() => setActivePage("screening")}
            >
              Create Screening

            </button>

          </div>

        </section>

      </div>
    );
  };

  // =========================================================
  // SETTINGS
  // =========================================================

  const renderSettings = () => {
    const toggleSetting = (name) => {
      setSettings((previous) => ({
        ...previous,
        [name]: !previous[name],
      }));
    };

    return (
      <div className="inner-page">

        <header className="page-header">

          <div>
            <span className="header-label">
              SYSTEM CONFIGURATION
            </span>

            <h1>Settings</h1>

            <p>
              Manage officer and application preferences.
            </p>
          </div>

        </header>

        <section className="settings-layout">

          {/* PROFILE */}
          <div className="dashboard-card">

            <h2>👮 Officer Profile</h2>

            <p className="section-description">
              Current authorized officer information.
            </p>

            <div className="settings-profile">

              <div className="large-avatar">
                👮
              </div>

              <div>
                <h3>OFFICER001</h3>

                <p>
                  Authorized Border Screening Officer
                </p>

                <span className="profile-status">
                  ● Active Session
                </span>
              </div>

            </div>

          </div>

          {/* PREFERENCES */}
          <div className="dashboard-card">

            <h2>⚙️ Application Preferences</h2>

            <p className="section-description">
              Configure the officer console behaviour.
            </p>

            <div className="setting-row">

              <div>
                <strong>System Notifications</strong>

                <p>
                  Receive important screening notifications.
                </p>
              </div>

              <button
                className={
                  settings.notifications
                    ? "toggle on"
                    : "toggle"
                }
                onClick={() =>
                  toggleSetting("notifications")
                }
              >
                <span></span>
              </button>

            </div>

            <div className="setting-row">

              <div>
                <strong>Automatic Analysis</strong>

                <p>
                  Start AI processing after document upload.
                </p>
              </div>

              <button
                className={
                  settings.autoAnalysis
                    ? "toggle on"
                    : "toggle"
                }
                onClick={() =>
                  toggleSetting("autoAnalysis")
                }
              >
                <span></span>
              </button>

            </div>

            <div className="setting-row">

              <div>
                <strong>Dark Mode</strong>

                <p>
                  Interface theme preference.
                </p>
              </div>

              <button
                className={
                  settings.darkMode
                    ? "toggle on"
                    : "toggle"
                }
                onClick={() =>
                  toggleSetting("darkMode")
                }
              >
                <span></span>
              </button>

            </div>

          </div>

          {/* SECURITY */}
          <div className="dashboard-card">

            <h2>🔐 Security</h2>

            <p className="section-description">
              Security information for the current session.
            </p>

            <div className="security-row">
              <span>Authentication</span>
              <strong className="status-good">
                ✓ Active
              </strong>
            </div>

            <div className="security-row">
              <span>Officer Authorization</span>
              <strong className="status-good">
                ✓ Verified
              </strong>
            </div>

            <div className="security-row">
              <span>Database Connection</span>
              <strong className="status-pending">
                Pending Backend
              </strong>
            </div>

            <div className="security-row">
              <span>AI Services</span>
              <strong className="status-pending">
                Pending Integration
              </strong>
            </div>

          </div>

        </section>

      </div>
    );
  };

  // =========================================================
  // PAGE ROUTING
  // =========================================================

  const renderPage = () => {

    if (activePage === "dashboard") {
      return renderDashboard();
    }

    if (activePage === "screening") {
      return <Screening />;
    }

    if (activePage === "history") {
      return renderHistory();
    }

    if (activePage === "settings") {
      return renderSettings();
    }

    return renderDashboard();
  };

  // =========================================================
  // MAIN LAYOUT
  // =========================================================

  return (
    <div className="dashboard-layout">

      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        onLogout={onLogout}
      />

      <div className="dashboard-main">
        {renderPage()}
      </div>

    </div>
  );
}

export default Dashboard;