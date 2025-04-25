# ncaa_hoops_pbp
Package to Extract Play-by-Play Data for NCAA Men's and Women's Basketball

## Getting Started

To install the package, clone this repo, switch into the root level of the directory. 

Then, run the following command:

`pip install -e .`

## Getting the Play-By-Play Data

Inside the `scripts` folder, the file called `pbp_script.py` contains all of the functions needed to grab the play-by-play data, and save it to a .csv file.

To call the file, switch into the `ncaa_hoops_pbp` directory and run the following prompt from the command line:

`python scripts/pbp_script.py`

By default, the script will collect all play-by-play data for Virginia basketball from the 2025 season. However, for flexibility, I have included several optional arguments that can be added on to gather all sorts of custom data for your needs.

* `--team`: String containing team name (for now, must match team name on the NCAA website. e.g. "St. John's" will not be accepted but "St. John's (NY)" will)
* `--sport`: Sport Code (can either be MBB or WBB). Defaults to MBB.
* `--opponent`: Any combination of opponents that the team played in the specified season. Defaults to all opponents.
* `--season`: Year of play (specified as a single year. e.g. the 2024-25 season would simply be entered in as 2025). Defaults to 2025
* `--division`: Division of the entered team. Defaults to division 1, must be changed if trying to collect data for non-D1 teams.

### Example Usage

Goal: collect play-by-play data for Auburn Women's Basketball against Vanderbilt and Florida from the 2022-23 season.

Command: `python scripts/pbp_script.py --team "Auburn" --sport "WBB" --opponent "Vanderbilt" "Florida" --season 2023`

Goal: collect play-by-play data for Rochester Men's Basketball against all teams from the 2024-25 season.

Command: `python scripts/pbp_script.py --team "Rochester (NY)" --division 3`

Notice that the sport, opponent, and season commands are not needed for the latter, as the defaults will work here.

## Getting On-Off Splits

The other file in the `scripts` folder, called `onoffscript.py`, can be used to extract on-off information from the play-by-play data.

To call the file, switch into the `ncaa_hoops_pbp` directory and run the following prompt from the command line:

`python scripts/onoffscript.py`

Unlike the play-by-play data file, there are some required arguments here:

* `--pbp_data`: the play-by-play data file that results from calling `pbp_script.py`
* `--team`: team name to compute on-off data for
* `--players`: list of players to compute on-off information for

In addition, there is one optional argument:

* `--opponent`: Any combination of opponents that appear in the play-by-play file. Defaults to all opponents.

In the example above, if my Auburn .csv file was called 'Auburn_pbp.csv', I would calculate the on-off splits for lineups that contain *both* Sania Wells and Kharyssa Richardson like so:

Command: `python scripts/onoffscript.py --team Rochester (NY) --players 'Sania Wells' 'Kharyssa Richardson'`

