import React, { useState } from "react";

function Screening() {
  const [document, setDocument] = useState(null);
  const [preview, setPreview] = useState("");
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

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

    if (file.type.startsWith("image/")) {
      const imageUrl = URL.createObjectURL(file);
      setPreview(imageUrl);
    } else {
      setPreview("");
    }
  };

  const startAnalysis = () => {
    if (!document) return;

    setAnalysisStarted(true);
    setAnalysisComplete(false);
    setCurrentStep(1);

    let step = 1;

    const interval = setInterval(() => {
      step++;

      if (step <= 5) {
        setCurrentStep(step);
      }

      if (step === 5) {
        clearInterval(interval);

        setTimeout(() => {
          setAnalysisComplete(true);
        }, 1000);
      }
    }, 1200);
  };

  const clearScreening = () => {
    setDocument(null);
    setPreview("");
    setAnalysisStarted(false);
    setAnalysisComplete(false);
    setCurrentStep(0);
  };

  const getStepStatus = (index) => {
    if (!analysisStarted) return "waiting";

    if (index + 1 < currentStep) return "complete";

    if (index + 1 === currentStep) return "processing";

    return "waiting";
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


      {/* DEMO NOTICE */}
      <div className="demo-notice">
        <span>ℹ️</span>

        <div>
          <strong>Frontend Demo Mode</strong>

          <p>
            AI, OCR, MRZ, face verification and risk results are
            simulated in this frontend version. Real analysis will
            be connected through the backend later.
          </p>
        </div>
      </div>


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
            accept=".jpg,.jpeg,.png,.pdf"
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
              : "Supported formats: JPG, JPEG, PNG, PDF"}
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
              <strong>{document.type || "PDF"}</strong>
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
          </div>


          <div className="screening-results-grid">

            <div className="result-card">
              <span className="result-icon">📄</span>
              <span>Document Quality</span>
              <strong>
                {analysisComplete ? "Good" : "Processing"}
              </strong>
            </div>

            <div className="result-card">
              <span className="result-icon">🔤</span>
              <span>OCR & MRZ</span>
              <strong>
                {analysisComplete ? "Validated" : "Processing"}
              </strong>
            </div>

            <div className="result-card">
              <span className="result-icon">🛡️</span>
              <span>Tampering</span>
              <strong>
                {analysisComplete ? "No Result Yet" : "Processing"}
              </strong>
            </div>

            <div className="result-card">
              <span className="result-icon">👤</span>
              <span>Face Verification</span>
              <strong>
                {analysisComplete ? "Pending Capture" : "Waiting"}
              </strong>
            </div>

            <div className="result-card">
              <span className="result-icon">⚠️</span>
              <span>Risk Assessment</span>
              <strong>
                {analysisComplete ? "Pending Review" : "Waiting"}
              </strong>
            </div>

          </div>

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