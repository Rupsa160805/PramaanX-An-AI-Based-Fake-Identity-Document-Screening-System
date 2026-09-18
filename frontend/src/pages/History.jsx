import React, { useState } from "react";

function History() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const screenings = [
    {
      id: "PX-2026-00124",
      date: "09 Sep 2026, 18:42",
      document: "Passport",
      country: "India",
      status: "Approved",
      risk: "Low",
    },
    {
      id: "PX-2026-00123",
      date: "09 Sep 2026, 17:15",
      document: "Visa",
      country: "Thailand",
      status: "Manual Review",
      risk: "Medium",
    },
    {
      id: "PX-2026-00122",
      date: "09 Sep 2026, 15:31",
      document: "Passport",
      country: "Bangladesh",
      status: "Secondary Inspection",
      risk: "High",
    },
    {
      id: "PX-2026-00121",
      date: "09 Sep 2026, 13:07",
      document: "Passport",
      country: "India",
      status: "Approved",
      risk: "Low",
    },
    {
      id: "PX-2026-00120",
      date: "08 Sep 2026, 21:48",
      document: "Visa",
      country: "Nepal",
      status: "False Positive",
      risk: "Medium",
    },
  ];

  const filteredData = screenings.filter((item) => {

    const matchesSearch =
      item.id.toLowerCase().includes(search.toLowerCase()) ||
      item.document.toLowerCase().includes(search.toLowerCase()) ||
      item.country.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === "All" ||
      item.status === filter;

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="history-page">

      <div className="page-header">

        <div>
          <div className="breadcrumb">
            Dashboard / Screening History
          </div>

          <h1>Screening History</h1>

          <p>
            Review previous document screening activities.
          </p>
        </div>

        <div className="history-count">
          {filteredData.length} Records
        </div>

      </div>


      {/* STATISTICS */}
      <div className="history-stats">

        <div className="history-stat-card">
          <span>📋</span>
          <div>
            <small>Total Screenings</small>
            <strong>124</strong>
          </div>
        </div>

        <div className="history-stat-card">
          <span>✓</span>
          <div>
            <small>Approved</small>
            <strong>98</strong>
          </div>
        </div>

        <div className="history-stat-card">
          <span>⚠️</span>
          <div>
            <small>Manual Reviews</small>
            <strong>18</strong>
          </div>
        </div>

        <div className="history-stat-card">
          <span>🚨</span>
          <div>
            <small>High Risk</small>
            <strong>8</strong>
          </div>
        </div>

      </div>


      {/* TABLE CARD */}
      <div className="history-card">

        <div className="history-toolbar">

          <div className="search-box">
            🔎

            <input
              type="text"
              placeholder="Search screening ID, document or country..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="All">All Status</option>
            <option value="Approved">Approved</option>
            <option value="Manual Review">
              Manual Review
            </option>
            <option value="Secondary Inspection">
              Secondary Inspection
            </option>
            <option value="False Positive">
              False Positive
            </option>
          </select>

        </div>


        <div className="history-table-wrapper">

          <table className="history-table">

            <thead>
              <tr>
                <th>Screening ID</th>
                <th>Date & Time</th>
                <th>Document</th>
                <th>Country</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>

              {filteredData.map((item) => (

                <tr key={item.id}>

                  <td>
                    <strong>{item.id}</strong>
                  </td>

                  <td>
                    {item.date}
                  </td>

                  <td>
                    {item.document}
                  </td>

                  <td>
                    {item.country}
                  </td>

                  <td>
                    <span
                      className={`history-status ${item.status
                        .toLowerCase()
                        .replaceAll(" ", "-")}`}
                    >
                      {item.status}
                    </span>
                  </td>

                  <td>
                    <span
                      className={`risk-label ${item.risk.toLowerCase()}`}
                    >
                      {item.risk}
                    </span>
                  </td>

                  <td>
                    <button
                      className="view-button"
                      onClick={() =>
                        alert(
                          `Opening screening ${item.id}`
                        )
                      }
                    >
                      View
                    </button>
                  </td>

                </tr>

              ))}

            </tbody>

          </table>

          {filteredData.length === 0 && (
            <div className="empty-history">
              <div>🔍</div>
              <h3>No screenings found</h3>
              <p>
                Try changing your search or filter.
              </p>
            </div>
          )}

        </div>

      </div>


      <div className="screening-footer-note">

        <span>🔐</span>

        <div>
          <strong>Audit Trail</strong>

          <p>
            Screening history is intended to provide an auditable
            record of officer actions. Persistent database storage
            will be connected in the backend phase.
          </p>
        </div>

      </div>

    </div>
  );
}

export default History;