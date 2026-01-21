import nfl_data_py as nfl
import pandas as pd
import matplotlib.pyplot as plt

def load_and_filter_field_goals(year):
    """
    Load NFL play-by-play data for the specified year and filter for field goal attempts.
    """
    # Load play-by-play data
    data = nfl.import_pbp_data([year])
    field_goals = data[data['play_type'] == 'field_goal']
    return field_goals

def analyze_field_goal_distances(field_goals):
    """
    Analyze field goal attempts and makes by distance buckets.
    """
    # Create distance buckets
    bins = [0, 29, 39, 49, 54, 59, 99]
    labels = ["<30", "30-39", "40-49", "50-54", "55-59", "60+"]
    field_goals['distance_bucket'] = pd.cut(field_goals['kick_distance'], bins=bins, labels=labels, right=False)

    # Calculate attempts and makes
    fg_summary = field_goals.groupby('distance_bucket').agg(
        attempts=('play_id', 'count'),
        makes=('field_goal_result', lambda x: (x == 'made').sum())
    ).reset_index()

    # Calculate success rate
    fg_summary['success_rate'] = (fg_summary['makes'] / fg_summary['attempts']) * 100
    return fg_summary

def plot_field_goal_summary(fg_summary, year):
    """
    Plot field goal attempts and makes by distance buckets with success rate.
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Bar chart for attempts and makes
    ax1.bar(fg_summary['distance_bucket'], fg_summary['attempts'], label="Attempts", alpha=0.6, color='blue')
    ax1.bar(fg_summary['distance_bucket'], fg_summary['makes'], label="Makes", alpha=0.6, color='green')

    # Add labels and legend
    ax1.set_title(f"Field Goal Attempts and Makes by Distance ({year})", fontsize=14)
    ax1.set_xlabel("Distance Bucket", fontsize=12)
    ax1.set_ylabel("Count", fontsize=12)
    ax1.legend(loc='upper left')

    # Secondary axis for success rate
    ax2 = ax1.twinx()
    ax2.plot(fg_summary['distance_bucket'], fg_summary['success_rate'], label="Success Rate", color='red', marker='o')
    ax2.set_ylabel("Success Rate (%)", fontsize=12)
    ax2.set_ylim(0, 100)  # Set the range of the right Y-axis

    # Add a legend for the secondary axis
    ax2.legend(loc='upper right')

    # Improve layout
    plt.tight_layout()
    plt.show()

def main():
    # Ask user for the year
    year = int(input("Enter the year to analyze field goals: "))
    
    # Load and filter data
    field_goals = load_and_filter_field_goals(year)

    # Analyze distances
    fg_summary = analyze_field_goal_distances(field_goals)

    # Print summary table
    print(f"\nField Goal Summary for {year}:\n", fg_summary)

    # Plot results
    plot_field_goal_summary(fg_summary, year)

if __name__ == "__main__":
    main()
