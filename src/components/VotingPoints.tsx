import type { PlayerSession } from "../game/gameTypes";
import { uiAssets } from "../uiAssets";

export function VotingPoints({ state }: { state?: PlayerSession }) {
  return (
    <div className="vp-bank">
      <img src={uiAssets.votingPoint} alt="" aria-hidden="true" />
      <span>Voting Points</span>
      <strong>{state?.voting_points_remaining ?? 0}</strong>
    </div>
  );
}
