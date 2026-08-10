import type { Player } from "../game/gameTypes";

export function PlayerAvatar({ player, compact = false }: { player: Player; compact?: boolean }) {
  return (
    <div className={compact ? "player-pill compact" : "player-pill"}>
      <span>{player.avatar}</span>
      <strong>{player.name}</strong>
      {player.simulated && <small>SIM</small>}
    </div>
  );
}
