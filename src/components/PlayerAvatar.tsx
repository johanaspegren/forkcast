import type { Player } from "../game/gameTypes";
import { uiAssets } from "../uiAssets";

export function PlayerAvatar({ player, compact = false }: { player: Player; compact?: boolean }) {
  return (
    <div className={compact ? "player-pill compact" : "player-pill"}>
      <span className="player-avatar-token">
        <img src={uiAssets.defaultAvatar} alt="" aria-hidden="true" />
        <b>{player.avatar}</b>
      </span>
      <strong>{player.name}</strong>
      {player.simulated && <small>SIM</small>}
    </div>
  );
}
