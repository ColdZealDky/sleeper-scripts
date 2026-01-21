import requests
import json

# Sleeper API Base URL
BASE_URL = "https://api.sleeper.app/v1"

def get_rosters(league_id):
    """
    Fetch rosters for the league.
    """
    url = f"{BASE_URL}/league/{league_id}/rosters"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_matchups(league_id, week):
    """
    Fetch matchups for a specific week.
    """
    url = f"{BASE_URL}/league/{league_id}/matchups/{week}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def process_matchups(league_id, max_week):
    """
    Process matchups to calculate game results, record, and division records.
    """
    rosters = get_rosters(league_id)
    if not rosters:
        print("Failed to fetch rosters.")
        return None

    roster_divisions = {roster["roster_id"]: roster.get("settings", {}).get("division", "Unknown") for roster in rosters}

    standings = {roster_id: {
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "division_wins": 0,
        "division_losses": 0,
        "division_ties": 0
    } for roster_id in roster_divisions.keys()}

    for week in range(1, max_week + 1):
        matchups = get_matchups(league_id, week)
        if not matchups:
            print(f"Failed to fetch matchups for week {week}.")
            continue

        for matchup in matchups:
            roster_id = matchup["roster_id"]
            points = matchup["points"]
            opponent_id = matchup.get("matchup_id")
            opponent_points = None

            # Find opponent's points
            if opponent_id:
                opponent_matchup = next((m for m in matchups if m["roster_id"] == opponent_id), None)
                if opponent_matchup:
                    opponent_points = opponent_matchup["points"]

            if opponent_points is None:
                print(f"Could not determine opponent points for roster ID {roster_id} in week {week}.")
                continue

            # Determine win, loss, or tie
            if points > opponent_points:
                standings[roster_id]["wins"] += 1
                standings[opponent_id]["losses"] += 1
            elif points < opponent_points:
                standings[roster_id]["losses"] += 1
                standings[opponent_id]["wins"] += 1
            else:
                standings[roster_id]["ties"] += 1
                standings[opponent_id]["ties"] += 1

            # Update division record if applicable
            if roster_divisions[roster_id] == roster_divisions[opponent_id]:
                if points > opponent_points:
                    standings[roster_id]["division_wins"] += 1
                    standings[opponent_id]["division_losses"] += 1
                elif points < opponent_points:
                    standings[roster_id]["division_losses"] += 1
                    standings[opponent_id]["division_wins"] += 1
                else:
                    standings[roster_id]["division_ties"] += 1
                    standings[opponent_id]["division_ties"] += 1

    return standings

def save_to_file(data, filename):
    """
    Save data to a JSON file.
    """
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def main():
    league_id = "1050127292493721600"
    max_week = int(input("Enter the maximum week to process: "))

    standings = process_matchups(league_id, max_week)
    if standings:
        output_filename = f"standings_division_records_week_{max_week}.json"
        save_to_file(standings, output_filename)
        print(f"Standings and division records saved to '{output_filename}'.")

if __name__ == "__main__":
    main()
