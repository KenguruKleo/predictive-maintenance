import client from "./client";
import type { Equipment, Batch } from "../types/equipment";

export async function getEquipmentList(): Promise<Equipment[]> {
  const { data } = await client.get<Equipment[]>("/equipment");
  return data;
}

export async function getEquipment(id: string): Promise<Equipment> {
  const { data } = await client.get<Equipment>(`/equipment/${encodeURIComponent(id)}`);
  return data;
}

export async function getCurrentBatch(equipmentId: string): Promise<Batch> {
  const { data } = await client.get<Batch>(
    `/batches/current/${encodeURIComponent(equipmentId)}`,
  );
  return data;
}
