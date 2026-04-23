import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";
import type { Equipment } from "../../types/equipment";

interface Props {
  equipment: Equipment[];
  incidents: Incident[];
  isLoading?: boolean;
}

type TileStatus = "critical" | "warning" | "processing" | "ok";

interface EquipmentTile {
  equipmentId: string;
  equipmentName: string;
  tileStatus: TileStatus;
  activeCount: number;
}

function resolveTileStatus(incidents: Incident[]): TileStatus {
  if (incidents.some((i) => i.status === "escalated")) return "critical";
  if (incidents.some((i) => i.status === "pending_approval")) return "critical";
  if (incidents.some((i) => i.severity === "critical" || i.severity === "major")) return "warning";
  if (
    incidents.some((i) =>
      ["analyzing", "awaiting_agents", "ingested", "open"].includes(i.status)
    )
  )
    return "processing";
  return "ok";
}

const TILE_STATUS_LABEL: Record<TileStatus, string> = {
  critical: "Action Required",
  warning: "Warning",
  processing: "Processing",
  ok: "OK",
};

const STATUS_SORT: Record<TileStatus, number> = {
  critical: 0,
  warning: 1,
  processing: 2,
  ok: 3,
};

export default function EquipmentHealthGrid({ equipment, incidents, isLoading = false }: Props) {
  const tiles = useMemo<EquipmentTile[]>(() => {
    const byEquip: Record<string, Incident[]> = {};
    for (const inc of incidents) {
      if (!byEquip[inc.equipment_id]) byEquip[inc.equipment_id] = [];
      byEquip[inc.equipment_id].push(inc);
    }
    const equipmentById = new Map(equipment.map((asset) => [asset.id, asset]));
    const inventory = [...equipment];

    for (const equipmentId of Object.keys(byEquip)) {
      if (!equipmentById.has(equipmentId)) {
        inventory.push({ id: equipmentId, name: equipmentId });
      }
    }

    return inventory
      .map((asset) => {
        const assetIncidents = byEquip[asset.id] ?? [];
        return {
          equipmentId: asset.id,
          equipmentName: asset.name || asset.id,
          tileStatus: assetIncidents.length > 0 ? resolveTileStatus(assetIncidents) : "ok",
          activeCount: assetIncidents.length,
        };
      })
      .sort(
        (a, b) =>
          STATUS_SORT[a.tileStatus] - STATUS_SORT[b.tileStatus] ||
          a.equipmentId.localeCompare(b.equipmentId),
      );
  }, [equipment, incidents]);

  if (isLoading) {
    return (
      <div className="equipment-health-empty">
        Loading equipment inventory…
      </div>
    );
  }

  if (tiles.length === 0) {
    return (
      <div className="equipment-health-empty">
        No active equipment incidents.
      </div>
    );
  }

  return (
    <div className="equipment-health-grid">
      {tiles.map((tile) => (
        <Link
          key={tile.equipmentId}
          to={`/history?equipment_id=${encodeURIComponent(tile.equipmentId)}`}
          className={`eq-tile eq-tile--${tile.tileStatus}`}
          title={tile.equipmentName}
        >
          <span className="eq-tile-id">{tile.equipmentId}</span>
          <span className={`eq-tile-status-dot eq-tile-status-dot--${tile.tileStatus}`} />
          <span className="eq-tile-label">{TILE_STATUS_LABEL[tile.tileStatus]}</span>
          <span className="eq-tile-count">
            {tile.activeCount > 0
              ? `${tile.activeCount} incident${tile.activeCount !== 1 ? "s" : ""}`
              : "No active incidents"}
          </span>
        </Link>
      ))}
    </div>
  );
}
