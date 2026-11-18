import { useEffect, useState } from "react";
import { Camera, Download, ImageUp, LoaderCircle, Ruler, Settings2, AlertTriangle, CheckCircle, UploadCloud, ChevronRight, Database, Search, UsersRound, Pencil, Save, Trash2, X } from "lucide-react";
import { datasetImageUrl, deleteDatasetImage, deleteDatasetPerson, downloadTrainingDatasetCsv, getDatasetPeople, lookupDatasetPerson, predictBody, submitFeedback, updateDatasetPerson } from "./services/api";

export default function App() {
  const [tab, setTab] = useState("predict"); // 'predict', 'add_data', or 'dataset'
  const [mode, setMode] = useState("height_weight"); // 'height_only' or 'height_weight'
  
  const [file, setFile] = useState(null);
  const [fileSide, setFileSide] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewSide, setPreviewSide] = useState(null);
  const [personName, setPersonName] = useState("");
  const [lookupMatches, setLookupMatches] = useState([]);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupChecked, setLookupChecked] = useState(false);
  
  const [cameraHeight, setCameraHeight] = useState("100");
  const [distance, setDistance] = useState("150");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Feedback/Add Data State
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [actualHeight, setActualHeight] = useState("");
  const [actualWeight, setActualWeight] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [datasetSearch, setDatasetSearch] = useState("");
  const [datasetPeople, setDatasetPeople] = useState([]);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState(null);
  const [datasetTotal, setDatasetTotal] = useState(0);
  const [datasetImageCount, setDatasetImageCount] = useState(0);
  const [datasetPage, setDatasetPage] = useState(0);
  const [datasetRefresh, setDatasetRefresh] = useState(0);
  const [editingPerson, setEditingPerson] = useState(null);
  const [editPersonName, setEditPersonName] = useState("");
  const [editPersonHeight, setEditPersonHeight] = useState("");
  const [editPersonWeight, setEditPersonWeight] = useState("");
  const [personSaveLoading, setPersonSaveLoading] = useState(false);
  const [personSaveError, setPersonSaveError] = useState(null);
  const [personSaveMessage, setPersonSaveMessage] = useState(null);
  const [datasetMutation, setDatasetMutation] = useState(null);
  const [personDeleteError, setPersonDeleteError] = useState(null);
  const [imageDeleteError, setImageDeleteError] = useState(null);
  const [datasetDownloadLoading, setDatasetDownloadLoading] = useState(false);
  const [datasetDownloadError, setDatasetDownloadError] = useState(null);
  const [selectedDatasetImage, setSelectedDatasetImage] = useState(null);

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

  useEffect(() => {
    if (!selectedDatasetImage) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setSelectedDatasetImage(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedDatasetImage]);

  useEffect(() => {
    if (tab !== "dataset") return undefined;

    let active = true;
    const timer = setTimeout(() => {
      setDatasetLoading(true);
      setDatasetError(null);
      getDatasetPeople(datasetSearch, 50, datasetPage * 50)
        .then((data) => {
          if (!active) return;
          setDatasetPeople(data.people);
          setDatasetTotal(data.total);
          setDatasetImageCount(data.image_count);
        })
        .catch(() => {
          if (active) setDatasetError("Unable to load the dataset. Check that the backend is running.");
        })
        .finally(() => {
          if (active) setDatasetLoading(false);
        });
    }, 200);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [tab, datasetSearch, datasetPage, datasetRefresh]);

  useEffect(() => {
    if (tab !== "predict" || !file) return undefined;

    let active = true;
    setLookupLoading(true);
    setLookupChecked(false);
    lookupDatasetPerson(file)
      .then((data) => {
        if (!active) return;
        setLookupMatches(data.matches);
        setLookupChecked(true);
      })
      .catch(() => {
        if (active) setLookupMatches([]);
      })
      .finally(() => {
        if (active) setLookupLoading(false);
      });

    return () => {
      active = false;
    };
  }, [file, tab]);

  function handleFileDrop(e, type) {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith("image/")) {
      if (type === "front") {
        setFile(droppedFile);
        setLookupMatches([]);
        setLookupChecked(false);
      } else {
        setFileSide(droppedFile);
      }
      setError(null);
    } else {
      setError("Please select an image file.");
    }
  }

  async function checkExistingPerson() {
    if (!file) {
      setError("Upload a front-view image first.");
      return;
    }
    setLookupLoading(true);
    setLookupChecked(false);
    setError(null);
    try {
      const data = await lookupDatasetPerson(file, personName);
      setLookupMatches(data.matches);
      setLookupChecked(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Unable to search the saved dataset.");
    } finally {
      setLookupLoading(false);
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
    setShowFeedback(false);
    
    try {
      const res = await predictBody(file, mode === "height_weight" ? fileSide : null, cameraHeight, distance);
      setResult(res);
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
    if (!personName.trim()) {
      alert("Please enter the person's name.");
      return;
    }
    const includeWeight = tab === "add_data" || mode === "height_weight";
    if (!actualHeight || (includeWeight && !actualWeight)) return;
    
    setFeedbackLoading(true);
    try {
      const hCm = parseFloat(actualHeight);
      const wKg = includeWeight ? parseFloat(actualWeight) : null;
      
      const feedbackMode = includeWeight ? "height_weight" : "height_only";
      const response = await submitFeedback(file, fileSide, personName, hCm, wKg, cameraHeight, distance, feedbackMode);
      setShowFeedback(false);
      setFeedbackSubmitted(true);
      setDatasetRefresh((value) => value + 1);
      setLookupMatches([]);
      setLookupChecked(false);
      if (tab === "add_data") {
        setActualHeight("");
        setActualWeight("");
        setFile(null);
        setFileSide(null);
        setPersonName("");
        setError(null);
        setDatasetSearch("");
        setDatasetPage(0);
        setFeedbackSubmitted(true);
      } else {
        setPersonName(response.person_name);
        setActualHeight("");
        setActualWeight("");
      }
    } catch (err) {
      alert(err.response?.data?.detail ?? "Failed to submit data. Please try again.");
    } finally {
      setFeedbackLoading(false);
    }
  }

  function startEditingPerson(person, modelImage) {
    setEditingPerson(person.normalized_name);
    setEditPersonName(person.name);
    setEditPersonHeight(String(modelImage.height_cm ?? ""));
    setEditPersonWeight(String(modelImage.weight_kg ?? ""));
    setPersonSaveError(null);
    setPersonSaveMessage(null);
  }

  async function savePersonEdits(e) {
    e.preventDefault();
    const person = datasetPeople.find((entry) => entry.normalized_name === editingPerson);
    if (!person) return;
    setPersonSaveLoading(true);
    setPersonSaveError(null);
    setPersonSaveMessage(null);
    try {
      const response = await updateDatasetPerson(
        person.name,
        editPersonName,
        editPersonHeight,
        editPersonWeight,
      );
      setEditingPerson(null);
      setDatasetSearch(response.person_name);
      setDatasetPage(0);
      setPersonSaveMessage(`${response.person_name}'s records were updated. Model retraining has started.`);
      setDatasetRefresh((value) => value + 1);
    } catch (err) {
      setPersonSaveError(err.response?.data?.detail ?? "Unable to update this person's dataset records.");
    } finally {
      setPersonSaveLoading(false);
    }
  }

  async function deletePerson(person) {
    if (!window.confirm(
      `Delete ${person.name} and all of their training records? Images not shared with other records will also be deleted. This cannot be undone.`
    )) {
      return;
    }

    setDatasetMutation({ type: "person", key: person.normalized_name });
    setPersonDeleteError(null);
    setPersonSaveMessage(null);
    try {
      const response = await deleteDatasetPerson(person.name);
      setPersonSaveMessage(
        response.image_cleanup_errors > 0
          ? `${person.name} was removed from the training data, but some associated images could not be deleted. Model retraining has started.`
          : `${person.name} was removed from the training data. Model retraining has started.`
      );
      if (datasetPeople.length === 1 && datasetPage > 0) {
        setDatasetPage((page) => page - 1);
      }
      setDatasetRefresh((value) => value + 1);
    } catch (err) {
      setPersonDeleteError({
        name: person.normalized_name,
        message: err.response?.data?.detail ?? "Unable to delete this participant.",
      });
    } finally {
      setDatasetMutation(null);
    }
  }

  async function deletePersonImage(person, image) {
    const imageKey = `${image.dataset}/${image.name}`;
    if (!window.confirm(
      `Remove ${image.name} from ${person.name}'s training data? All training records using this image will be deleted.`
    )) {
      return;
    }

    setDatasetMutation({ type: "image", key: imageKey });
    setImageDeleteError(null);
    setPersonSaveMessage(null);
    try {
      const response = await deleteDatasetImage(image.dataset, image.name);
      setPersonSaveMessage(
        response.image_cleanup_error
          ? `${image.name} was removed from the training records, but the image file could not be deleted. Model retraining has started.`
          : `${image.name} was removed from ${person.name}'s training data. Model retraining has started.`
      );
      if (person.images.length === 1 && datasetPeople.length === 1 && datasetPage > 0) {
        setDatasetPage((page) => page - 1);
      }
      setDatasetRefresh((value) => value + 1);
    } catch (err) {
      setImageDeleteError({
        key: imageKey,
        message: err.response?.data?.detail ?? "Unable to delete this image.",
      });
    } finally {
      setDatasetMutation(null);
    }
  }

  async function downloadDatasetCsv() {
    setDatasetDownloadLoading(true);
    setDatasetDownloadError(null);
    try {
      await downloadTrainingDatasetCsv();
      setPersonSaveMessage("Training dataset CSV downloaded.");
    } catch {
      setDatasetDownloadError("Unable to download the training dataset. Check that the backend is running.");
    } finally {
      setDatasetDownloadLoading(false);
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
            To find saved measurements, enter the person's saved name or upload the exact same image.
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
        <button
          className={`tab ${tab === 'dataset' ? 'active' : ''}`}
          onClick={() => { setTab('dataset'); setDatasetSearch(""); setDatasetPage(0); setDatasetRefresh((value) => value + 1); setError(null); }}
        >
          <UsersRound size={18} /> Training Dataset
        </button>
      </div>

      {tab === 'predict' && (
        <div className="tabs">
          <button 
            className={`tab ${mode === 'height_only' ? 'active' : ''}`}
            onClick={() => { setMode('height_only'); setFileSide(null); setActualWeight(''); setFeedbackSubmitted(false); }}
          >
            Height Only (1 Image)
          </button>
          <button 
            className={`tab ${mode === 'height_weight' ? 'active' : ''}`}
            onClick={() => { setMode('height_weight'); setFeedbackSubmitted(false); }}
          >
            Height & Weight (2 Images) 
          </button>
        </div>
      )}

      {tab === "dataset" ? (
        <section className="dataset-page">
          <div className="panel dataset-header">
            <div className="dataset-header-top">
              <div className="dataset-title">
                <span className="dataset-title-icon"><UsersRound size={22} /></span>
                <div>
                  <p className="dataset-eyebrow">DATA MANAGEMENT</p>
                  <h2>Training dataset</h2>
                  <p>Review participant records, images, and measurements.</p>
                </div>
              </div>
              <button
                type="button"
                className="button-secondary dataset-download-button"
                onClick={downloadDatasetCsv}
                disabled={datasetDownloadLoading}
              >
                {datasetDownloadLoading
                  ? <LoaderCircle className="spin" size={18} />
                  : <Download size={18} />}
                {datasetDownloadLoading ? "Preparing CSV…" : "Download CSV"}
              </button>
            </div>
            <label className="dataset-search">
              <Search size={18} />
              <input
                type="text"
                value={datasetSearch}
                onChange={(event) => {
                  setDatasetSearch(event.target.value);
                  setDatasetPage(0);
                }}
                placeholder="Search names, e.g. Bhargav"
              />
            </label>
            <div className="dataset-count">
              <span><ImageUp size={16} /> {datasetImageCount} images</span>
              <span><UsersRound size={16} /> {datasetTotal}{datasetSearch ? " matching" : ""} participant{datasetTotal === 1 ? "" : "s"}</span>
              {datasetLoading && <span className="dataset-loading"><LoaderCircle className="spin" size={15} /> Refreshing…</span>}
            </div>
            {datasetError && <div className="error">{datasetError}</div>}
            {datasetDownloadError && <div className="error">{datasetDownloadError}</div>}
          </div>

          {datasetPeople.length > 0 && (
            <div className="people-grid">
              {datasetPeople.map((person) => {
                const modelImages = person.images.filter((image) => image.dataset === "model_specification");
                const modelImage = modelImages.find((image) => image.weight_kg != null) ?? modelImages[0];
                const isEditing = editingPerson === person.normalized_name;
                return (
                  <article className="person-card" key={person.normalized_name}>
                    <div className="person-card-heading">
                      <div>
                        <h3>{person.name}</h3>
                        <p className="person-measurement-summary">
                          {modelImage
                            ? `Height: ${modelImage.height_cm} cm${modelImage.weight_kg != null ? ` · Weight: ${modelImage.weight_kg} kg` : ""}`
                            : person.measurements.map((measurement, index) => (
                              <span key={index}>
                                {measurement.height_cm != null && `Height: ${measurement.height_cm} cm`}
                                {measurement.height_cm != null && measurement.weight_kg != null && " · "}
                                {measurement.weight_kg != null && `Weight: ${measurement.weight_kg} kg`}
                              </span>
                            ))}
                        </p>
                      </div>
                      {!isEditing && (
                        <div className="person-card-actions">
                          {modelImage?.weight_kg != null && (
                            <button
                              type="button"
                              className="button-secondary person-edit-button"
                              onClick={() => startEditingPerson(person, modelImage)}
                            >
                              <Pencil size={16} /> Edit
                            </button>
                          )}
                          <button
                            type="button"
                            className="button-danger person-edit-button"
                            onClick={() => deletePerson(person)}
                            disabled={datasetMutation !== null}
                          >
                            {datasetMutation?.type === "person" && datasetMutation.key === person.normalized_name
                              ? <LoaderCircle className="spin" size={16} />
                              : <Trash2 size={16} />}
                            {datasetMutation?.type === "person" && datasetMutation.key === person.normalized_name
                              ? "Deleting…" : "Delete"}
                          </button>
                        </div>
                      )}
                    </div>

                    {personDeleteError?.name === person.normalized_name && (
                      <div className="error">{personDeleteError.message}</div>
                    )}
                    {isEditing && (
                      <form className="person-edit-form" onSubmit={savePersonEdits}>
                        <label>
                          Person name
                          <input value={editPersonName} onChange={(event) => setEditPersonName(event.target.value)} maxLength={100} required />
                        </label>
                        <div className="person-edit-fields">
                          <label>
                            Height (cm)
                            <input type="number" min="1" max="300" step="0.1" value={editPersonHeight} onChange={(event) => setEditPersonHeight(event.target.value)} required />
                          </label>
                          <label>
                            Weight (kg)
                            <input type="number" min="1" max="500" step="0.1" value={editPersonWeight} onChange={(event) => setEditPersonWeight(event.target.value)} required />
                          </label>
                        </div>
                        {personSaveError && <div className="error">{personSaveError}</div>}
                        <div className="person-edit-actions">
                          <button type="submit" disabled={personSaveLoading}>
                            {personSaveLoading ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />}
                            {personSaveLoading ? "Saving…" : "Save changes"}
                          </button>
                          <button type="button" className="button-secondary" onClick={() => setEditingPerson(null)} disabled={personSaveLoading}>
                            <X size={17} /> Cancel
                          </button>
                        </div>
                      </form>
                    )}

                    <div className="person-images">
                      {person.images.map((image) => {
                        const imageKey = `${image.dataset}/${image.name}`;
                        const isDeleting = datasetMutation?.type === "image" && datasetMutation.key === imageKey;
                        return (
                          <div className="person-image" key={imageKey}>
                            <div className="person-image-preview">
                              <button
                                type="button"
                                className="person-image-open"
                                onClick={() => setSelectedDatasetImage({
                                  url: datasetImageUrl(image.url),
                                  alt: `${person.name} ${image.view ?? "dataset"} image`,
                                  title: `${person.name}${image.view ? ` · ${image.view}` : ""}`,
                                })}
                                aria-label={`View full-size ${image.view ?? "dataset"} image for ${person.name}`}
                                aria-haspopup="dialog"
                              >
                                <img src={datasetImageUrl(image.url)} alt="" loading="lazy" />
                              </button>
                              <button
                                type="button"
                                className="person-image-delete"
                                onClick={() => deletePersonImage(person, image)}
                                disabled={datasetMutation !== null}
                                aria-label={`Delete ${image.name} from ${person.name}'s training data`}
                                title="Delete image"
                              >
                                {isDeleting
                                  ? <LoaderCircle className="spin" size={16} />
                                  : <Trash2 size={16} />}
                              </button>
                            </div>
                            <small>{image.view ? `${image.view} · ` : ""}{image.name}</small>
                            {imageDeleteError?.key === imageKey && (
                              <span className="image-delete-error">{imageDeleteError.message}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
          {personSaveMessage && <div className="feedback-banner dataset-save-message">{personSaveMessage}</div>}

          {!datasetLoading && !datasetError && datasetPeople.length === 0 && (
            <div className="panel empty">No matching people found.</div>
          )}

          {datasetTotal > 50 && (
            <div className="dataset-pagination">
              <button
                className="button-secondary"
                onClick={() => setDatasetPage((page) => Math.max(0, page - 1))}
                disabled={datasetPage === 0}
              >
                Previous
              </button>
              <span>Page {datasetPage + 1} of {Math.ceil(datasetTotal / 50)}</span>
              <button
                className="button-secondary"
                onClick={() => setDatasetPage((page) => page + 1)}
                disabled={(datasetPage + 1) * 50 >= datasetTotal}
              >
                Next
              </button>
            </div>
          )}
        </section>
      ) : (
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
                <input type="file" accept="image/*" onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setFile(e.target.files[0]);
                    setLookupMatches([]);
                    setLookupChecked(false);
                  }
                }} />
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
                Existing person's name (optional)
                <input
                  type="text"
                  value={personName}
                  onChange={(event) => setPersonName(event.target.value)}
                  placeholder="Enter a saved name to find their records"
                />
              </label>
              <p className="lookup-note">
                Name results depend on the name you enter. Image matching finds only an identical image file; it does not recognize faces.
              </p>
              <button type="button" className="button-secondary" onClick={checkExistingPerson} disabled={lookupLoading}>
                {lookupLoading ? <><LoaderCircle className="spin" /> Checking…</> : <><Search size={18} /> Check Existing Records</>}
              </button>
              {lookupChecked && (
                <div className="lookup-results">
                  {lookupMatches.length === 0 ? (
                    <p>No matching record found. Exact-image matching only recognizes the same image file.</p>
                  ) : (
                    lookupMatches.map((person) => (
                      <div className="lookup-person" key={person.normalized_name}>
                        <strong>
                          {person.match_type === "identical_image"
                            ? `Exact image already exists for ${person.name}`
                            : `Possible name match: ${person.name} (confirm identity)`}
                        </strong>
                        {person.measurements.map((measurement, index) => (
                          <div className="lookup-measurement" key={`${measurement.distance_cm}-${measurement.camera_height_cm}-${index}`}>
                            <p>
                              Camera height from ground: {measurement.camera_height_cm ?? "Unknown"} cm
                              {" · "}
                              Subject distance from camera: {measurement.distance_cm ?? "Unknown"} cm
                            </p>
                            <p>
                              Height: {measurement.height_cm != null ? `${measurement.height_cm} cm` : "Not recorded"}
                              {" · "}
                              Weight: {measurement.weight_kg != null ? `${measurement.weight_kg} kg` : "Not recorded"}
                            </p>
                          </div>
                        ))}
                        <small>Images: {person.images.map((image) => image.name).join(", ")}</small>
                      </div>
                    ))
                  )}
                </div>
              )}
              
              <label>
                Camera height <span>{cameraHeight || 0} cm</span>
                <input type="number" min="30" max="500" step="0.1" value={cameraHeight} onChange={(event) => setCameraHeight(event.target.value)} required />
              </label>
              <label>
                Subject distance <span>{distance || 0} cm</span>
                <input type="number" min="30" max="2000" value={distance} onChange={(e) => setDistance(e.target.value === "" ? "" : String(Number(e.target.value)))} required />
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
                      <button
                        type="button"
                        className="result-image-open"
                        onClick={() => setSelectedDatasetImage({
                          url: `data:image/jpeg;base64,${result.annotated_image_base64}`,
                          alt: "Front-view pose and height analysis with detected joints",
                          title: "Front view · Pose & height analysis",
                        })}
                        aria-label="View full-size front-view pose and height analysis"
                        aria-haspopup="dialog"
                      >
                        <img src={`data:image/jpeg;base64,${result.annotated_image_base64}`} alt="Front Analysis" />
                      </button>
                    </div>
                    {result.annotated_image_base64_side && (
                      <div>
                        <button
                          type="button"
                          className="result-image-open"
                          onClick={() => setSelectedDatasetImage({
                            url: `data:image/jpeg;base64,${result.annotated_image_base64_side}`,
                            alt: "Side-view pose and height analysis with detected joints",
                            title: "Side view · Pose & height analysis",
                          })}
                          aria-label="View full-size side-view pose and height analysis"
                          aria-haspopup="dialog"
                        >
                          <img src={`data:image/jpeg;base64,${result.annotated_image_base64_side}`} alt="Side Analysis" />
                        </button>
                      </div>
                    )}
                  </div>

                  <p style={{ textAlign: 'center', marginTop: '12px', fontSize: '0.95rem', color: '#6b7280' }}>
                    <strong>Detection/pose score:</strong> {(result.confidence_score * 100).toFixed(1)}%
                  </p>

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
                      <Database size={18} /> Help us improve
                    </button>
                  ) : (
                    <div className="feedback-banner">
                      <h3><CheckCircle size={20} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: '6px' }}/> Thank you!</h3>
                      <p style={{ margin: 0 }}>
                        {mode === "height_only"
                          ? "Your name, image, and height were saved for height calibration. No weight was collected."
                          : "Your name, image, and corrected height and weight were saved for model training."}
                      </p>
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
            <p>Enter the person's name and verified measurements. The images and measurements are added to the training CSV; front and side images are grouped under the same name.</p>
            
            <form onSubmit={handleDataSubmit} style={{ maxWidth: '600px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                Person name
                <input
                  type="text"
                  value={personName}
                  onChange={(event) => setPersonName(event.target.value)}
                  placeholder="Enter a name used to find this person later"
                  maxLength="100"
                  required
                />
              </label>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Camera Height (cm)
                  </label>
                  <input type="number" min="30" max="500" step="0.1" value={cameraHeight} onChange={(event) => setCameraHeight(event.target.value)} required />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Subject Distance (cm)
                  </label>
                  <input type="number" min="30" max="2000" value={distance} onChange={(e) => setDistance(e.target.value === "" ? "" : String(Number(e.target.value)))} required />
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
            {feedbackSubmitted && (
              <div className="feedback-banner">
                <h3><CheckCircle size={20} /> Data saved</h3>
                <p>The named person and image records were added to the training cohort. Open Training Dataset to search for them.</p>
              </div>
            )}
          </div>
        )}
      </section>
      )}

      {selectedDatasetImage && (
        <div
          className="image-lightbox"
          role="presentation"
          onClick={() => setSelectedDatasetImage(null)}
        >
          <div
            className="image-lightbox-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={`Full-size image: ${selectedDatasetImage.title}`}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="image-lightbox-header">
              <span>{selectedDatasetImage.title}</span>
              <button
                type="button"
                className="image-lightbox-close"
                onClick={() => setSelectedDatasetImage(null)}
                aria-label="Close full-size image"
                autoFocus
              >
                <X size={20} />
              </button>
            </div>
            <img className="image-lightbox-image" src={selectedDatasetImage.url} alt={selectedDatasetImage.alt} />
            <p className="image-lightbox-hint">Press Esc or click outside the image to close</p>
          </div>
        </div>
      )}

      {/* Feedback Modal for Predict Tab */}
      {showFeedback && tab === 'predict' && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Help us improve</h3>
            <p>
              {mode === "height_only"
                ? "Submit your verified height to help improve height estimates. Weight is not requested in Height Only mode."
                : "Submit your verified height and weight to help improve both estimates."}
              {" "}Your name, image, and provided measurements will be saved in the project training dataset.
            </p>
            
            <form onSubmit={handleDataSubmit}>
              <label>
                Person name
                <input
                  type="text"
                  value={personName}
                  onChange={(event) => setPersonName(event.target.value)}
                  placeholder="Enter a name used to find this person later"
                  maxLength="100"
                  required
                />
              </label>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                    Actual Height (cm)
                  </label>
                  <input 
                    type="number" min="1" max="300" step="0.1" required
                    value={actualHeight} 
                    onChange={e => setActualHeight(e.target.value)} 
                    placeholder="175" 
                  />
                </div>
                {mode === "height_weight" && (
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
                      Actual Weight (kg)
                    </label>
                    <input
                      type="number" min="1" max="500" step="0.1" required
                      value={actualWeight}
                      onChange={e => setActualWeight(e.target.value)}
                      placeholder="70"
                    />
                  </div>
                )}
              </div>

              <div className="modal-actions">
                <button type="button" className="button-secondary" onClick={() => setShowFeedback(false)} disabled={feedbackLoading}>
                  Skip
                </button>
                <button type="submit" disabled={feedbackLoading}>
                  {feedbackLoading
                    ? <LoaderCircle className="spin" />
                    : <>{mode === "height_only" ? "Submit height" : "Submit corrections"} <ChevronRight size={18} /></>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
