"""Workers AI daily Neurons stay under 8,000."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_workers_ai_neurons import evaluate, live_spec, main, worst_case_neurons  # noqa: E402

FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'workers_ai_neurons_over.json'


def test_planted_over_neuron_fixture_fails():
    spec = json.loads(FIXTURE.read_text(encoding='utf-8'))
    per_call = worst_case_neurons(
        spec['max_input_tokens'],
        spec['max_output_tokens'],
        spec['neurons_per_million_input'],
        spec['neurons_per_million_output'],
    )
    assert spec['calls_per_day'] * per_call > spec['ceiling']
    assert evaluate(spec)


def test_live_config_stays_under_8000():
    spec = live_spec()
    assert spec['errors'] == []
    assert spec['calls_per_day'] == 100
    per_call = worst_case_neurons(
        spec['max_input_tokens'],
        spec['max_output_tokens'],
        spec['neurons_per_million_input'],
        spec['neurons_per_million_output'],
    )
    assert per_call == 58
    assert spec['calls_per_day'] * per_call == 5800
    assert spec['calls_per_day'] * per_call <= spec['ceiling']
    assert main() == 0
