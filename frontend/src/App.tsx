import { ChangeEvent, DragEvent, useEffect, useState, useRef, MouseEvent as ReactMouseEvent } from "react";
import { Camera, ImageUp, LoaderCircle, Ruler, Settings2, ZoomIn, ZoomOut, Maximize, AlertTriangle } from "lucide-react";
import { HeightResult, predictHeight } from "./services/api";

export default function App() {
  const [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState<string | null>(null),
    [results, setResults] = useState<{file: File, result: HeightResult}[]>([]),
    [cameraHeight, setCameraHeight] = useState(140),
    [distance, setDistance] = useState(200),
    [loading, setLoading] = useState(false),
    [error, setError] = useState<string | null>(null);

  // Zoom and Pan state
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(next: File | undefined) {
    if (!next) return;
    if (!next.type.startsWith("image/")) {
      setError("Please select an image file.");
      return;
    }
    setFile(next);
    setError(null);
  }

  function drop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    selectFile(e.dataTransfer.files[0]);
  }

  async function analyze() {
    if (!file) {
      setError("Choose a full-body image first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await predictHeight(file, cameraHeight, distance);
      setResults(prev => {
        const newResults = [...prev, { file, result: res }];
        // Keep only the last two results for comparison
        if (newResults.length > 2) {
          return newResults.slice(-2);
        }
        return newResults;
      });
      // Reset zoom/pan when new result is added
      resetZoom();
    } catch (err: unknown) {
      const data = (
        err as { response?: { data?: { error?: string; detail?: string } } }
      ).response?.data;
      setError(
        data?.error ??
          data?.detail ??
          "Unable to reach the API. Start the FastAPI server and try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleZoomIn() { setScale(s => Math.min(s + 0.5, 4)); }
  function handleZoomOut() { setScale(s => Math.max(s - 0.5, 1)); }
  function resetZoom() { setScale(1); setPosition({ x: 0, y: 0 }); }

  function handleMouseDown(e: ReactMouseEvent<HTMLDivElement>) {
    if (scale <= 1) return;
    setIsDragging(true);
    dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
  }

  function handleMouseMove(e: ReactMouseEvent<HTMLDivElement>) {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y
    });
  }

  function handleMouseUp() {
    setIsDragging(false);
  }

  function clearResults() {
    setResults([]);
    resetZoom();
  }

  const latestResult = results[results.length - 1];

  return (
    <main>
      <header>
        <div className="brand">
          <Ruler />
          Height<span>Vision</span>
        </div>
        <p>Human height estimation from a single image</p>
      </header>
      <section className="hero">
        <div>
          <b>CAPSTONE PROJECT</b>
          <h1>
            Estimate height with <em>computer vision.</em>
          </h1>
          <p>
            Upload a clear full-body photo, then use the camera details for an
            informed geometric estimate.
          </p>
        </div>
        <Camera />
      </section>
      
      {results.length === 2 && (
        <section className="comparison-view">
          <h2>Compare Images</h2>
          <div className="compare-grid">
            {results.map((r, i) => (
              <div key={i} className="panel result compare-panel">
                <img
                  src={`data:image/jpeg;base64,${r.result.annotated_image_base64}`}
                  alt={`Result ${i + 1}`}
                />
                <div className="height">
                  {r.result.estimated_height_cm} <small>cm</small>
                </div>
                <strong>{r.result.estimated_height_ft}</strong>
                {r.result.posture_warning && (
                  <div className="warning">
                    <AlertTriangle size={16} /> Posture Warning: Bent knees
                  </div>
                )}
                <p>File: {r.file.name}</p>
              </div>
            ))}
          </div>
          <button onClick={clearResults} className="clear-btn">Clear Comparison</button>
        </section>
      )}

      <section className="workspace">
        <div className="panel">
          <h2>
            <ImageUp />
            Source image
          </h2>
          <label
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={drop}
          >
            {preview ? (
              <img src={preview} alt="Selected subject" />
            ) : (
              <>
                <ImageUp size={38} />
                <strong>Drop a full-body photo here</strong>
                <small>or click to browse · JPG, PNG, WEBP</small>
              </>
            )}
            <input
              type="file"
              accept="image/*"
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                selectFile(e.target.files?.[0])
              }
            />
          </label>
          {file && <p>{file.name}</p>}
        </div>
        <div className="panel">
          <h2>
            <Settings2 />
            Camera settings
          </h2>
          <label>
            Camera height <span>{cameraHeight} cm</span>
            <input
              type="number"
              min="30"
              max="500"
              value={cameraHeight}
              onChange={(e) => setCameraHeight(Number(e.target.value))}
            />
          </label>
          <label>
            Subject distance <span>{distance} cm</span>
            <input
              type="number"
              min="30"
              max="2000"
              value={distance}
              onChange={(e) => setDistance(Number(e.target.value))}
            />
          </label>
          <button onClick={analyze} disabled={loading}>
            {loading ? (
              <>
                <LoaderCircle className="spin" />
                Analysing…
              </>
            ) : (
              <>
                <Ruler />
                Estimate height
              </>
            )}
          </button>
          {error && <p className="error">{error}</p>}
        </div>
        <div className="panel result">
          <h2>
            <Camera />
            Processed result
          </h2>
          {latestResult ? (
            <>
              <div 
                className="zoom-container"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <img
                  className={isDragging ? 'dragging' : ''}
                  style={{
                    transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                    cursor: scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default'
                  }}
                  src={`data:image/jpeg;base64,${latestResult.result.annotated_image_base64}`}
                  alt="Height analysis overlay"
                  draggable={false}
                />
                <div className="zoom-controls">
                  <button onClick={handleZoomIn} title="Zoom In"><ZoomIn size={18} /></button>
                  <button onClick={handleZoomOut} title="Zoom Out"><ZoomOut size={18} /></button>
                  <button onClick={resetZoom} title="Reset Zoom"><Maximize size={18} /></button>
                </div>
              </div>
              <div className="height">
                {latestResult.result.estimated_height_cm} <small>cm</small>
              </div>
              <strong>{latestResult.result.estimated_height_ft}</strong>
              <p>
                Confidence: {Math.round(latestResult.result.confidence_score * 100)}% ·{" "}
                {latestResult.result.pixel_height}px detected height
              </p>
              {latestResult.result.posture_warning && (
                  <div className="warning">
                    <AlertTriangle size={16} /> Posture Warning: Legs are bent, which may reduce accuracy.
                  </div>
              )}
            </>
          ) : (
            <div className="empty">
              Your annotated image and prediction will appear here.
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
