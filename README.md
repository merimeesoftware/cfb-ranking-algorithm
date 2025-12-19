# CFB Ranking System

An algorithmic college football ranking system that implements a mathematically pure approach to team and conference rankings based on the mathematical model described in Idea.md.

## Overview

This application creates college football rankings using a dynamic team quality scoring system that:

1. **Adjusts scores based on opponent quality** - Beating stronger teams yields greater rewards
2. **Accounts for home/away performance** - Away wins are valued more than home wins
3. **Factors in conference strength** - Teams get credit for their conference's collective strength
4. **Optional ATS (Against The Spread) consideration** - Teams can earn bonuses for exceeding expectations

The system processes games sequentially through the season week-by-week, allowing teams' scores to evolve organically. This creates a ranking system that reflects the interconnected nature of college football performance.

## Installation

### Prerequisites

- Python 3.8+
- College Football Data (CFBD) API key - Get one at [collegefootballdata.com](https://collegefootballdata.com)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/CFB-Ranking-System.git
   cd CFB-Ranking-System
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up your API key:
   - Create a `.env` file in the project root
   - Add your CFBD API key: `CFBD_API_KEY=your_api_key_here

4. Start up the app
    - run command `python app.py` for web app.

## Usage

### Basic Command

Generate rankings for a specific year:

```
python main.py --year 2023
```

This will display the top 25 team rankings and conference rankings for the entire 2023 season.

### Common Options

```
python main.py --year 2023 --week 10  # Rankings through week 10
python main.py --year 2023 --save     # Save rankings to JSON file
python main.py --year 2023 --charts   # Generate visualization charts
python main.py --year 2023 --top 50   # Show top 50 teams instead of just 25
python main.py --year 2023 --compare "Michigan" "Ohio State"  # Compare two teams
```

### Full Command Options

```
usage: main.py [-h] --year YEAR [--week WEEK] [--output-dir OUTPUT_DIR] [--save] [--charts]
               [--ats] [--exclude-fcs] [--top TOP] [--compare TEAM1 TEAM2]

CFB Ranking System

options:
  -h, --help            show this help message and exit
  --year YEAR           Season year
  --week WEEK           Week number (omit for full season)
  --output-dir OUTPUT_DIR
                        Output directory (default: ranking_results)
  --save                Save rankings to file
  --charts              Generate charts
  --ats                 Use Against The Spread performance
  --exclude-fcs         Exclude FCS games
  --top TOP             Number of teams to display (default: 25)
  --compare TEAM1 TEAM2
                        Compare two teams

Advanced Configuration:
  --power-conf-initial POWER_CONF_INITIAL
                        Initial quality score for Power conferences
  --group5-initial GROUP5_INITIAL
                        Initial quality score for Group of 5 conferences
  --fcs-initial FCS_INITIAL
                        Initial quality score for FCS conferences
  --home-win-factor HOME_WIN_FACTOR
                        Score adjustment factor for home wins
  --away-win-factor AWAY_WIN_FACTOR
                        Score adjustment factor for away wins
  --conference-weight CONFERENCE_WEIGHT
                        Weight of conference quality in final score
```

## Examples

### Generate Season Rankings with Charts

Generate complete rankings for the 2023 season with visualization charts:

```
python main.py --year 2023 --charts --save
```

This will:
- Process all games from the 2023 season
- Display team and conference rankings
- Save the ranking data to a JSON file
- Generate visualization charts in the `ranking_results` directory

### Mid-Season Rankings

Generate rankings through week 8 of the 2022 season:

```
python main.py --year 2022 --week 8
```

### Custom Parameters

Adjust the model parameters to modify how quality scores are calculated:

```
python main.py --year 2023 --power-conf-initial 95 --group5-initial 75 --conference-weight 0.7
```

### Team Comparison

Compare two specific teams:

```
python main.py --year 2023 --compare "Georgia" "Alabama"
```

This will display a detailed comparison table and create a radar chart showing relative strengths.

## Understanding the Outputs

### Team Rankings Table

The team rankings include:

- **Rank** - Team's position in the ranking
- **Team** - Team name
- **Conference** - Conference affiliation
- **Record** - Overall win-loss record
- **Conf Record** - Conference win-loss record
- **vs P5/G5/FCS** - Records against Power 5, Group of 5, and FCS opponents
- **Team Quality** - Team's intrinsic quality score
- **Conf Quality** - Conference quality score
- **Final Score** - Final ranking score (team quality + weighted conference quality)

### Conference Rankings Table

The conference rankings include:

- **Rank** - Conference's position in the ranking
- **Conference** - Conference name
- **Teams** - Number of teams in the conference
- **Total Record** - Collective record of all teams
- **vs P5/G5/FCS** - Collective records against each tier of competition
- **Win%** - Win percentages against each tier
- **Quality Score** - Mean of member teams' quality scores

## Math Behind the Rankings (Version 5.1 Lean Pure)

See the [ALGORITHM_BREAKDOWN.md](ALGORITHM_BREAKDOWN.md) file for detailed explanation of the mathematical model.

Key components:

1.  **Master Formula**
    -   `FRS = (0.65 * TeamQuality) + (0.27 * RecordScore) + (0.08 * ConferenceQuality)`

2.  **Team Quality (Elo)**
    -   **Expectation:** $E_A = 1 / (1 + 10 ^ ((R_B - R_A) / 400))$
    -   **Update:** $\Delta = K \times MatchupWeight \times MoV \times (Actual - Expected)$
    -   **Iterative Solver:** Season is simulated 2 times to ensure convergence.

3.  **Resume (Record Score)**
    -   Rewards winning percentage, strength of schedule, and quality wins.
    -   **Milestone Multipliers:** Boosts for Undefeated seasons (1.05x) and Conference Championships.

4.  **Conference Quality**
    -   `CQ = Mean_Elo - (0.15 * StdDev)`
    -   Rewards depth and penalizes high variance (cannibalization).

## Advanced Customization

The model can be customized with the following parameters:

- `--power-conf-initial`: Initial quality score for Power 4 conferences (default: 1500)
- `--group5-initial`: Initial quality score for Group of 5 conferences (default: 1200)
- `--fcs-initial`: Initial quality score for FCS conferences (default: 900)
- `--base-factor`: Base K-factor for Elo updates (default: 40.0)
- `--conference-weight`: Weight of conference quality in final score (default: 0.08)

## License

[MIT License](LICENSE)

## Acknowledgements

- College Football Data API ([collegefootballdata.com](https://collegefootballdata.com))
- NCAA API integration for additional data sources when needed