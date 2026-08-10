export type GamePhase =
  | "LOBBY"
  | "MEAL_SELECTION"
  | "SECRET_PLACEMENT"
  | "REVEAL"
  | "NEGOTIATION"
  | "FINAL_VOTE"
  | "COMPLETE";

export type Meal = {
  id: string;
  name: string;
  emoji: string;
  tags: string[];
  protein_type: string | null;
  minced_meat: boolean;
  fish: boolean;
};

export type Player = {
  id: string;
  name: string;
  avatar: string;
  favourite_meals: string[];
  simulated: boolean;
};

export type Proposal = {
  id: string;
  meal_id: string;
  day: string;
  owners: string[];
  voting_points: number;
  supporters: string[];
  support_points: Record<string, number>;
  downvote_points: Record<string, number>;
  downvotes: number;
  status: "ACTIVE" | "LOCKED";
  chef_volunteers: string[];
  cleanup_volunteers: string[];
};

export type PlayerSession = {
  player_id: string;
  voting_points_remaining: number;
  meal_cards: string[];
  action_cards: string[];
  action_cards_played: string[];
  cook_commitments: string[];
  clean_commitments: string[];
  selected_meals: string[];
  placed: boolean;
};

export type WeekEntry = {
  meal_id: string;
  chef: string[];
  cleanup: string[];
  rule_exceptions: string[];
};

export type RuleStatus = {
  id: string;
  label: string;
  level: string;
  satisfied: boolean;
  detail: string;
};

export type Session = {
  id: string;
  join_code: string;
  phase: GamePhase;
  days: string[];
  players: Record<string, Player>;
  player_state: Record<string, PlayerSession>;
  proposals: Record<string, Proposal>;
  week: Record<string, WeekEntry | null>;
  rules: RuleStatus[];
  turn_order: string[];
  current_turn_index: number;
  turn_log: string[];
  max_players: number;
  starting_voting_points: number;
  max_selected_meals: number;
  max_action_cards_played: number;
};
