import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
from collections import defaultdict
import argparse
import time
from datetime import datetime

import warnings

# Suppress FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)


headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'
    }

def create_ncaa_team_lookup_table(academic_year, sport, division):
    
    # NCAA stats page URL for the current year
    base_url = 'http://stats.ncaa.org/team/inst_team_list?academic_year='+str(academic_year)+'&conf_id=-1&division='+str(division)+'&sport_code='+str(sport)
    
    try:
        # Fetch the page
        print(f"Fetching data from NCAA website...")
        page = requests.get(base_url, headers=headers)
        page.raise_for_status()  # Check for request errors
        
        # Parse the content
        soup = BeautifulSoup(page.content, 'lxml')
        
        # Find all team links
        team_links = soup.find_all('a', href=re.compile(r'/teams/\d+'))
        
        # Create lookup dictionary
        team_lookup = {}
        
        # Extract team names and IDs
        for link in team_links:
            team_name = link.text.strip()
            href = link['href']
            team_id = href.split('/')[-1]
            team_lookup[team_name] = {
                'team_id': team_id,
                'href': href
            }
        
        print(f"Found {len(team_lookup)} teams in division {division}.")
        return team_lookup
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}
    
def create_contest_lookup_table(soup_content=None):
    """
    Create a lookup table from NCAA contest data
    Can work with either provided soup content or by making a new request
    """
    if soup_content is None:
        print("Error: No soup content or URL provided")
        return {}
    
    # Find all table rows that might contain game data
    rows = soup_content.find_all('tr')
    
    # Create contest lookup dictionary - use defaultdict to handle multiple contests per team
    contest_lookup = defaultdict(list)
    
    # Process each row
    for row in rows:
        # Look for cells that might contain our data
        cells = row.find_all('td')
        if len(cells) >= 3:  # Need at least date, team, and result cells
            # Check for team link
            team_cell = cells[1] if len(cells) > 1 else None
            team_link = team_cell.find('a') if team_cell else None
            
            # Check for contest link
            contest_cell = cells[2] if len(cells) > 2 else None
            contest_link = contest_cell.find('a') if contest_cell else None
            
            if team_link and contest_link:
                # Get date from first cell if available
                date = cells[0].text.strip() if cells[0] else "Unknown Date"
                
                # Extract team name - handle cases with or without image
                if team_link.img:
                    team_name = team_link.get_text().strip()
                else:
                    team_name = team_link.text.strip()
                
                # Remove @ symbol if present
                team_name = re.sub(r'^@\s*', '', team_name)
                
                # Remove rankings (like "#1", "#25", etc.) from team name
                team_name = re.sub(r'^#\d+\s+', '', team_name)
                
                # Get team href
                team_href = team_link.get('href', '')
                
                # Get contest href and result
                contest_href = contest_link.get('href', '')
                contest_href = contest_href.replace('box_score', 'play_by_play')
                contest_result = contest_link.text.strip()
                
                # Add to lookup dictionary
                contest_lookup[team_name].append({
                    'date': date,
                    'team_href': team_href,
                    'contest_href': contest_href,
                    'result': contest_result
                })
    
    print(f"Found matchup data for {len(contest_lookup)} opponents.")
    return dict(contest_lookup)

def parse_play_by_play_data(soup_content):
    """
    Parse NCAA play-by-play data and organize into a structured table
    Including the period of play (1st Half, 2nd Half, OT, etc.)
    
    Parameters:
    soup_content - BeautifulSoup object containing the play-by-play tables
    
    Returns:
    DataFrame with columns: period, time_remaining, player_name, team, event_type
    """
    # Find all period sections
    period_sections = soup_content.find_all('div', class_='card-header')
    team1_name = ''
    team2_name = ''
    
    all_play_data = []

    responsive_tables = soup_content.find_all('div', class_='table-responsive')

    top_table = responsive_tables[0].find('table')

    tds = top_table.find_all('td', class_='grey_text')

    date_td = None
    for td in tds:
        # Check if it has any colspan and contains a date pattern
        if td.has_attr('colspan') and re.search(r'\d{2}/\d{2}/\d{4}', td.text):
            date_td = td
            break

    date_text = date_td.text.strip()

    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text)

    if date_match:
        date_only = ''.join(date_match.groups())
    
    # For each period section, find the associated table and parse it
    for period_section in period_sections:
        # Get the period name
        period_name = period_section.text.strip()
        print(f"Processing period: {period_name}")
        
        # Find the associated card-body (table container)
        card_body = period_section.find_next_sibling('div', class_='card-body')
        if not card_body:
            print(f"Warning: Could not find table for period {period_name}")
            continue
        
        # Get the table within this card-body
        table = card_body.find('table')
        if not table:
            print(f"Warning: No table found in period {period_name}")
            continue
        
        # Extract team names from the header row
        headers = table.find_all('th')
        team1_name = None
        team2_name = None
        
        for header in headers:
            span = header.find('span', class_='d-none d-sm-block')
            if span:
                if team1_name is None:
                    team1_name = span.text.strip()
                else:
                    team2_name = span.text.strip()
        
        if not team1_name or not team2_name:
            print(f"Warning: Could not identify both team names in period {period_name}")
            team1_name = team1_name or "Team 1"
            team2_name = team2_name or "Team 2"
        
        # Find all data rows in this table
        rows = table.find_all('tr')
        
        # Skip header row(s)
        data_rows = []
        for row in rows:
            if row.find('th'):
                continue
            data_rows.append(row)
        
        # Process each play in this period
        for row in data_rows:
            cells = row.find_all('td')
            
            # Skip rows with insufficient data
            if len(cells) < 3:
                continue
            
            # Extract time remaining
            time_remaining = cells[0].text.strip()
            
            # Check if it's a special event that spans multiple columns
            colspan_cell = None
            for cell in cells:
                if cell.get('colspan'):
                    colspan_cell = cell
                    break
            
            if colspan_cell:
                # Handle special events (jumpball startperiod, period start, etc.)
                event_text = colspan_cell.text.strip()
                if event_text:
                    # Try to extract event type
                    event_match = re.search(r'(\w+)$', event_text)
                    event_type = event_match.group(1) if event_match else event_text
                    
                    all_play_data.append({
                        'period': period_name,
                        'time_remaining': time_remaining,
                        'player_name': "",
                        'team': "GAME EVENT",
                        'event_type': event_type
                    })
                continue
            
            # Regular play - determine which team and extract player, event
            team1_cell = cells[1].text.strip() if len(cells) > 1 else ""
            score_cell = cells[2].text.strip() if len(cells) > 2 else ""
            team2_cell = cells[3].text.strip() if len(cells) > 3 else ""
            
            # Process team 1 event
            if team1_cell:
                player_name = ""
                event_type = team1_cell
                
                # Extract player name if it exists
                player_match = re.search(r'<b>(.*?),</b>', str(cells[1]))
                if player_match:
                    player_name = player_match.group(1).strip()
                    
                    # Extract event type - everything after the player name and comma
                    event_text = re.sub(r'<b>.*?</b>', '', str(cells[1]))
                    event_text = BeautifulSoup(event_text, 'lxml').text.strip()
                    event_text = re.sub(r'^,\s*', '', event_text)
                    event_type = event_text.strip()
                
                all_play_data.append({
                    'period': period_name,
                    'time_remaining': time_remaining,
                    'player_name': player_name,
                    'team': team1_name,
                    'event_type': event_type
                })
            
            # Process team 2 event
            if team2_cell:
                player_name = ""
                event_type = team2_cell
                
                # Extract player name if it exists
                player_match = re.search(r'<b>(.*?),</b>', str(cells[3]))
                if player_match:
                    player_name = player_match.group(1).strip()
                    
                    # Extract event type - everything after the player name and comma
                    event_text = re.sub(r'<b>.*?</b>', '', str(cells[3]))
                    event_text = BeautifulSoup(event_text, 'lxml').text.strip()
                    event_text = re.sub(r'^,\s*', '', event_text)
                    event_type = event_text.strip()
                
                all_play_data.append({
                    'period': period_name,
                    'time_remaining': time_remaining,
                    'player_name': player_name,
                    'team': team2_name,
                    'event_type': event_type
                })
    
    # Create DataFrame and return
    df = pd.DataFrame(all_play_data)
    
    # Add sorting if needed - first by period in appearance order, then by time in descending order
    # This requires mapping period names to numeric order
    period_order = {'1st Half': 1, '2nd Half': 2, 'OT': 3, '2nd OT': 4, '3rd OT': 5, '4th OT': 6, '5th OT': 7, '6th OT': 8, '7th OT': 9, '8th OT': 10, '9th OT': 11, '10th OT': 12}
    
    # Create a period_order column for sorting if we have standard period names
    if df.empty:
        return df
        
    if all(p in period_order for p in df['period'].unique()):
        df['period_order'] = df['period'].map(period_order)
        df = df.sort_values(['period_order', 'time_remaining'], ascending=[True, False])
        df = df.drop('period_order', axis=1)

    def clean_name(name):
        return re.sub(r"[ .']", '', name)

    df['game_id'] = clean_name(team1_name) + clean_name(team2_name) + date_only
    
    return df

def add_shot_information(df):
    """
    Analyze event types to identify shots and their outcomes
    Parameters:
    df - DataFrame with play-by-play data including 'event_type' column
    Returns:
    DataFrame with two new columns: 'is_shot' and 'shot_outcome'
    """
    import pandas as pd
    import numpy as np
    import re
    
    # Create a copy to avoid modifying the original
    result_df = df.copy()
    
    # Initialize columns
    result_df['is_shot'] = False
    result_df['shot_outcome'] = np.nan
    
    # Define shot patterns
    shot_patterns = ['2pt', '3pt', 'jumpshot', 'layup', 'dunk', 'freethrow']
    
    # Process each row
    for i, row in result_df.iterrows():
        event = row['event_type']
        
        # Check if this is a shot event
        is_shot = any(pattern in event.lower() for pattern in shot_patterns)
        result_df.at[i, 'is_shot'] = is_shot
        
        if is_shot:
            # Check if shot was made or missed
            if 'made' in event.lower():
                result_df.at[i, 'shot_outcome'] = 'made'
                # Remove 'made' from event_type
                result_df.at[i, 'event_type'] = re.sub(r'\s+made', '', event, flags=re.IGNORECASE)
            elif 'missed' in event.lower():
                result_df.at[i, 'shot_outcome'] = 'missed'
                # Remove 'missed' from event_type
                result_df.at[i, 'event_type'] = re.sub(r'\s+missed', '', event, flags=re.IGNORECASE)

            
    
    result_df['event_type'] = result_df['event_type'].str.replace(';', '', regex=False)

    import numpy as np

    # Step 1: Define shot_type based on patterns in event_type
    result_df['shot_type'] = np.select(
        [
            result_df['event_type'].str.contains('freethrow', case=False),
            result_df['event_type'].str.contains('3pt jumpshot', case=False) | result_df['event_type'].str.contains('Three Point', case=False) | result_df['event_type'].str.contains('3pt', case=False) ,
            result_df['event_type'].str.contains(r'(2pt|two point).*?(jumper|jumpshot)', case=False, regex=True),
            result_df['event_type'].str.contains('dunk', case=False),
            result_df['event_type'].str.contains('layup', case=False)
        ],
        [
            'freethrow',
            '3pt jumpshot',
            '2pt jumpshot',
            'dunk',
            'layup'
        ],
        default='None'
    )

    # Step 2: Define shot_range based on shot_type and presence of 'pointsinthepaint'
    result_df['shot_range'] = np.select(
        [
            result_df['shot_type'] == 'freethrow',
            result_df['shot_type'] == '3pt jumpshot',
            result_df['event_type'].str.contains('pointsinthepaint', case=False),
            result_df['shot_type'] == '2pt jumpshot'  # not in paint
        ],
        [
            'freethrow',
            '3pt',
            'paint',
            'mid-range'
        ],
        default='None'
    )

    result_df['points'] = np.select(
        [
            result_df['shot_type'] == 'freethrow',
            result_df['shot_type'] == '3pt jumpshot',
            result_df['event_type'].str.contains('2pt', case=False)        
            ],
        [
            1,
            3,
            2
        ],
        default=0
    )

    result_df.loc[result_df['shot_outcome'] == 'missed', 'points'] = 0

    return result_df

def track_lineups(pbp_data):
    """
    Track lineups throughout the game using play-by-play data.
    
    Parameters:
    pbp_data - DataFrame containing play-by-play data with columns:
               event_type, team, player_name, period, time_remaining
               
    Returns:
    DataFrame with additional columns for lineups and lineup length
    """
    # Create a copy of the input data to avoid modifying the original
    pbp_data = pbp_data.copy()
    
    # Filter substitution events
    subs = pbp_data[pbp_data['event_type'].str.contains('substitution', case=False)].copy()


    # Sort substitution events in game order
    subs_sorted = subs.sort_values(by=['period', 'time_remaining'], ascending=[True, False])
    
    # Track players who have subbed in
    players_subbed_in = defaultdict(set)
    
    # Starting lineups dict
    starting_lineups = defaultdict(list)
    
    # Go through each sub event to determine starting lineups
    for _, row in subs_sorted.iterrows():
        team = row['team']
        player = row['player_name']
        event = row['event_type'].lower()


        if ('substitution out' in event) or ("Leaves Game" in event):
            if player not in players_subbed_in[team] and len(starting_lineups[team]) < 5:
                starting_lineups[team].append(player.title())
        elif ('substitution in' in event) or ("Enters Game" in event):
            players_subbed_in[team].add(player.title())
        
        # Once both teams have 5 starters, we can stop
        if starting_lineups and all(len(v) == 5 for v in starting_lineups.values()):
            break
    
    # Print starting lineups (comment out if not needed)
    for team, lineup in starting_lineups.items():
        print(f"{team} starters: {lineup}")
    
    # Convert lists to sets for efficient membership tests
    lineups = {team: set(players) for team, players in starting_lineups.items()}
    team_list = list(starting_lineups.keys())

    if len(team_list) <= 1:
        print('Incorrect/Nonexistent PBP Data, Skipping...')
        return pbp_data
    else:
    # Prepare columns to store lineups
        pbp_data['lineup_' + team_list[0]] = None
        pbp_data['lineup_' + team_list[1]] = None
        
        # Iterate through events in order
        pbp_data = pbp_data.sort_values(by=['period', 'time_remaining'], ascending=[True, False]).reset_index(drop=True)
        
        for i, row in pbp_data.iterrows():
            event = row['event_type'].lower() if pd.notna(row['event_type']) else ""
            team = row['team']
            player = row['player_name']
            
            # Update lineup if it's a substitution
            if pd.notna(team) and pd.notna(player):
                if 'substitution out' in event:
                    lineups[team].discard(player.title())
                elif 'substitution in' in event:
                    lineups[team].add(player.title())
            
            # Record current lineup for both teams as sorted tuples
            for t in team_list:
                pbp_data.at[i, f'lineup_{t}'] = tuple(sorted(lineups[t]))
        
        # Add lineup lengths
        pbp_data['lineup_len_' + team_list[0]] = pbp_data['lineup_' + team_list[0]].apply(
            lambda x: len(x) if isinstance(x, tuple) else np.nan)
        pbp_data['lineup_len_' + team_list[1]] = pbp_data['lineup_' + team_list[1]].apply(
            lambda x: len(x) if isinstance(x, tuple) else np.nan)
    
    return pbp_data

def main():
    parser = argparse.ArgumentParser(description="Get Play-by-Play Data For Any Team, for Any Season.")
    parser.add_argument("--team", default="Virginia",
                        help="Team Name")
    parser.add_argument('--sport', default="MBB",
                        help='Sport code (MBB or WBB)')
    parser.add_argument('--opponent', nargs='*', default=['all'],
                    help='Opponent Information (can specify multiple, defaults to all opponents)')
    parser.add_argument("--season", default=2025, type=int,
                        help="Season to Search")
    parser.add_argument("--division", default=1, type=int,
                        help="NCAA Division (1, 2, or 3)")
    args = parser.parse_args()

    team_lookup = create_ncaa_team_lookup_table(args.season, args.sport, args.division)

    print("Looking for team: " + args.team)

    if args.team in team_lookup:
        team_href = team_lookup[args.team]["href"]
    else:
        print(args.team + " not found in the lookup table.")
    
    base_url = 'http://stats.ncaa.org/' + team_href

    # Fetch the page
    print(f"Fetching matchup data from NCAA website...")
    page = requests.get(base_url, headers=headers)
    page.raise_for_status()  # Check for request errors

    # Parse the content
    soup = BeautifulSoup(page.content, 'lxml')

    matchup_table = create_contest_lookup_table(soup)

    if 'all' in args.opponent:
        opponents_list = list(matchup_table.keys())
    else:
        opponents_list = args.opponent

    pbp_data_list = []
    for opponent in opponents_list:
        if opponent in matchup_table:
            matchups = matchup_table[opponent]

            for i, matchup in enumerate(matchups, 1):
                contest_href = matchup['contest_href']
                date = matchup['date']

                matchup_url = 'http://stats.ncaa.org/' + contest_href

                # Fetch the page
                page = requests.get(matchup_url, headers=headers)
                page.raise_for_status()  # Check for request errors

                # Parse the content
                soup = BeautifulSoup(page.content, 'lxml')

                pbp_data_matchup = parse_play_by_play_data(soup)

                pbp_data_matchup = add_shot_information(pbp_data_matchup)

                pbp_data_matchup = track_lineups(pbp_data_matchup)

                pbp_data_list.append(pbp_data_matchup)

                print("Play-by-Play Data Collected For: " + opponent + ' on date ' + str(date))

                time.sleep(2)
        else:
            print(f"No matchups found with {opponent}")
    
    pbp_data = pd.concat(pbp_data_list)

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    pbp_data.to_csv('./'+args.team+'_pbp_data_'+current_time+'.csv')

    return pbp_data

if __name__ == "__main__":
    main()            

