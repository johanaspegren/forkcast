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
  downvotes: number;
  status: "ACTIVE" | "LOCKED";
};

export type PlayerSession = {
  player_id: string;
  voting_points_remaining: number;
  meal_cards: string[];
  action_cards: string[];
  action_cards_played: string[];
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
  max_players: number;
  starting_voting_points: number;
  max_selected_meals: number;
};
