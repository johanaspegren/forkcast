import type { PlayerSession } from "../game/gameTypes";

export function VotingPoints({ state }: { state?: PlayerSession }) {
  return (
    <div className="vp-bank">
      <span>Voting Points</span>
      <strong>{state?.voting_points_remaining ?? 0}</strong>
    </div>
  );
}

