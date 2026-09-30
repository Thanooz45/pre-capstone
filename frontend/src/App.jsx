import { useEffect, useState } from "react";
import { Camera, ImageUp, LoaderCircle, Ruler, Settings2, AlertTriangle, CheckCircle, UploadCloud, ChevronRight, Database } from "lucide-react";
import { predictBody, submitFeedback } from "./services/api";

export default function App() {
  const [tab, setTab] = useState("predict"); // 'predict' or 'add_data'
  const [mode, setMode] = useState("height_weight"); // 'height_only' or 'height_weight'
  
  const [file, setFile] = useState(null);
  const [fileSide, setFileSide] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewSide, setPreviewSide] = useState(null);
  
  const [cameraHeight, setCameraHeight] = useState(140);
  const [distance, setDistance] = useState(200);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Feedback/Add Data State
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [actualHeight, setActualHeight] = useState("");
  const [actualWeight, setActualWeight] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreview(null);
    }
  }, [file]);

  useEffect(() => {
    if (fileSide) {
      const url = URL.createObjectURL(fileSide);
      setPreviewSide(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewSide(null);
    }
  }, [fileSide]);

  function handleFileDrop(e, type) {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith("image/")) {
      type === "front" ? setFile(droppedFile) : setFileSide(droppedFile);
      setError(null);
    } else {
      setError("Please select an image file.");
    }
  }

  async function analyze() {
    if (!file) {
      setError("Please upload a front-view image.");
      return;
    }
    if (mode === "height_weight" && !fileSide) {
      setError("Please upload a side-view image for better weight prediction.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setFeedbackSubmitted(false);
    
    try {
      const res = await predictBody(file, mode === "height_weight" ? fileSide : null, cameraHeight, distance);
      setResult(res);
      setTimeout(() => setShowFeedback(true), 2500);
    } catch (err) {
      const data = err.response?.data;
      setError(data?.error ?? data?.detail ?? "Unable to reach the server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDataSubmit(e) {
    e.preventDefault();
    if (!file) {
      alert("Please provide at least a front image.");
      return;
    }
    if (!actualHeight || !actualWeight) return;
    
    setFeedbackLoading(true);
    try {
      let hCm = parseFloat(actualHeight);
      let wKg = parseFloat(actualWeight);
      
      await submitFeedback(file, fileSide, hCm, wKg, cameraHeight, distance);
      setShowFeedback(false);
      setFeedbackSubmitted(true);
      if (tab === "add_data") {
        setActualHeight("");
        setActualWeight("");
        setFile(null);
        setFileSide(null);
        alert("Data successfully added to the dataset!");
      }
    } catch (err) {
      alert("Failed to submit data. Please try again.");
    } finally {
      setFeedbackLoading(false);
    }
  }

  return (
    <main>
      <header>
        <div className="brand">
          <Ruler size={28} strokeWidth={2.5} />
          Body<span>Vision</span>
        </div>
        <p>Premium Human Body Estimation</p>
      </header>

      <section className="hero">
        <div>
          <b>CAPSTONE PROJECT</b>
          <h1>
            Estimate measurements <em>instantly.</em>
          </h1>
          <p>
            Upload a clear full-body photo to calculate height using camera geometry.
            For precise weight estimation, we recommend providing both a front and side profile.
          </p>
        </div>
        <Camera />
      </section>

      <div className="tabs" style={{ marginBottom: '10px' }}>
        <button 
          className={`tab ${tab === 'predict' ? 'active' : ''}`}
          onClick={() => { setTab('predict'); setError(null); setResult(null); setFeedbackSubmitted(false); }}
        >
          <Camera size={18} /> Predict Measurements
        </button>
        <button 
          className={`tab ${tab === 'add_data' ? 'active' : ''}`}
          onClick={() => { setTab('add_data'); setMode('height_weight'); setError(null); setResult(null); setFeedbackSubmitted(false); setShowFeedback(false); }}
        >
          <Database size={18} /> Add Training Data
        </button>
      </div>

      {tab === 'predict' && (
        <div className="tabs">
          <button 
            className={`tab ${mode === 'height_only' ? 'active' : ''}`}
            onClick={() => { setMode('height_only'); setFileSide(null); }}
          >
            Height Only (1 Image)
          </button>
          <button 
            className={`tab ${mode === 'height_weight' ? 'active' : ''}`}
            onClick={() => setMode('height_weight')}
          >
            Height & Weight (2 Images) 
          </button>
        </div>
      )}

      <section className="workspace">
        <div className="panel">
          <h2><ImageUp /> Source Images</h2>
          
          <div style={{ display: "flex", gap: "10px", marginBottom: "15px" }}>
            <label style={{ flex: 1, fontSize: "0.9rem" }}>
              <strong>Front View</strong> (Required)
            </label>
            {mode === 'height_weight' && (
              <label style={{ flex: 1, fontSize: "0.9rem" }}>
                <strong>Side View</strong> (Required)
              </label>
            )}
          </div>

          <div className={mode === "height_weight" ? "images-row" : ""}>
            <div>
              <label className="dropzone" onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleFileDrop(e, "front")}>
                {preview ? (
                  <img src={preview} alt="Front view" />
                ) : (
                  <>
                    <ImageUp size={32} />
                    <strong>Front View</strong>
                    <small>Click or Drag</small>
                  </>
                )}
                <input type="file" accept="image/*" onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])} />
              </label>
            </div>

            {mode === "height_weight" && (
              <div>
                <label className="dropzone" onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleFileDrop(e, "side")}>
                  {previewSide ? (
                    <img src={previewSide} alt="Side view" />
                  ) : (
                    <>
                      <ImageUp size={32} />
                      <strong>Side View</strong>
                      <small>Click or Drag</small>
                    </>
                  )}
                  <input type="file" accept="image/*" onChange={(e) => e.target.files?.[0] && setFileSide(e.target.files[0])} />
                </label>
              </div>
            )}
          </div>
          
        </div>

        {tab === 'predict' ? (
          <>
            <div className="panel">
              <h2><Settings2 /> Camera & Settings</h2>
              
              <label>
                Camera height <span>{cameraHeight} cm</span>
                <input type="number" min="30" max="500" value={cameraHeight} onChange={(e) => setCameraHeight(Number(e.target.value))} />
              </label>
              <label>
                Subject distance <span>{distance} cm</span>
                <input type="number" min="30" max="2000" value={distance} onChange={(e) => setDistance(Number(e.target.value))} />
              </label>
              
              <button onClick={analyze} disabled={loading} style={{ marginTop: '20px' }}>
                {loading ? <><LoaderCircle className="spin" /> Analysing…</> : <><Ruler /> Predict Measurements</>}
              </button>
              
              {error && <div className="error">{error}</div>}
            </div>

            <div className="panel result">
              <h2><Camera /> Processed Result</h2>
              {result ? (
                <>
                  <div className={result.annotated_image_base64_side ? "images-row" : ""}>
                    <div>
                      <img src={`data:image/jpeg;base64,${result.annotated_image_base64}`} alt="Front Analysis" style={{ borderRadius: '12px' }} />
                    </div>
                    {result.annotated_image_base64_side && (
                      <div>
                        <img src={`data:image/jpeg;base64,${result.annotated_image_base64_side}`} alt="Side Analysis" style={{ borderRadius: '12px' }} />
                      </div>
                    )}
                  </div>

                  <div className="height">
                    {result.estimated_height_cm} <small>cm</small>
                    <br />
                    <span style={{ fontSize: '1.5rem', color: '#6b7280' }}>{result.estimated_height_ft}</span>
                  </div>

                  {mode === 'height_weight' && (
                    <div className="weight">
                      {result.estimated_weight_kg} <small>kg</small>
                      <br />
                      <span style={{ fontSize: '1.2rem', color: '#6b7280' }}>{result.estimated_weight_lb} lbs</span>
                      <p style={{ fontSize: '0.9rem', marginTop: '4px' }}>
                        Range: {result.weight_estimate_range_kg[0]} - {result.weight_estimate_range_kg[1]} kg
                      </p>
                    </div>
                  )}

                  {result.posture_warning && (
                    <div className="error" style={{ color: '#d97706', background: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '16px' }}>
                      <AlertTriangle size={18} /> Posture Warning: Legs are bent, which may reduce accuracy.
                    </div>
                  )}

                  {!feedbackSubmitted ? (
                    <button 
                      onClick={() => setShowFeedback(true)} 
                      className="button-secondary"
                      style={{ marginTop: '16px' }}
                    >
                      <Database size={18} /> Correct these measurements?
                    </button>
                  ) : (
                    <div className="feedback-banner">
                      <h3><CheckCircle size={20} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: '6px' }}/> Thank you!</h3>
                      <p style={{ margin: 0 }}>Your data has been submitted and the system is retraining in the background.</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty">
                  <UploadCloud size={48} opacity={0.3} style={{ marginBottom: '16px' }} />
                  Upload images and click predict to see results here.
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="panel" style={{ gridColumn: 'span 2' }}>
            <h2><Database /> Submit Sample Data</h2>
            <p>Upload a person's photos along with their actual verified measurements. This will append the data to the dataset and trigger automatic retraining.</p>
            
            <form onSubmit={handleDataSubmit} style={{ maxWidth: '600px' }}>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Camera Height (cm)
                  </label>
                  <input type="number" value={cameraHeight} onChange={(e) => setCameraHeight(Number(e.target.value))} required />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Subject Distance (cm)
                  </label>
                  <input type="number" value={distance} onChange={(e) => setDistance(Number(e.target.value))} required />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Actual Height (cm)
                  </label>
                  <input 
                    type="number" step="0.1" required
                    value={actualHeight} 
                    onChange={e => setActualHeight(e.target.value)} 
                    placeholder="e.g. 175" 
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Actual Weight (kg)
                  </label>
                  <input 
                    type="number" step="0.1" required
                    value={actualWeight} 
                    onChange={e => setActualWeight(e.target.value)} 
                    placeholder="e.g. 70" 
                  />
                </div>
              </div>

              <button type="submit" disabled={feedbackLoading}>
                {feedbackLoading ? <LoaderCircle className="spin" /> : <>Add to Dataset & Retrain <Database size={18} /></>}
              </button>
            </form>
          </div>
        )}
      </section>

      {/* Feedback Modal for Predict Tab */}
      {showFeedback && tab === 'predict' && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Help us improve! 🚀</h3>
            <p>Were these measurements precise? You can submit your actual height and weight to help the system learn continuously.</p>
            
            <form onSubmit={handleDataSubmit}>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Actual Height (cm)
                  </label>
                  <input 
                    type="number" step="0.1" required
                    value={actualHeight} 
                    onChange={e => setActualHeight(e.target.value)} 
                    placeholder="175" 
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Actual Weight (kg)
                  </label>
                  <input 
                    type="number" step="0.1" required
                    value={actualWeight} 
                    onChange={e => setActualWeight(e.target.value)} 
                    placeholder="70" 
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="button-secondary" onClick={() => setShowFeedback(false)} disabled={feedbackLoading}>
                  Skip
                </button>
                <button type="submit" disabled={feedbackLoading}>
                  {feedbackLoading ? <LoaderCircle className="spin" /> : <>Submit Data <ChevronRight size={18} /></>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
