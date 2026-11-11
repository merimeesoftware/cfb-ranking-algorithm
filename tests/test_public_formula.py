"""Published formula numbers and conference-row labels stay tied to the code."""

import json
import subprocess
from pathlib import Path

from conference_label import conference_row_tier
from ranking_algorithm import MATCHUP_WEIGHTS, TeamQualityRanker
from ranking_service import DEFAULT_CONFIG

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / 'frontend' / 'src' / 'lib' / 'publicFormula.json'
RANKINGS = ROOT / 'frontend' / 'static' / 'rankings'
TOLERANCE = 1e-9


def _formula():
    return json.loads(FORMULA_PATH.read_text(encoding='utf-8'))


def test_public_formula_matches_ranker_defaults():
    ranker = TeamQualityRanker(dict(DEFAULT_CONFIG))
    formula = _formula()
    assert formula['team_quality_weight'] == ranker.team_quality_weight
    assert formula['record_weight'] == ranker.record_weight
    assert formula['conference_weight'] == ranker.conference_weight
    assert formula['base_factor'] == ranker.base_factor
    assert formula['hfa_elo'] == ranker.hfa_elo
    assert formula['hfa_postseason'] == ranker.hfa_postseason
    assert formula['upset_bonus_mult'] == ranker.upset_bonus_mult
    assert formula['upset_elo_threshold'] == ranker.upset_elo_threshold
    assert formula['g5_beats_p4_mult'] == ranker.g5_beats_p4_mult
    assert formula['power_conf_initial'] == ranker.power_conf_initial
    assert formula['group5_initial'] == ranker.group_five_initial
    assert formula['fcs_initial'] == ranker.fcs_initial
    assert formula['prior_strength'] == ranker.prior_strength
    assert formula['postseason_k_mult'] == ranker.postseason_k_mult
    assert formula['elo_clamp_max'] == ranker.elo_clamp_max
    assert formula['matchup_p4_p4'] == MATCHUP_WEIGHTS['p4_p4']
    assert formula['matchup_p4_g5'] == MATCHUP_WEIGHTS['p4_g5']
    assert formula['matchup_g5_g5'] == MATCHUP_WEIGHTS['g5_g5']
    assert formula['matchup_fbs_fcs'] == MATCHUP_WEIGHTS['fbs_fcs']
    assert formula['matchup_fcs_fcs'] == MATCHUP_WEIGHTS['fcs_fcs']
    weight_sum = (
        formula['team_quality_weight']
        + formula['record_weight']
        + formula['conference_weight']
    )
    assert abs(weight_sum - 1.0) < TOLERANCE


def test_shown_parts_sum_to_published_score_for_every_stored_week():
    formula = _formula()
    look_w = formula['team_quality_weight']
    resume_w = formula['record_weight']
    league_w = formula['conference_weight']
    weeks = [
        path
        for path in RANKINGS.glob('*/*.json')
        if path.name.startswith('week-') and path.name.count('.') == 1
    ]
    assert weeks, 'expected stored week files'
    checked = 0
    for path in weeks:
        payload = json.loads(path.read_text(encoding='utf-8'))
        teams = payload.get('team_rankings') or payload.get('teams') or []
        assert teams, path.name
        for team in teams:
            parts = (
                look_w * team['team_quality_score']
                + resume_w * team['record_score']
                + league_w * team['conference_quality_score']
            )
            assert abs(parts - team['final_ranking_score']) < TOLERANCE, (
                path.name,
                team.get('team_name'),
            )
            checked += 1
    assert checked > 1000


def test_frontend_conference_label_matches_python_and_stored_weeks():
    cases = [
        ('FBS Independents', 'Power 4', ['Power 4', 'Power 4'], 'Mixed'),
        ('FBS Independents', 'Power 4', ['Power 4'], 'Power 4'),
        ('FBS Independents', 'Power 4', ['Power 4', 'Group of 5'], 'Mixed'),
        ('FBS Independents', 'Group of 5', ['Group of 5', 'Group of 5'], 'Group of 5'),
        ('SEC', 'Power 4', ['Power 4', 'Power 4'], 'Power 4'),
        ('FCS Independents', 'FCS', ['FCS'], 'FCS'),
        ('Sun Belt', 'Group of 5', [], 'Group of 5'),
    ]
    for conference, stored, members, expected in cases:
        assert conference_row_tier(conference, stored, members) == expected

    script = """
import { conferenceRowTier } from './frontend/src/lib/conferenceLabel.js';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const cases = JSON.parse(process.argv[1]);
for (const [conference, stored, members, expected] of cases) {
  const got = conferenceRowTier(conference, stored, members);
  if (got !== expected) {
    console.error('case', conference, stored, members, got, expected);
    process.exit(1);
  }
}
const root = 'frontend/static/rankings';
let rows = 0;
for (const year of readdirSync(root)) {
  const dir = join(root, year);
  let names;
  try { names = readdirSync(dir); } catch { continue; }
  for (const name of names) {
    if (!/^week-\\d+\\.json$/.test(name)) continue;
    const data = JSON.parse(readFileSync(join(dir, name), 'utf8'));
    const teams = data.team_rankings || [];
    for (const conf of data.conference_rankings || []) {
      const members = teams
        .filter((t) => t.conference === conf.conference_name)
        .map((t) => t.conference_type || '');
      const label = conferenceRowTier(conf.conference_name, conf.conference_type || '', members);
      if (conf.conference_name === 'FBS Independents') {
        rows += 1;
        const distinct = [...new Set(members.filter(Boolean))];
        const legacyMixed = distinct.length === 1 && distinct[0] === 'Power 4' && members.length > 1;
        if ((distinct.length > 1 || legacyMixed) && label !== 'Mixed') {
          console.error(name, label, members);
          process.exit(1);
        }
      }
    }
  }
}
if (rows < 1) {
  console.error('no independents rows');
  process.exit(1);
}
console.log('ok', rows);
"""
    completed = subprocess.run(
        ['node', '--input-type=module', '-e', script, json.dumps(cases)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_ui_does_not_hardcode_retired_formula_numbers():
    modal = (ROOT / 'frontend/src/lib/components/TeamDetailModal.svelte').read_text(encoding='utf-8')
    page = (ROOT / 'frontend/src/routes/methodology/+page.svelte').read_text(encoding='utf-8')
    blob = modal + '\n' + page
    for stale in ('65%', '27%', '(8%)', '1.25', '1.20', '* 0.65', '* 0.27', '* 0.08'):
        assert stale not in blob, stale
    assert 'Base volatility = 40' not in blob
    assert '65 Elo' not in blob
