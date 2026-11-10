import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});

export async function predictBody(
  file,
  fileSide,
  cameraHeight,
  distance
) {
  const body = new FormData();
  body.append("file", file);
  if (fileSide) {
    body.append("file_side", fileSide);
  }
  body.append("camera_height_cm", String(cameraHeight));
  body.append("distance_cm", String(distance));
  const { data } = await api.post("/predict-body", body);
  return data;
}

export async function getDatasetPeople(search = "", limit = 50, offset = 0) {
  const { data } = await api.get("/dataset/people", {
    params: { search: search || undefined, limit, offset },
  });
  return data;
}

export async function updateDatasetPerson(currentName, name, height, weight) {
  const { data } = await api.put("/dataset/people", {
    current_name: currentName,
    name,
    height_cm: Number(height),
    weight_kg: Number(weight),
  });
  return data;
}

export async function lookupDatasetPerson(file, personName = "") {
  const body = new FormData();
  body.append("file", file);
  body.append("person_name", personName);
  const { data } = await api.post("/dataset/lookup", body);
  return data;
}

export function datasetImageUrl(path) {
  return `${api.defaults.baseURL}${path.replace(/^\/api/, "")}`;
}

export async function submitFeedback(
  file,
  fileSide,
  personName,
  actualHeight,
  actualWeight,
  cameraHeight,
  distance
) {
  const body = new FormData();
  body.append("file", file);
  if (fileSide) {
    body.append("file_side", fileSide);
  }
  body.append("person_name", personName);
  body.append("actual_height_cm", String(actualHeight));
  body.append("actual_weight_kg", String(actualWeight));
  body.append("camera_height_cm", String(cameraHeight));
  body.append("distance_cm", String(distance));
  const { data } = await api.post("/submit-feedback", body);
  return data;
}
