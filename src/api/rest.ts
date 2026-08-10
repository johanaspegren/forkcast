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
  createSession: () => request<Session>("/api/sessions", { method: "POST" }),
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
  vote: (sessionId: string, playerId: string, proposalId: string, kind: "support" | "downvote") =>
    request<Session>(`/api/sessions/${sessionId}/vote`, {
      method: "POST",
      body: JSON.stringify({ player_id: playerId, proposal_id: proposalId, kind })
    }),
  lockDay: (
    sessionId: string,
    day: string,
    proposalId: string,
    chef: string[],
    cleanup: string[],
    ruleExceptions: string[] = []
  ) =>
    request<Session>(`/api/sessions/${sessionId}/lock-day`, {
      method: "POST",
      body: JSON.stringify({
        day,
        proposal_id: proposalId,
        chef,
        cleanup,
        rule_exceptions: ruleExceptions
      })
    }),
  complete: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/complete`, { method: "POST" })
};
