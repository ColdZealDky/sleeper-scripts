import requests
import json
import matplotlib.pyplot as plt
import os
import numpy as np

# Sleeper API Base URL
BASE_URL = "https://api.sleeper.app/v1"

def get_matchups(league_id, week):
    """
    Fetch matchups for a specific week.
    """
    url = f"{BASE_URL}/league/{league_id}/matchups/{week}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_players():
    """
    Load player data from a local file if it exists; otherwise, fetch it from the Sleeper API and save it to a file.
    """
    file_name = "player_database.json"
    if os.path.exists(file_name):
        print(f"Loading player data from {file_name}...")
        with open(file_name, "r") as f:
            return json.load(f)
    else:
        print(f"{file_name} not found. Fetching data from Sleeper API...")
        url = f"{BASE_URL}/players/nfl"
        response = requests.get(url)
        if response.status_code == 200:
            player_data = response.json()
            with open(file_name, "w") as f:
                json.dump(player_data, f, indent=4)
            print(f"Player data saved to {file_name}.")
            return player_data
        else:
            print("Failed to fetch player data from Sleeper API.")
            return None

def find_scores_by_position(league_id, players, start_week, end_week, position):
    """
    Retrieve highest and 12th-highest scores by position for each week.
    """
    weekly_scores = []

    for week in range(start_week, end_week + 1):
        matchups = get_matchups(league_id, week)
        if not matchups:
            print(f"Failed to fetch matchups for week {week}.")
            continue

        position_scores = []

        for matchup in matchups:
            players_points = matchup.get("players_points", {})
            for player_id, score in players_points.items():
                player_info = players.get(player_id, {})
                if player_info.get("position") == position:  # Check if the player matches the position
                    position_scores.append(score)

        if position_scores:
            position_scores.sort(reverse=True)  # Sort scores in descending order
            highest_score = position_scores[0]
            twelfth_highest_score = position_scores[11] if len(position_scores) >= 12 else None
            weekly_scores.append({
                "week": week,
                "highest_score": highest_score,
                "12th_highest_score": twelfth_highest_score
            })
        else:
            print(f"No {position} scores found for week {week}.")
            weekly_scores.append({
                "week": week,
                "highest_score": None,
                "12th_highest_score": None
            })

    return weekly_scores

def plot_scores(weekly_kicker_scores, weekly_te_scores):
    """
    Plot highest and 12th-highest kicker and TE scores by week, with average lines.
    """
    weeks = [entry["week"] for entry in weekly_kicker_scores]
    kicker_highest = [entry["highest_score"] for entry in weekly_kicker_scores]
    kicker_12th = [entry["12th_highest_score"] for entry in weekly_kicker_scores]

    te_highest = [entry["highest_score"] for entry in weekly_te_scores]
    te_12th = [entry["12th_highest_score"] for entry in weekly_te_scores]

    bar_width = 0.2  # Width of each bar
    group_spacing = 0.5  # Space between kicker and TE groups

    # Calculate averages (ignore None values)
    avg_kicker_highest = np.mean([score for score in kicker_highest if score is not None])
    avg_kicker_12th = np.mean([score for score in kicker_12th if score is not None])
    avg_te_highest = np.mean([score for score in te_highest if score is not None])
    avg_te_12th = np.mean([score for score in te_12th if score is not None])

    # Calculate positions
    kicker_positions = [x for x in weeks]
    kicker_highest_pos = [x - bar_width / 2 for x in kicker_positions]
    kicker_12th_pos = [x + bar_width / 2 for x in kicker_positions]

    te_positions = [x + group_spacing for x in weeks]
    te_highest_pos = [x - bar_width / 2 for x in te_positions]
    te_12th_pos = [x + bar_width / 2 for x in te_positions]

    # Plot bars
    plt.figure(figsize=(14, 8))
    plt.bar(kicker_highest_pos, kicker_highest, width=bar_width, label="K Highest Scorer", color="blue")
    plt.bar(kicker_12th_pos, kicker_12th, width=bar_width, label="K 12th Highest Scorer", color="cyan")
    plt.bar(te_highest_pos, te_highest, width=bar_width, label="TE Highest Scorer", color="orange")
    plt.bar(te_12th_pos, te_12th, width=bar_width, label="TE 12th Highest Scorer", color="red")

    # Add labels for the data points
    for x, y in zip(kicker_highest_pos, kicker_highest):
        if y is not None:
            plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=8)
    for x, y in zip(kicker_12th_pos, kicker_12th):
        if y is not None:
            plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=8)
    for x, y in zip(te_highest_pos, te_highest):
        if y is not None:
            plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=8)
    for x, y in zip(te_12th_pos, te_12th):
        if y is not None:
            plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=8)

    # Add average lines
    plt.axhline(avg_kicker_highest, color="blue", linestyle="--", linewidth=1.5, label=f"Avg K Highest: {avg_kicker_highest:.1f}")
    plt.axhline(avg_kicker_12th, color="cyan", linestyle="--", linewidth=1.5, label=f"Avg K 12th: {avg_kicker_12th:.1f}")
    plt.axhline(avg_te_highest, color="orange", linestyle="--", linewidth=1.5, label=f"Avg TE Highest: {avg_te_highest:.1f}")
    plt.axhline(avg_te_12th, color="red", linestyle="--", linewidth=1.5, label=f"Avg TE 12th: {avg_te_12th:.1f}")

    # Graph customization
    plt.title("Kicker and TE Scores by Week (Grouped)", fontsize=16)
    plt.xlabel("Week", fontsize=14)
    plt.ylabel("Score", fontsize=14)
    plt.xticks(weeks, fontsize=12)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.show()


def main():
    # Michigan Misfits
    # league_id = "1050127292493721600"
    
    # Dummy
    league_id = "1079247134282686464"
    start_week = 1
    end_week = 17

    # Fetch player data
    print("Fetching player data...")
    players = get_players()
    if not players:
        print("Failed to fetch player data.")
        return

    # Find kicker and TE scores for each week
    print("Processing kicker scores...")
    weekly_kicker_scores = find_scores_by_position(league_id, players, start_week, end_week, "K")

    print("Processing TE scores...")
    weekly_te_scores = find_scores_by_position(league_id, players, start_week, end_week, "TE")

    # Plot results
    plot_scores(weekly_kicker_scores, weekly_te_scores)

if __name__ == "__main__":
    main()
