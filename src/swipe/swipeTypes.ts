export type Verdict = "dislike" | "like" | "superlike";

export type DeckCard = {
  meal_id: string;
  name: string;
  emoji: string;
  thumb_url: string | null;
  minutes: number | null;
  servings: number | null;
  protein: string | null;
  is_fish: boolean;
  is_minced: boolean;
  previous_verdict: Verdict | null;
};

export type SwipeMember = {
  member_id: string;
  name: string;
  avatar: string;
  verdicts: Record<string, { verdict: Verdict; updated_at: string }>;
};

export type MemberSummary = {
  member_id: string;
  name: string;
  avatar: string;
  swiped_total: number;
  swiped_this_round: boolean;
  remaining_in_deck: number;
};

export type DayPick = {
  day: string;
  meal_id: string;
  meal_name: string;
  meal_emoji: string;
  chef: string[];
  cleanup: string[];
  reason: string | null;
};

export type WeekCandidate = {
  picks: DayPick[];
  satisfaction: Record<string, number>;
  members_without_a_win: string[];
  rule_exceptions: string[];
  mean_satisfaction: number;
};

export type SwipeRound = {
  week_id: string;
  year: number;
  week: number;
  status: "collecting" | "proposed" | "locked";
  participants: string[];
  verdicts_revision: number;
  proposal: WeekCandidate | null;
  proposal_revision: number | null;
  proposal_ai_used: boolean;
  rerolls: number;
  shown_sets: string[][];
  updated_at: string | null;
};

export type RoundView = {
  round: SwipeRound;
  members: MemberSummary[];
  proposal_stale: boolean;
  note: string | null;
};
