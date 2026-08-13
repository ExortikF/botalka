export type ClanMember = {
  user_id: number;
  display_name: string;
  role: string;
  nick_color: string | null;
  prefix: string | null;
  avatar: string | null;
  frame: string | null;
  solved_week: number;
  is_you: boolean;
};

export type Clan = {
  id: number;
  name: string;
  tag: string;
  description: string | null;
  color: string;
  join_policy: string;
  max_members: number;
  members_count: number;
  points_week: number;
  average_week: number;
  active_week: number;
  your_role: string | null;
  can_join: boolean;
  requested: boolean;
  members: ClanMember[];
  requests: ClanMember[];
};

export type ClanRow = {
  place: number;
  id: number;
  name: string;
  tag: string;
  color: string;
  members_count: number;
  average_week: number;
  points_week: number;
  is_yours: boolean;
};

/** Столько же в `MIN_FOR_BOARD` на бэкенде — держим согласованным вручную. */
export const MIN_FOR_BOARD = 3;

export const POLICY: Record<string, string> = {
  open: "Любой желающий",
  request: "По заявке",
  closed: "Только по приглашению",
};

export const ROLE: Record<string, string> = {
  leader: "глава",
  officer: "офицер",
  member: "участник",
};
