import { authenticatedRequest } from "./client";
import type { BarSize, LabourRateEntry, MaterialEntry, RebarShape } from "./types";

const BASE = "/drawings-boq";

function send(method: string, payload?: unknown): RequestInit {
  return payload === undefined ? { method } : { method, body: JSON.stringify(payload) };
}

export function listMaterials(): Promise<MaterialEntry[]> {
  return authenticatedRequest<MaterialEntry[]>(`${BASE}/material-library`);
}

export function createMaterial(payload: Record<string, unknown>): Promise<MaterialEntry> {
  return authenticatedRequest<MaterialEntry>(`${BASE}/material-library`, send("POST", payload));
}

export function updateMaterial(id: string, payload: Record<string, unknown>): Promise<MaterialEntry> {
  return authenticatedRequest<MaterialEntry>(`${BASE}/material-library/${id}`, send("PATCH", payload));
}

export function listLabourRates(): Promise<LabourRateEntry[]> {
  return authenticatedRequest<LabourRateEntry[]>(`${BASE}/labour-rates`);
}

export function createLabourRate(payload: Record<string, unknown>): Promise<LabourRateEntry> {
  return authenticatedRequest<LabourRateEntry>(`${BASE}/labour-rates`, send("POST", payload));
}

export function updateLabourRate(id: string, payload: Record<string, unknown>): Promise<LabourRateEntry> {
  return authenticatedRequest<LabourRateEntry>(`${BASE}/labour-rates/${id}`, send("PATCH", payload));
}

export function listBarSizes(): Promise<BarSize[]> {
  return authenticatedRequest<BarSize[]>(`${BASE}/rebar/bar-sizes`);
}

export function createBarSize(payload: Record<string, unknown>): Promise<BarSize> {
  return authenticatedRequest<BarSize>(`${BASE}/rebar/bar-sizes`, send("POST", payload));
}

export function listRebarShapes(): Promise<RebarShape[]> {
  return authenticatedRequest<RebarShape[]>(`${BASE}/rebar/shapes`);
}

export function createRebarShape(payload: Record<string, unknown>): Promise<RebarShape> {
  return authenticatedRequest<RebarShape>(`${BASE}/rebar/shapes`, send("POST", payload));
}