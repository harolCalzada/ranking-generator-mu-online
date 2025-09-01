from __future__ import annotations
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import re

DATE_PATTERN = re.compile(r"([A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)")

@dataclass
class Event:
    ts: datetime
    killer: str
    target: str


def parse_event_line(line: str) -> Tuple[datetime, str, str] | None:
    """Parse a line like 'August 31, 2025 6:04 PM | DeadPoll -> R3APER'"""
    line = line.strip()
    if not line or "|" not in line or "->" not in line:
        return None
    try:
        date_part, action = line.split("|", 1)
        killer, target = action.split("->", 1)
    except ValueError:
        return None
    ts_match = DATE_PATTERN.search(date_part)
    if not ts_match:
        return None
    ts_str = ts_match.group(1)
    try:
        ts = datetime.strptime(ts_str, "%B %d, %Y %I:%M %p")
    except ValueError:
        # fallback: try without comma variations or leading zeros
        return None
    killer = killer.strip()
    target = target.strip()
    if not killer or not target:
        return None
    return ts, killer, target


def load_events(path: Path) -> List[Event]:
    events: List[Event] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_event_line(line)
            if parsed is None:
                continue
            ts, killer, target = parsed
            events.append(Event(ts=ts, killer=killer, target=target))
    # sort by timestamp to ensure chronological order
    events.sort(key=lambda e: e.ts)
    return events


def aggregate(events: List[Event]):
    kills = defaultdict(int)
    deaths = defaultdict(int)
    kills_by = defaultdict(Counter)   # killer -> Counter(target)
    deaths_by = defaultdict(Counter)  # target -> Counter(killer)
    for ev in events:
        kills[ev.killer] += 1
        deaths[ev.target] += 1
        kills_by[ev.killer][ev.target] += 1
        deaths_by[ev.target][ev.killer] += 1
    return kills, deaths, kills_by, deaths_by


def ranking(kills: Dict[str,int], deaths: Dict[str,int]):
    players = set(kills) | set(deaths)
    rows = []
    for p in players:
        k = kills[p]
        d = deaths[p]
        rows.append((p, k, d, k - d))
    rows.sort(key=lambda x: (x[3], x[1], -x[2], x[0].lower()), reverse=True)
    return rows


def compute_head_to_head(kills_by: Dict[str, Counter]) -> Dict[Tuple[str, str], int]:
    h2h: Dict[Tuple[str,str], int] = {}
    for killer, c in kills_by.items():
        for target, cnt in c.items():
            h2h[(killer, target)] = cnt
    return h2h


def compute_top_rivals(name: str, kills_by: Dict[str, Counter], deaths_by: Dict[str, Counter], top: int = 10):
    victims = kills_by.get(name, Counter()).most_common(top)
    killers = deaths_by.get(name, Counter()).most_common(top)
    return victims, killers


def compute_streaks(events: List[Event]):
    """Compute max kill/death streaks per player scanning chronologically.
    A kill increments killer's kill_streak and resets their death_streak.
    The target increments death_streak and resets kill_streak.
    """
    cur_kill = defaultdict(int)
    cur_death = defaultdict(int)
    max_kill = defaultdict(int)
    max_death = defaultdict(int)

    for ev in events:
        # killer gets a kill
        cur_kill[ev.killer] += 1
        max_kill[ev.killer] = max(max_kill[ev.killer], cur_kill[ev.killer])
        # a kill breaks their death streak
        cur_death[ev.killer] = 0

        # target dies
        cur_death[ev.target] += 1
        max_death[ev.target] = max(max_death[ev.target], cur_death[ev.target])
        # a death breaks their kill streak
        cur_kill[ev.target] = 0

    return max_kill, max_death


def compute_elo(events: List[Event], k_factor: float = 32.0, init_rating: float = 1000.0):
    """Simple Elo where each kill is a 'match' killer vs target (killer wins).
    Ratings evolve chronologically.
    Uses plain dict to keep results picklable for Streamlit cache.
    """
    rating: Dict[str, float] = {}

    def expected(ra: float, rb: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

    for ev in events:
        a = ev.killer
        b = ev.target
        ra = rating.get(a, init_rating)
        rb = rating.get(b, init_rating)
        ea = expected(ra, rb)
        eb = 1.0 - ea
        # killer wins (score 1), target loses (score 0)
        rating[a] = ra + k_factor * (1 - ea)
        rating[b] = rb + k_factor * (0 - eb)

    # return sorted list
    ranked = sorted(rating.items(), key=lambda x: x[1], reverse=True)
    return rating, ranked
