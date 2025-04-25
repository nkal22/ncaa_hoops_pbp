import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import ast


def calculate_on_off_stats(df, players, team="Syracuse"):
    """
    Calculate on-off statistics for specified players for both team and their opponents.
    
    Parameters:
    -----------
    df : pandas DataFrame
        Play-by-play data frame
    players : str or list
        Player name(s) to analyze
    team : str, default="Syracuse"
        Team to analyze (e.g., "Syracuse")
        
    Returns:
    --------
    pandas DataFrame
        DataFrame containing on-off statistics with proper Net calculations
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    team_str = team
    
    # Ensure players is a list
    if isinstance(players, str):
        players = [players]
    
    # Helper function to convert time strings to seconds
    def time_to_seconds(time_str):
        if pd.isna(time_str):
            return 0
        parts = time_str.split(':')
        if len(parts) == 3:
            minutes, seconds, _ = parts
            return int(minutes) * 60 + int(seconds)
        elif len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(seconds)
        else:
            return 0
    
    # Convert time_remaining to seconds
    df['time_seconds'] = df['time_remaining'].apply(time_to_seconds)

    df[f'lineup_{team}'] = df[f'lineup_{team}'].apply(
    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
)
    
    
    # Create columns to track if players are on court
    for player in players:
        df[f'{player}_on_court'] = df[f'lineup_{team}'].apply(lambda x: player in x if isinstance(x, tuple) else False)
    
    # Calculate if ALL of the specified players are on court
    df['players_on_court'] = df[[f'{player}_on_court' for player in players]].all(axis=1)
    
    # Get the list of all opponents that team played against
    opponents = [col for col in df.columns if col.startswith('lineup_') and col != f'lineup_{team}']
    opponents = [col.replace('lineup_', '') for col in opponents]
    
    # Initialize results dictionary
    results = {
        team_str: {
            'on': {
                'minutes': 0, 'points': 0, 'rebounds': 0, 'assists': 0, 
                'steals': 0, 'blocks': 0, 'turnovers': 0,
                # Add shooting stats
                'fg_made': 0, 'fg_attempted': 0,
                '3pt_made': 0, '3pt_attempted': 0,
                'ft_made': 0, 'ft_attempted': 0,
                'rim_fg_made': 0, 'rim_fg_attempted': 0,
                'mid_range_fg_made': 0, 'mid_range_fg_attempted': 0
            },
            'off': {
                'minutes': 0, 'points': 0, 'rebounds': 0, 'assists': 0, 
                'steals': 0, 'blocks': 0, 'turnovers': 0,
                # Add shooting stats
                'fg_made': 0, 'fg_attempted': 0,
                '3pt_made': 0, '3pt_attempted': 0,
                'ft_made': 0, 'ft_attempted': 0,
                'rim_fg_made': 0, 'rim_fg_attempted': 0,
                'mid_range_fg_made': 0, 'mid_range_fg_attempted': 0
            }
        },
        'Opponents': {
            'on': {
                'minutes': 0, 'points': 0, 'rebounds': 0, 'assists': 0, 
                'steals': 0, 'blocks': 0, 'turnovers': 0,
                # Add shooting stats
                'fg_made': 0, 'fg_attempted': 0,
                '3pt_made': 0, '3pt_attempted': 0,
                'ft_made': 0, 'ft_attempted': 0,
                'rim_fg_made': 0, 'rim_fg_attempted': 0,
                'mid_range_fg_made': 0, 'mid_range_fg_attempted': 0
            },
            'off': {
                'minutes': 0, 'points': 0, 'rebounds': 0, 'assists': 0, 
                'steals': 0, 'blocks': 0, 'turnovers': 0,
                # Add shooting stats
                'fg_made': 0, 'fg_attempted': 0,
                '3pt_made': 0, '3pt_attempted': 0,
                'ft_made': 0, 'ft_attempted': 0,
                'rim_fg_made': 0, 'rim_fg_attempted': 0,
                'mid_range_fg_made': 0, 'mid_range_fg_attempted': 0
            }
        }
    }
    
    # Group by game_id to process each game separately
    for game_id, game_df in df.groupby('game_id'):
        # Sort by period and time_seconds to ensure chronological order
        game_df = game_df.copy()
        
        # For basketball, higher time_remaining means earlier in the period
        game_df = game_df.sort_values(['period', 'time_seconds'], ascending=[True, False])
        
        # Reset index for easier processing
        game_df = game_df.reset_index(drop=True)
        
        # Determine the opponent for this specific game
        opponent = None
        for opp in opponents:
            if f'lineup_{opp}' in game_df.columns and not game_df[f'lineup_{opp}'].isna().all():
                opponent = opp
                break
        
        if opponent is None:
            continue  # Skip if we can't determine the opponent
        
        # Calculate time differences between consecutive plays
        game_df['next_time'] = game_df['time_seconds'].shift(-1)
        game_df['next_period'] = game_df['period'].shift(-1)
        
        # Handle period transitions
        game_df['time_diff'] = np.where(
            game_df['period'] == game_df['next_period'],
            game_df['time_seconds'] - game_df['next_time'],
            game_df['time_seconds']  # End of period - assume it's the time_remaining until end of period
        )
        
        # Convert time_diff to minutes
        game_df['minutes_played'] = game_df['time_diff'] / 60
        
        # Remove negative time differences and last row
        game_df = game_df[:-1]  # Remove last row since it has no next_time
        game_df = game_df[game_df['minutes_played'] >= 0]
        
        # Accumulate statistics while players are on/off court
        for idx, row in game_df.iterrows():
            status = 'on' if row['players_on_court'] else 'off'
            
            # Update minutes
            results[team_str][status]['minutes'] += row['minutes_played']
            results['Opponents'][status]['minutes'] += row['minutes_played']
            
            # Process this event
            if row['team'] == team:
                # Team stats
                team_key = team_str
            else:
                # Opponent stats
                team_key = 'Opponents'
            
            # Update points
            if pd.notna(row['points']) and row['points'] != '':
                results[team_key][status]['points'] += float(row['points'])
            
            # Update other stats based on event_type
            event = str(row['event_type']).lower() if pd.notna(row['event_type']) else ''
            
            if 'rebound' in event:
                results[team_key][status]['rebounds'] += 1
            elif 'assist' in event:
                results[team_key][status]['assists'] += 1
            elif 'steal' in event:
                results[team_key][status]['steals'] += 1
            elif 'block' in event:
                results[team_key][status]['blocks'] += 1
            elif 'turnover' in event:
                results[team_key][status]['turnovers'] += 1
            
            # Track shots for FG%, 3PT%, and FT%
            if row['is_shot']:
                shot_type = str(row['shot_type']).lower() if pd.notna(row['shot_type']) else ''
                shot_outcome = str(row['shot_outcome']).lower() if pd.notna(row['shot_outcome']) else ''
                
                # Field goal tracking (all shots except free throws)
                if 'freethrow' not in shot_type:
                    results[team_key][status]['fg_attempted'] += 1
                    if shot_outcome == 'made':
                        results[team_key][status]['fg_made'] += 1
                
                # Three point tracking
                if '3pt' in shot_type or 'three' in shot_type:
                    results[team_key][status]['3pt_attempted'] += 1
                    if shot_outcome == 'made':
                        results[team_key][status]['3pt_made'] += 1
                
                # Free throw tracking
                if 'freethrow' in shot_type:
                    results[team_key][status]['ft_attempted'] += 1
                    if shot_outcome == 'made':
                        results[team_key][status]['ft_made'] += 1

                if 'layup' in shot_type or 'dunk' in shot_type:
                    results[team_key][status]['rim_fg_attempted'] += 1
                    if shot_outcome == 'made':
                        results[team_key][status]['rim_fg_made'] += 1

                if '2pt jumpshot' in shot_type:
                    results[team_key][status]['mid_range_fg_attempted'] += 1
                    if shot_outcome == 'made':
                        results[team_key][status]['mid_range_fg_made'] += 1
    
    # Calculate percentages and per-minute statistics
    for team_key in [team_str, 'Opponents']:
        for status in ['on', 'off']:
            minutes = results[team_key][status]['minutes']
            
            # Calculate shooting percentages
            if results[team_key][status]['fg_attempted'] > 0:
                results[team_key][status]['fg_pct'] = results[team_key][status]['fg_made'] / results[team_key][status]['fg_attempted']
            else:
                results[team_key][status]['fg_pct'] = 0
                
            if results[team_key][status]['3pt_attempted'] > 0:
                results[team_key][status]['3pt_pct'] = results[team_key][status]['3pt_made'] / results[team_key][status]['3pt_attempted']
            else:
                results[team_key][status]['3pt_pct'] = 0
                
            if results[team_key][status]['ft_attempted'] > 0:
                results[team_key][status]['ft_pct'] = results[team_key][status]['ft_made'] / results[team_key][status]['ft_attempted']
            else:
                results[team_key][status]['ft_pct'] = 0

            if results[team_key][status]['rim_fg_attempted'] > 0:
                results[team_key][status]['rim_fg_pct'] = results[team_key][status]['rim_fg_made'] / results[team_key][status]['rim_fg_attempted']
            else:
                results[team_key][status]['rim_fg_pct'] = 0

            if results[team_key][status]['mid_range_fg_attempted'] > 0:
                results[team_key][status]['mid_range_fg_pct'] = results[team_key][status]['mid_range_fg_made'] / results[team_key][status]['mid_range_fg_attempted']
            else:
                results[team_key][status]['mid_range_fg_pct'] = 0
            
            # Calculate per-minute stats
            if minutes > 0:
                for stat in ['points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers']:
                    results[team_key][status][f'{stat}_per_min'] = results[team_key][status][stat] / minutes
                    results[team_key][status][f'{stat}_per_40'] = results[team_key][status][stat] / minutes * 40
    
    # Create a DataFrame for team stats
    team_on_stats = pd.Series(results[team_str]['on'])
    team_off_stats = pd.Series(results[team_str]['off'])
    
    # Create a DataFrame for opponent stats
    opp_on_stats = pd.Series(results['Opponents']['on'])
    opp_off_stats = pd.Series(results['Opponents']['off'])
    
    # Calculate NET stats (team - opponent)
    net_on_stats = team_on_stats - opp_on_stats
    net_off_stats = team_off_stats - opp_off_stats
    
    # Create a DataFrame with all the data
    stats_df = pd.DataFrame({
        f'{team_str}_ON': team_on_stats,
        'Opponents_ON': opp_on_stats,
        'NET_ON': net_on_stats,
        f'{team_str}_OFF': team_off_stats,
        'Opponents_OFF': opp_off_stats,
        'NET_OFF': net_off_stats
    })
    
    # Round percentage values for better readability
    pct_columns = [col for col in stats_df.index if 'pct' in col or 'per_' in col]
    for col in pct_columns:
        stats_df.loc[col] = stats_df.loc[col].round(3)

    stats_df = stats_df.T

    stats_df['players'] = [tuple(players)] * len(stats_df)
    cols = ['players'] + [col for col in stats_df.columns if col != 'players']
    stats_df = stats_df[cols]
    
    return stats_df

def main():
    parser = argparse.ArgumentParser(description="Get On-Off Splits For Any Team Given Play-by-Play Data.")
    parser.add_argument('--pbp_data', default = '/Users/nka1139/Downloads/Rochester (NY)_pbp_data_20250425_140039.csv',
                        help = 'Play-By-Play Data, Collected From pbp_script.py')
    parser.add_argument("--team", default = 'Rochester (NY)',
                        help="Team Name")
    parser.add_argument("--players", nargs='*', default = ['Nate Sock', 'Corvin Oprea'],
                        help="players list")
    parser.add_argument('--opponent', nargs='*', default=['all'],
                    help='Opponent Information (can specify multiple, defaults to all opponents)')
    args = parser.parse_args()

    team = args.team
    opponents = args.opponent
    players_list = args.players

    print(players_list)

    pbp_data = pd.read_csv(args.pbp_data)
    
    if 'all' not in opponents:
        # Create a mask for each opponent and combine with OR (|)
        opponent_mask = False
        for opponent in opponents:
            column_name = f'lineup_{opponent}'
            opponent_mask = opponent_mask | ~pbp_data[column_name].isna()
        
        # Apply the combined mask to filter the data
        pbp_data = pbp_data.loc[opponent_mask].reset_index(drop=True)

    
    on_off_data = calculate_on_off_stats(pbp_data, players_list, team)

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    on_off_data.to_csv(team+'_onoffdata_'+current_time+'.csv')


if __name__ == "__main__":
    main()   
