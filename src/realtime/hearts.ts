import { useCallback, useSyncExternalStore } from "react";

export type RealtimeHeartEvent = {
  eventId: string;
  proposalId: string;
  playerId: string;
  total: number;
  day: string;
  leaderId: string;
};

type HeartState = {
  total: number;
  bursts: RealtimeHeartEvent[];
};

const heartStates = new Map<string, HeartState>();
const listeners = new Map<string, Set<() => void>>();
const fallbackStates = new Map<string, HeartState>();
const dayLeaders = new Map<string, string>();
const dayLeaderListeners = new Map<string, Set<() => void>>();
const seenEventIds = new Set<string>();
const seenEventOrder: string[] = [];

function notify(proposalId: string) {
  listeners.get(proposalId)?.forEach((listener) => listener());
}

function notifyLeader(day: string) {
  dayLeaderListeners.get(day)?.forEach((listener) => listener());
}

function rememberEvent(eventId: string) {
  if (seenEventIds.has(eventId)) return false;
  seenEventIds.add(eventId);
  seenEventOrder.push(eventId);
  if (seenEventOrder.length > 200) {
    const oldest = seenEventOrder.shift();
    if (oldest) seenEventIds.delete(oldest);
  }
  return true;
}

function removeBurst(proposalId: string, eventId: string) {
  const current = heartStates.get(proposalId);
  if (!current || !current.bursts.some((burst) => burst.eventId === eventId)) return;
  heartStates.set(proposalId, {
    ...current,
    bursts: current.bursts.filter((burst) => burst.eventId !== eventId)
  });
  notify(proposalId);
}

export function heartTotal(proposalId: string, fallbackTotal: number) {
  return heartStates.get(proposalId)?.total ?? fallbackTotal;
}

export function publishHeart(event: RealtimeHeartEvent) {
  const current = heartStates.get(event.proposalId);
  if (dayLeaders.get(event.day) !== event.leaderId) {
    dayLeaders.set(event.day, event.leaderId);
    notifyLeader(event.day);
  }
  if (!rememberEvent(event.eventId)) {
    if (current && current.total !== event.total) {
      heartStates.set(event.proposalId, { ...current, total: event.total });
      notify(event.proposalId);
    }
    return;
  }

  const next: HeartState = {
    total: event.total,
    bursts: [...(current?.bursts ?? []), event].slice(-4)
  };
  heartStates.set(event.proposalId, next);
  notify(event.proposalId);
  window.setTimeout(() => removeBurst(event.proposalId, event.eventId), 760);
}

export function rollbackHeart(eventId: string, proposalId: string) {
  const current = heartStates.get(proposalId);
  if (!current || !current.bursts.some((burst) => burst.eventId === eventId)) return;
  heartStates.set(proposalId, {
    total: Math.max(0, current.total - 1),
    bursts: current.bursts.filter((burst) => burst.eventId !== eventId)
  });
  notify(proposalId);
}

export function useProposalHearts(proposalId: string, fallbackTotal: number) {
  const subscribe = useCallback((listener: () => void) => {
    const proposalListeners = listeners.get(proposalId) ?? new Set<() => void>();
    proposalListeners.add(listener);
    listeners.set(proposalId, proposalListeners);
    return () => {
      proposalListeners.delete(listener);
      if (proposalListeners.size === 0) listeners.delete(proposalId);
    };
  }, [proposalId]);

  const getSnapshot = useCallback(() => {
    const liveState = heartStates.get(proposalId);
    if (liveState) return liveState;
    const fallbackKey = `${proposalId}:${fallbackTotal}`;
    const existing = fallbackStates.get(fallbackKey);
    if (existing) return existing;
    const created = { total: fallbackTotal, bursts: [] };
    fallbackStates.set(fallbackKey, created);
    return created;
  }, [fallbackTotal, proposalId]);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useDayLeader(day: string, fallbackLeaderId: string) {
  const subscribe = useCallback((listener: () => void) => {
    const dayListeners = dayLeaderListeners.get(day) ?? new Set<() => void>();
    dayListeners.add(listener);
    dayLeaderListeners.set(day, dayListeners);
    return () => {
      dayListeners.delete(listener);
      if (dayListeners.size === 0) dayLeaderListeners.delete(day);
    };
  }, [day]);

  const getSnapshot = useCallback(() => dayLeaders.get(day) ?? fallbackLeaderId, [day, fallbackLeaderId]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
