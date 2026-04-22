import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";

interface Props {
  incidents: Incident[];
}

type TileStatus = "critical" | "warning" | "processing" | "ok";

interface EquipmentTile {
  equipmentId: string;
  tileStatus: TileStatus;
  activeCount: number;
  worstSeverity: string;
  worstStatus: string;
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

export default function EquipmentHealthGrid({ incidents }: Props) {
  const tiles = useMemo<EquipmentTile[]>(() => {
    const byEquip: Record<string, Incident[]> = {};
    for (const inc of incidents) {
      if (!byEquip[inc.equipment_id]) byEquip[inc.equipment_id] = [];
      byEquip[inc.equipment_id].push(inc);
    }
    return Object.entries(byEquip)
      .map(([equipmentId, incs]) => ({
        equipmentId,
        tileStatus: resolveTileStatus(incs),
        activeCount: incs.length,
        worstSeverity: incs.find((i) => i.severity === "critical")?.severity ??
          incs.find((i) => i.severity === "major")?.severity ??
          incs[0]?.severity ?? "minor",
        worstStatus: incs.find((i) => i.status === "escalated")?.status ??
          incs.find((i) => i.status === "pending_approval")?.status ??
          incs.find((i) => i.status === "analyzing")?.status ??
          incs[0]?.status ?? "open",
      }))
      .sort((a, b) => STATUS_SORT[a.tileStatus] - STATUS_SORT[b.tileStatus]);
  }, [incidents]);

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
        >
          <span className="eq-tile-id">{tile.equipmentId}</span>
          <span className={`eq-tile-status-dot eq-tile-status-dot--${tile.tileStatus}`} />
          <span className="eq-tile-label">{TILE_STATUS_LABEL[tile.tileStatus]}</span>
          <span className="eq-tile-count">
            {tile.activeCount} incident{tile.activeCount !== 1 ? "s" : ""}
          </span>
        </Link>
      ))}
    </div>
  );
}
