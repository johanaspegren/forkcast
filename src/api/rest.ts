import type { GameMode, SavedWeek, SchoolMenu, Session } from "../game/gameTypes";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  meals: () => request("/api/meals"),
  schoolMenu: (url: string) => request<SchoolMenu>(`/api/school-menu?url=${encodeURIComponent(url)}`),
  savedWeeks: () => request<SavedWeek[]>("/api/saved-weeks"),
  getSavedWeek: (savedWeekId: string) => request<SavedWeek>(`/api/saved-weeks/${savedWeekId}`),
  saveWeek: (sessionId: string, year: number, week: number) =>
    request<SavedWeek>("/api/saved-weeks", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, year, week })
    }),
  createSession: (maxSelectedMeals = 3, gameMode: GameMode = "CLASSIC_DRAFT") =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ max_selected_meals: maxSelectedMeals, game_mode: gameMode })
    }),
  getSession: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}`),
  join: (sessionId: string, name: string) =>
    request<Session>(`/api/sessions/${sessionId}/join`, {
      method: "POST",
      body: JSON.stringify({ name })
    }),
  addSimulatedPlayers: (sessionId: string) =>
    request<Session>(`/api/sessions/${sessionId}/simulate/add-players`, { method: "POST" }),
  simulateNext: (sessionId: string) =>
    request<Session>(`/api/sessions/${sessionId}/simulate/next`, { method: "POST" }),
  start: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/start`, { method: "POST" }),
  selectMeals: (sessionId: string, playerId: string, mealIds: string[]) =>
    request<Session>(`/api/sessions/${sessionId}/meal-selection`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, meal_ids: mealIds })
    }),
  placeMeals: (
    sessionId: string,
    playerId: string,
    placements: Array<{ meal_id: string; day: string; points: number }>
  ) =>
    request<Session>(`/api/sessions/${sessionId}/placement`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, placements })
    }),
  continueReveal: (sessionId: string) =>
    request<Session>(`/api/sessions/${sessionId}/reveal/continue`, { method: "POST" }),
  realtimeHeart: (sessionId: string, playerId: string, proposalId: string) =>
    request<Session>(`/api/sessions/${sessionId}/realtime/heart`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, proposal_id: proposalId })
    }),
  realtimeFreeze: (sessionId: string, playerId: string, proposalId: string) =>
    request<Session>(`/api/sessions/${sessionId}/realtime/freeze`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, proposal_id: proposalId })
    }),
  realtimeOverride: (sessionId: string, playerId: string, windowId: string) =>
    request<Session>(`/api/sessions/${sessionId}/realtime/override`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, window_id: windowId })
    }),
  realtimeTick: (sessionId: string) =>
    request<Session>(`/api/sessions/${sessionId}/realtime/tick`, { method: "POST" }),
  vote: (sessionId: string, playerId: string, proposalId: string, kind: "support" | "withdraw" | "downvote") =>
    request<Session>(`/api/sessions/${sessionId}/vote`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, proposal_id: proposalId, kind })
    }),
  playCard: (
    sessionId: string,
    payload: {
      player_id: string;
      card: string;
      proposal_id?: string;
      day?: string;
      target_day?: string;
      meal_id?: string;
    }
  ) =>
    request<Session>(`/api/sessions/${sessionId}/cards/play`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  passTurn: (sessionId: string, playerId: string) =>
    request<Session>(`/api/sessions/${sessionId}/pass-turn`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId })
    }),
  lockDay: (
    sessionId: string,
    playerId: string,
    day: string,
    proposalId: string,
    ruleExceptions: string[] = []
  ) =>
    request<Session>(`/api/sessions/${sessionId}/lock-day`, {
      method: "POST",
      body: JSON.stringify({
        player_id: playerId,
        day,
        proposal_id: proposalId,
        rule_exceptions: ruleExceptions
      })
    }),
  generalAssembly: (sessionId: string, playerId: string, ruleId: string, points: number) =>
    request<Session>(`/api/sessions/${sessionId}/general-assembly`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, rule_id: ruleId, points })
    }),
  unlockDay: (sessionId: string, playerId: string, day: string) =>
    request<Session>(`/api/sessions/${sessionId}/unlock-day`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, day })
    }),
  complete: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/complete`, { method: "POST" })
};
