import axios from "axios";
export interface HeightResult {
  estimated_height_cm: number;
  estimated_height_ft: string;
  confidence_score: number;
  pixel_height: number;
  annotated_image_base64: string;
  posture_warning: boolean;
}
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});
export async function predictHeight(
  file: File,
  cameraHeight: number,
  distance: number,
) {
  const body = new FormData();
  body.append("file", file);
  body.append("camera_height_cm", String(cameraHeight));
  body.append("distance_cm", String(distance));
  const { data } = await api.post<HeightResult>("/predict-height", body);
  return data;
}
