export type GamePhase =
  | "LOBBY"
  | "MEAL_SELECTION"
  | "SECRET_PLACEMENT"
  | "REVEAL"
  | "NEGOTIATION"
  | "REALTIME_RUSH"
  | "FINAL_VOTE"
  | "COMPLETE";

export type GameMode = "CLASSIC_DRAFT" | "REALTIME_RUSH";

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

export type RealtimeOverrideWindow = {
  id: string;
  rule_id: string;
  proposal_ids: string[];
  message: string;
  opened_at: number;
  closes_at: number;
  votes: Record<string, boolean>;
  threshold: number;
  status: "OPEN" | "PASSED" | "FAILED";
};

export type RealtimeStats = {
  hearts_by_player: Record<string, number>;
  hearts_by_proposal: Record<string, number>;
  own_hearts_by_player: Record<string, number>;
  freezes_by_player: Record<string, number>;
  awards: string[];
};

export type Session = {
  id: string;
  join_code: string;
  phase: GamePhase;
  game_mode: GameMode;
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
  rule_overrides: string[];
  general_assembly: Record<string, Record<string, number>>;
  general_assembly_threshold: number;
  realtime_started_at: number | null;
  realtime_ends_at: number | null;
  realtime_freeze_until: Record<string, number>;
  realtime_freezes_used: string[];
  realtime_override_window: RealtimeOverrideWindow | null;
  realtime_stats: RealtimeStats;
};

export type SchoolMenuCourse = {
  name: string;
  option_name: string;
  tags: string[];
  image: string | null;
};

export type SchoolMenuDay = {
  date: string;
  name: string;
  courses: SchoolMenuCourse[];
};

export type SchoolMenu = {
  source_url: string;
  start_date: string;
  end_date: string;
  distributor: string;
  days: SchoolMenuDay[];
};

export type SavedWeekEntry = {
  meal_id: string;
  meal_name: string;
  meal_emoji: string;
  chef: string[];
  cleanup: string[];
  rule_exceptions: string[];
};

export type SavedWeek = {
  id: string;
  saved_at: string;
  session_id: string;
  join_code: string;
  year: number;
  week: number;
  days: string[];
  plan: Record<string, SavedWeekEntry | null>;
  rule_overrides: string[];
};
