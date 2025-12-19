
import logging
from main import CFBRankingApp
from ranking_algorithm import TeamQualityRanker

# Monkey patch calculate_conference_quality to print std devs
original_calc = TeamQualityRanker.calculate_conference_quality

def patched_calc(self, bad_loss_map=None):
    final_cq, conf_std_devs = original_calc(self, bad_loss_map)
    print("\n--- Conference Std Devs ---")
    for conf, std in conf_std_devs.items():
        print(f"{conf}: {std:.2f}")
    return final_cq, conf_std_devs

TeamQualityRanker.calculate_conference_quality = patched_calc

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = CFBRankingApp(api_key="dummy")
    app.run_ranking(2024, None)
