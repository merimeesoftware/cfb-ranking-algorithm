from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker

p = CFBDataProcessor()
games = p.get_games_for_season(2025, 15)
r = TeamQualityRanker()
for g in games:
    r.update_quality_scores(g)

h = r.team_stats['Indiana']
print(f"Indiana: {h['quality_score']:.1f} ({h['wins']}-{h['losses']})")
