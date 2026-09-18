import React, { useState } from "react";
import { verifyDocument } from "../services/api";

function Screening() {
  const [document, setDocument] = useState(null);
  const [preview, setPreview] = useState("");
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [scanResult, setScanResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const steps = [
    "Document Quality",
    "OCR & MRZ Extraction",
    "Tampering Detection",
    "Face Verification",
    "Risk Assessment",
  ];

  const handleDocumentUpload = (e) => {
    const file = e.target.files[0];

    if (!file) return;

    setDocument(file);
    setAnalysisStarted(false);
    setAnalysisComplete(false);
    setCurrentStep(0);
    setScanResult(null);
    setErrorMsg(null);

    if (file.type.startsWith("image/")) {
      const imageUrl = URL.createObjectURL(file);
      setPreview(imageUrl);
    } else {
      setPreview("");
    }
  };

  const startAnalysis = async () => {
    if (!document) return;

    setAnalysisStarted(true);
    setAnalysisComplete(false);
    setScanResult(null);
    setErrorMsg(null);
    setCurrentStep(1); // Starting Document Quality

    try {
      // Initiate actual API call
      const result = await verifyDocument(document);

      // Simulate pipeline progression for better UX
      let step = 1;
      const interval = setInterval(() => {
        step++;
        if (step <= 5) {
          setCurrentStep(step);
        }
        if (step === 5) {
          clearInterval(interval);
          setScanResult(result);
          setAnalysisComplete(true);
        }
      }, 800);

    } catch (err) {
      setErrorMsg(err.message || "An error occurred during verification.");
      setAnalysisStarted(false);
      setAnalysisComplete(false);
      setCurrentStep(0);
    }
  };

  const clearScreening = () => {
    setDocument(null);
    setPreview("");
    setAnalysisStarted(false);
    setAnalysisComplete(false);
    setCurrentStep(0);
    setScanResult(null);
    setErrorMsg(null);
  };

  const getStepStatus = (index) => {
    if (!analysisStarted) return "waiting";
    if (index + 1 < currentStep) return "complete";
    if (index + 1 === currentStep) return "processing";
    return "waiting";
  };

  // Helper to get formatted status from backend result
  const formatStatus = (moduleName) => {
    if (!scanResult) return "Waiting";
    const status = scanResult[moduleName]?.status;
    if (status === "completed") return "Completed";
    if (status === "failed") return "Failed";
    if (status === "not_available") return "Not Available";
    return "Waiting";
  };

  return (
    <div className="screening-page">

      {/* HEADER */}
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            Dashboard / New Screening
          </div>

          <h1>New Screening</h1>

          <p>
            Start a new document and identity verification process.
          </p>
        </div>

        <div className="screening-status">
          <span className="online-dot"></span>
          Ready
        </div>
      </div>

      {/* ERROR NOTICE */}
      {errorMsg && (
        <div className="demo-notice" style={{ backgroundColor: "#fee2e2", borderColor: "#ef4444" }}>
          <span>❌</span>
          <div>
            <strong style={{ color: "#b91c1c" }}>Error during analysis</strong>
            <p style={{ color: "#b91c1c" }}>{errorMsg}</p>
          </div>
        </div>
      )}


      {/* DOCUMENT UPLOAD */}
      <div className="screening-card">

        <div className="card-heading">
          <div>
            <h2>📄 Document Upload</h2>

            <p className="section-description">
              Upload a passport, visa, or supported identity document.
            </p>
          </div>

          {document && (
            <span className="file-ready">
              ✓ File Selected
            </span>
          )}
        </div>


        <label className="upload-area">

          <input
            type="file"
            accept=".jpg,.jpeg,.png,.webp,.bmp,.tiff"
            onChange={handleDocumentUpload}
          />

          {preview ? (
            <img
              className="screening-preview"
              src={preview}
              alt="Document preview"
            />
          ) : (
            <div className="upload-icon-large">
              📁
            </div>
          )}

          <h3>
            {document
              ? document.name
              : "Click to upload document"}
          </h3>

          <p>
            {document
              ? `${(document.size / 1024 / 1024).toFixed(2)} MB`
              : "Supported formats: JPG, JPEG, PNG, WEBP"}
          </p>

        </label>


        {document && (
          <div className="file-information">

            <div>
              <span>File Name</span>
              <strong>{document.name}</strong>
            </div>

            <div>
              <span>File Type</span>
              <strong>{document.type || "Unknown"}</strong>
            </div>

            <div>
              <span>File Size</span>
              <strong>
                {(document.size / 1024 / 1024).toFixed(2)} MB
              </strong>
            </div>

          </div>
        )}

      </div>


      {/* ANALYSIS PIPELINE */}
      <div className="screening-card">

        <div className="card-heading">

          <div>
            <h2>🔍 Analysis Pipeline</h2>

            <p className="section-description">
              The document passes through multiple verification stages.
            </p>
          </div>

          {analysisComplete && (
            <span className="analysis-complete">
              ✓ Analysis Complete
            </span>
          )}

        </div>


        <div className="analysis-pipeline">

          {steps.map((step, index) => {

            const status = getStepStatus(index);

            return (
              <div
                key={step}
                className={`pipeline-step ${status}`}
              >

                <div className="pipeline-number">

                  {status === "complete"
                    ? "✓"
                    : index + 1}

                </div>

                <div className="pipeline-content">

                  <strong>{step}</strong>

                  <p>

                    {status === "complete" &&
                      "Completed successfully"}

                    {status === "processing" &&
                      "Processing..."}

                    {status === "waiting" &&
                      (index === 0
                        ? "Waiting for analysis"
                        : "Waiting for previous stage")}

                  </p>

                </div>

                <div className="pipeline-status">

                  {status === "complete" && "✓"}

                  {status === "processing" && (
                    <span className="spinner"></span>
                  )}

                </div>

              </div>
            );
          })}

        </div>

      </div>


      {/* RESULTS */}
      {(analysisStarted || analysisComplete) && (

        <div className="screening-card">

          <div className="card-heading">
            <div>
              <h2>📊 Verification Results</h2>

              <p className="section-description">
                Current screening results.
              </p>
            </div>
            {scanResult?.request_id && (
              <div style={{ fontSize: "12px", color: "#64748b" }}>
                Request ID: {scanResult.request_id.slice(0, 8)}...
              </div>
            )}
          </div>


          <div className="screening-results-grid">

            <div className="result-card">
              <span className="result-icon">📄</span>
              <span>Document Quality</span>
              <strong>
                {analysisComplete ? (scanResult?.document?.quality?.usable ? "Good" : "Poor Flagged") : "Processing"}
              </strong>
            </div>

            <div className={`result-card ${scanResult?.ocr?.status === 'not_available' || scanResult?.mrz?.status === 'failed' ? 'warning' : ''}`}>
              <span className="result-icon">🔤</span>
              <span>OCR & MRZ</span>
              <strong>
                {analysisComplete ? `OCR: ${formatStatus('ocr')} | MRZ: ${formatStatus('mrz')}` : "Processing"}
              </strong>
            </div>

            <div className={`result-card ${scanResult?.tampering?.status === 'not_available' ? 'warning' : ''}`}>
              <span className="result-icon">🛡️</span>
              <span>Tampering</span>
              <strong>
                {analysisComplete ? formatStatus('tampering') : "Processing"}
              </strong>
            </div>

            <div className={`result-card ${scanResult?.face_verification?.status === 'not_available' ? 'warning' : ''}`}>
              <span className="result-icon">👤</span>
              <span>Face Verification</span>
              <strong>
                {analysisComplete ? formatStatus('face_verification') : "Waiting"}
              </strong>
            </div>

            <div className="result-card">
              <span className="result-icon">⚠️</span>
              <span>Risk Score / Recommendation</span>
              <strong>
                {analysisComplete
                  ? `Level: ${scanResult?.risk?.level?.toUpperCase() || 'UNKNOWN'} (${scanResult?.risk?.score || 0})`
                  : "Waiting"}
              </strong>
              {analysisComplete && (
                <div style={{ marginTop: '0.5rem', fontWeight: 500 }}>
                  Action: {scanResult?.recommendation?.action?.replace('_', ' ').toUpperCase()}
                </div>
              )}
            </div>

          </div>

          {/* BACKEND WARNINGS/NOTES */}
          {analysisComplete && scanResult?.warnings?.length > 0 && (
            <div style={{ marginTop: "20px", padding: "15px", backgroundColor: "#fffbeb", borderRadius: "8px", border: "1px solid #fef3c7" }}>
              <h4 style={{ margin: "0 0 10px 0", color: "#b45309" }}>System Warnings</h4>
              <ul style={{ margin: 0, paddingLeft: "20px", color: "#92400e" }}>
                {scanResult.warnings.map((warn, i) => <li key={i}>{warn}</li>)}
              </ul>
            </div>
          )}

        </div>

      )}


      {/* ACTIONS */}
      <div className="screening-actions">

        <button
          className="secondary-action"
          onClick={clearScreening}
        >
          ↻ Clear
        </button>

        <button
          className="primary-action"
          disabled={!document || analysisStarted}
          onClick={startAnalysis}
        >
          {analysisStarted
            ? "⏳ Analysis Running..."
            : "🔍 Start Analysis"}
        </button>

      </div>


      {/* INFORMATION */}
      <div className="screening-footer-note">

        <span>🔐</span>

        <div>
          <strong>Officer Decision Support</strong>

          <p>
            PramaanX provides evidence and risk indicators to assist
            authorized officers. Final decisions remain with the
            authorized officer.
          </p>
        </div>

      </div>

    </div>
  );
}

export default Screening;