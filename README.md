# Spotify Seasonal Playlist Generator
This script automatically creates and maintains seasonal playlists based on songs added to a main collaborative playlist. It organizes tracks by the season they were added, making it easy to revisit music from specific time periods.

## Features

* Automatic Seasonal Playlists: Creates playlists for Winter, Spring, Summer, and Fall
* Real-time Updates: Adds new tracks from your main playlist to the appropriate seasonal playlist
* Retroactive Creation: Can generate seasonal playlists for past years based on when songs were added
* Private Playlists: All created playlists are private by default
* Season Transitions: Automatically creates the next season's playlist when a new season begins

## Requirements

* Python 3.6+
* Spotify Premium account
* Spotify Developer API credentials

## Installation

1. Clone this repository or download the script
2. Install required packages:

```bash
   pip install spotipy python-dotenv
```

3. Create a `.env` file in the same directory with your Spotify credentials:
   
```bash
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
SPOTIPY_MAIN_PLAYLIST_ID=your_main_playlist_id
SPOTIPY_USER_ID=your_spotify_user_id
SPOTIPY_GIRLFRIEND_USER_ID=other_user_spotify_id
```

## Setup
1. Create a Spotify Developer application at `developer.spotify.com`
2. Set the redirect URI to `http://localhost:8888/callback` in your Spotify app settings
3. Copy your Client ID and Client Secret to the .env file
4. Find your main playlist ID (the part after playlist/ in the Spotify URL) and add it to the .env file
5. Add your Spotify user ID to the .env file

## Usage

### Regular Updates: Run the script to update the current seasonal playlist with new tracks:
  
```bash
python main.py
```

This will:

1. Identify the current season
2. Create a seasonal playlist if it doesn't exist
3. Add any new tracks from your main playlist to the seasonal playlist

### Retroactive Creation: To create seasonal playlists for past years:

```bash
python main.py --retroactive [start_year]
```

For example, to create playlists from 2020 onwards:

```bash
python main.py --retroactive 2020
```

## How It Works

* Seasons: The script defines seasons based on their astronomical start dates:
  * Winter: December 21 - March 19
  * Spring: March 20 - June 20
  * Summer: June 21 - September 21
  * Fall: September 22 - December 20
* Naming Convention: Playlists are named in the format "archie + kotoha [season] [year]"
* Winter is associated with the year it ends in (e.g., "Winter 2024" spans Dec 2023 to Mar 2024)
* Track Assignment: Tracks are assigned to seasons based on when they were added to the main playlist

## Troubleshooting

* Authentication Issues: If you encounter authentication problems, try deleting the .cache file and running the script again
* Missing Tracks: Ensure your main playlist is collaborative or owned by you
* API Rate Limits: If you hit rate limits, try running the script less frequently

## Customization

* You can customize the script by modifying:
  * The playlist naming format in the `find_or_create_seasonal_playlist` function
  * The season definitions in the `SEASONS` dictionary
  * The playlist description in the `find_or_create_seasonal_playlist` function
