import type { Session } from "../game/gameTypes";

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
  createSession: (maxSelectedMeals = 3) =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ max_selected_meals: maxSelectedMeals })
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
  complete: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/complete`, { method: "POST" })
};
