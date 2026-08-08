"""Pure ranking runner for the evaluation sandbox (no API / logos / static I/O)."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from ranking_algorithm import TeamQualityRanker
from ranking_service import DEFAULT_CONFIG


def organize_by_week(games: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    by_week: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for game in games:
        by_week[int(game['week'])].append(game)
    return dict(by_week)


def games_through_week(games: List[Dict[str, Any]], week: int) -> List[Dict[str, Any]]:
    return [g for g in games if int(g['week']) <= week]


def games_in_week(games: List[Dict[str, Any]], week: int) -> List[Dict[str, Any]]:
    return [g for g in games if int(g['week']) == week]


def dynamic_prior_strength(week: Optional[int]) -> float:
    """Match ranking_service schedule: strong early, ~0 by week 12+."""
    calc_week = week if week is not None else 15
    return max(0.0, 0.7 * (12.0 - calc_week) / 11.0)


def merge_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    if overrides:
        config.update(overrides)
    return config


def rank_through_week(
    games: List[Dict[str, Any]],
    through_week: int,
    *,
    config: Optional[Dict[str, Any]] = None,
    priors: Optional[Dict[str, float]] = None,
    apply_dynamic_priors: bool = True,
) -> Tuple[Dict[str, Any], TeamQualityRanker]:
    """Recompute rankings from scratch using only games with week <= through_week.

    Mirrors ranking_service.calculate_rankings_logic iteration protocol so sandbox
    scores match production math.
    """
    subset = games_through_week(games, through_week)
    by_week = organize_by_week(subset)
    cfg = merge_config(config)
    if apply_dynamic_priors and 'prior_strength' not in (config or {}):
        cfg['prior_strength'] = dynamic_prior_strength(through_week)

    priors = priors or {}
    reference_ranks = None
    conf_stddevs: Dict[str, float] = {}
    num_iterations = TeamQualityRanker(cfg, priors).num_iterations
    ranker = TeamQualityRanker(cfg, priors)

    for i in range(num_iterations):
        ranker = TeamQualityRanker(cfg, priors)
        if conf_stddevs:
            ranker.set_conference_stddevs(conf_stddevs)
        for week_num in sorted(by_week.keys()):
            for game in by_week[week_num]:
                ranker.update_quality_scores(game, reference_ranks)
        if i < num_iterations - 1:
            temp = ranker.calculate_final_rankings()
            reference_ranks = {
                t['team_name']: t['team_quality_score']
                for t in temp['team_rankings']
            }
            conf_stddevs = ranker.compute_conference_stddevs()

    rankings = ranker.calculate_final_rankings()
    rankings = ranker.normalize_scores(rankings)
    rankings['week'] = through_week
    rankings.pop('rankings', None)
    return rankings, ranker


def ratings_from_rankings(
    rankings: Dict[str, Any],
    *,
    field: str = 'team_quality_score',
) -> Dict[str, float]:
    """Extract a name → rating map used for next-week predictions."""
    return {
        t['team_name']: float(t[field])
        for t in rankings.get('team_rankings', [])
        if field in t
    }


def preseason_ratings(
    *,
    config: Optional[Dict[str, Any]] = None,
    priors: Optional[Dict[str, float]] = None,
    team_meta: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, float]:
    """Week-0 ratings: tier initials blended with priors (no games yet).

    team_meta maps team_name -> {conference, conference_type}.
    Teams only in priors default to Power-4-like blend via prior alone.
    """
    cfg = merge_config(config)
    # Preseason uses the week-1 prior_strength schedule unless overridden
    if config is None or 'prior_strength' not in config:
        cfg['prior_strength'] = dynamic_prior_strength(1)
    priors = priors or {}
    ranker = TeamQualityRanker(cfg, priors)
    ratings: Dict[str, float] = {}

    team_meta = team_meta or {}
    names = set(priors) | set(team_meta)
    for name in names:
        meta = team_meta.get(name, {})
        conf = meta.get('conference')
        conf_type = meta.get('conference_type', 'Power 4' if name in priors else 'FCS')
        ranker._initialize_team(name, conf, conf_type)
        ratings[name] = float(ranker.team_stats[name]['quality_score'])
    return ratings
