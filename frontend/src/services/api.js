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

export async function submitFeedback(
  file,
  fileSide,
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
  body.append("actual_height_cm", String(actualHeight));
  body.append("actual_weight_kg", String(actualWeight));
  body.append("camera_height_cm", String(cameraHeight));
  body.append("distance_cm", String(distance));
  const { data } = await api.post("/submit-feedback", body);
  return data;
}
