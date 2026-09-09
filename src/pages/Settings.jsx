import React, { useState } from "react";

function Settings() {
  const [notifications, setNotifications] = useState(true);
  const [sound, setSound] = useState(true);
  const [autoSave, setAutoSave] = useState(true);

  const [saved, setSaved] = useState(false);

  const saveSettings = () => {
    setSaved(true);

    setTimeout(() => {
      setSaved(false);
    }, 2000);
  };

  return (
    <div className="settings-page">

      <div className="page-header">

        <div>
          <div className="breadcrumb">
            Dashboard / Settings
          </div>

          <h1>Settings</h1>

          <p>
            Manage officer preferences and system settings.
          </p>
        </div>

      </div>


      {/* PROFILE */}
      <div className="settings-card">

        <div className="settings-card-header">

          <div>
            <h2>👮 Officer Profile</h2>

            <p>
              Current authenticated officer information.
            </p>
          </div>

          <span className="verified-badge">
            ✓ Verified
          </span>

        </div>


        <div className="profile-section">

          <div className="profile-avatar">
            O
          </div>

          <div className="profile-info">

            <h3>Border Officer</h3>

            <p>
              Officer ID: OFFICER001
            </p>

            <span>
              Authorized Screening Officer
            </span>

          </div>

        </div>


        <div className="settings-fields">

          <div className="settings-field">
            <label>Officer ID</label>
            <input
              value="OFFICER001"
              readOnly
            />
          </div>

          <div className="settings-field">
            <label>Role</label>
            <input
              value="Screening Officer"
              readOnly
            />
          </div>

        </div>

      </div>


      {/* PREFERENCES */}
      <div className="settings-card">

        <div className="settings-card-header">

          <div>
            <h2>🔔 Preferences</h2>

            <p>
              Customize the officer dashboard experience.
            </p>
          </div>

        </div>


        <div className="setting-row">

          <div>
            <strong>Notifications</strong>
            <p>
              Receive alerts for high-risk screening results.
            </p>
          </div>

          <button
            className={`toggle ${
              notifications ? "on" : ""
            }`}
            onClick={() =>
              setNotifications(!notifications)
            }
          >
            <span></span>
          </button>

        </div>


        <div className="setting-row">

          <div>
            <strong>Alert Sound</strong>
            <p>
              Play an alert when a critical risk is detected.
            </p>
          </div>

          <button
            className={`toggle ${
              sound ? "on" : ""
            }`}
            onClick={() =>
              setSound(!sound)
            }
          >
            <span></span>
          </button>

        </div>


        <div className="setting-row">

          <div>
            <strong>Automatic Draft Saving</strong>
            <p>
              Save screening notes locally during an active session.
            </p>
          </div>

          <button
            className={`toggle ${
              autoSave ? "on" : ""
            }`}
            onClick={() =>
              setAutoSave(!autoSave)
            }
          >
            <span></span>
          </button>

        </div>

      </div>


      {/* SECURITY */}
      <div className="settings-card">

        <div className="settings-card-header">

          <div>
            <h2>🔐 Security</h2>

            <p>
              Current session and security information.
            </p>
          </div>

        </div>


        <div className="security-items">

          <div className="security-item">
            <span>Session Status</span>
            <strong className="secure-text">
              ● Active
            </strong>
          </div>

          <div className="security-item">
            <span>Authentication</span>
            <strong>
              Officer Login
            </strong>
          </div>

          <div className="security-item">
            <span>Data Protection</span>
            <strong>
              Protected Session
            </strong>
          </div>

        </div>

      </div>


      {/* SYSTEM */}
      <div className="settings-card">

        <div className="settings-card-header">

          <div>
            <h2>⚙️ System</h2>

            <p>
              PramaanX system information.
            </p>
          </div>

        </div>


        <div className="system-information">

          <div>
            <span>Application</span>
            <strong>PramaanX</strong>
          </div>

          <div>
            <span>Version</span>
            <strong>Frontend Demo v1.0</strong>
          </div>

          <div>
            <span>AI Engine</span>
            <strong>Awaiting Backend</strong>
          </div>

          <div>
            <span>Database</span>
            <strong>Awaiting Backend</strong>
          </div>

        </div>

      </div>


      {/* SAVE */}
      <div className="settings-actions">

        {saved && (
          <span className="saved-message">
            ✓ Settings saved
          </span>
        )}

        <button
          className="primary-action"
          onClick={saveSettings}
        >
          Save Settings
        </button>

      </div>

    </div>
  );
}

export default Settings;