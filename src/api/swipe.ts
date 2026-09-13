import type { DeckCard, RoundView, SwipeMember, Verdict } from "../swipe/swipeTypes";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export const swipeApi = {
  members: () => request<SwipeMember[]>("/api/swipe/members"),
  register: (name: string, avatar: string, memberId?: string) =>
    request<SwipeMember>("/api/swipe/members", {
      method: "POST",
      body: JSON.stringify({ name, avatar, member_id: memberId ?? null })
    }),
  summary: (memberId: string) =>
    request<DeckCard[]>(`/api/swipe/summary?member_id=${encodeURIComponent(memberId)}`),
  deck: (memberId: string) => request<DeckCard[]>(`/api/swipe/deck?member_id=${encodeURIComponent(memberId)}`),
  sendVerdicts: (memberId: string, weekId: string, year: number, week: number, verdicts: Record<string, Verdict>) =>
    request<RoundView>("/api/swipe/verdicts", {
      method: "POST",
      body: JSON.stringify({ member_id: memberId, week_id: weekId, year, week, verdicts })
    }),
  getRound: (weekId: string, year: number, week: number) =>
    request<RoundView>(`/api/swipe/rounds/${weekId}?year=${year}&week=${week}`),
  propose: (weekId: string, year: number, week: number) =>
    request<RoundView>(`/api/swipe/rounds/${weekId}/propose`, {
      method: "POST",
      body: JSON.stringify({ year, week })
    }),
  reroll: (weekId: string, year: number, week: number, day?: string) =>
    request<RoundView>(`/api/swipe/rounds/${weekId}/reroll`, {
      method: "POST",
      body: JSON.stringify({ year, week, day: day ?? null })
    }),
  volunteer: (weekId: string, year: number, week: number, day: string, memberId: string, role: "chef" | "cleanup") =>
    request<RoundView>(`/api/swipe/rounds/${weekId}/volunteer`, {
      method: "POST",
      body: JSON.stringify({ year, week, day, member_id: memberId, role })
    }),
  enhance: (weekId: string, year: number, week: number) =>
    request<RoundView>(`/api/swipe/rounds/${weekId}/enhance`, {
      method: "POST",
      body: JSON.stringify({ year, week })
    }),
  confirm: (weekId: string, year: number, week: number) =>
    request<RoundView>(`/api/swipe/rounds/${weekId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ year, week })
    })
};
