/**
 * ISO week helpers, shared by the game, the hallway display and the swipe round.
 *
 * There is deliberately one implementation: the swipe round is keyed by the
 * same week id the display looks up, and `getDefaultWeekOffset` means that
 * planning on a Sunday targets *next* week. A second copy of this rule would
 * drift and the produced menu would quietly fail to appear on the tablet.
 */

export function getIsoWeek(date = new Date()) {
  const normalized = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = normalized.getUTCDay() || 7;
  normalized.setUTCDate(normalized.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(normalized.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((normalized.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: normalized.getUTCFullYear(), week };
}

/** On Sundays the family is planning the week that is about to start. */
export function getDefaultWeekOffset(date = new Date()) {
  return date.getDay() === 0 ? 1 : 0;
}

export function getDisplayWeek(weekOffset = getDefaultWeekOffset(), date = new Date()) {
  const target = new Date(date);
  target.setDate(target.getDate() + weekOffset * 7);
  const { year, week } = getIsoWeek(target);
  const day = target.getDay() || 7;
  const start = new Date(target);
  start.setDate(target.getDate() - day + 1);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { year, week, start, end };
}

export function weekId(year: number, week: number) {
  return `${year}-W${String(week).padStart(2, "0")}`;
}
