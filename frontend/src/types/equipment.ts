import type { BatchDispositionStatus } from "./incident";

export interface EquipmentLocation {
  plant?: string;
  building?: string;
  room?: string;
  line?: string;
}

export interface Equipment {
  id: string;
  name: string;
  type?: string;
  location?: string | EquipmentLocation;
  status?: string;
  criticality?: string;
  validation_status?: string;
}

export interface Batch {
  id: string;
  batch_number: string;
  product: string;
  equipment_id: string;
  status: BatchDispositionStatus;
  conditions?: string[];
  started_at: string;
  updated_at: string;
}
