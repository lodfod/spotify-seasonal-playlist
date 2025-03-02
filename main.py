import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
import time
import http.server
import socketserver
import threading
import dotenv

dotenv.load_dotenv()

# Set your Spotify API credentials as environment variables before running:
# export SPOTIPY_CLIENT_ID='your-spotify-client-id'
# export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
# export SPOTIPY_REDIRECT_URI='your-app-redirect-url'

# Configuration
MAIN_PLAYLIST_ID = os.getenv("SPOTIPY_MAIN_PLAYLIST_ID")  # Replace with your actual playlist ID
USER_ID = os.getenv("SPOTIPY_USER_ID")  # Your Spotify user ID
SCOPE = "playlist-read-collaborative playlist-modify-public playlist-modify-private user-library-read"

# Season definitions with approximate dates (month, day)
SEASONS = {
    "spring": (3, 20),  # Spring equinox (around March 20)
    "summer": (6, 21),  # Summer solstice (around June 21)
    "fall": (9, 22),    # Fall equinox (around September 22)
    "winter": (12, 21)  # Winter solstice (around December 21)
}

# The port your redirect URI is using
PORT = 8888

# HTML to display after successful authentication
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Authentication Successful</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            text-align: center;
            line-height: 1.5;
        }
        .container {
            background-color: #f5f5f5;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1DB954; /* Spotify green */
        }
        .icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">✅</div>
        <h1>Authentication Successful!</h1>
        <p>You've successfully authenticated with Spotify.</p>
        <p>You can now close this window and return to the application.</p>
    </div>
</body>
</html>
"""

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests to the server."""
        # Send a success response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Write the success HTML to the response
        self.wfile.write(SUCCESS_HTML.encode('utf-8'))
        
        # If this is the callback URL with a code, signal the server to shut down
        if self.path.startswith('/callback') and 'code=' in self.path:
            # Use a thread to shut down the server after sending the response
            threading.Thread(target=self.server.shutdown).start()

def start_callback_server():
    """Start the HTTP server to handle the callback."""
    handler = CallbackHandler
    
    # Create the server
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Callback server started at http://localhost:{PORT}")
        # Store the server instance so the handler can shut it down
        handler.server = httpd
        # Serve until shutdown is called from the handler
        httpd.serve_forever()

def get_spotify_client():
    """Initialize and return a Spotify client with proper authentication."""
    auth_manager = SpotifyOAuth(
        scope=SCOPE,
        redirect_uri="http://localhost:8888/callback",
        open_browser=True
    )
    
    # Get the cached token or go through auth flow
    token_info = auth_manager.get_cached_token()
    if not token_info:
        print("No cached token found. Please authenticate in your browser...")
        auth_url = auth_manager.get_authorize_url()
        print(f"Please visit this URL to authenticate: {auth_url}")
        
        # Wait for user to authenticate and manually enter the redirect URL
        redirect_url = input("Enter the URL you were redirected to: ")
        code = auth_manager.parse_response_code(redirect_url)
        token_info = auth_manager.get_access_token(code)
    
    return spotipy.Spotify(auth_manager=auth_manager)

def get_current_season():
    """Determine the current season based on today's date."""
    now = datetime.now()
    current_year = now.year
    
    # Convert season dates to actual dates for the current year
    season_dates = {
        season: datetime(current_year, month, day)
        for season, (month, day) in SEASONS.items()
    }
    
    # Handle year boundary for Winter
    if now < season_dates["spring"]:
        return "winter"
    elif now < season_dates["summer"]:
        return "spring"
    elif now < season_dates["fall"]:
        return "summer"
    elif now < season_dates["winter"]:
        return "fall"
    else:
        return "winter"

def get_current_season_year():
    """Get the year associated with the current season."""
    current_season = get_current_season()
    current_year = datetime.now().year
    
    if current_season == "winter" and datetime.now().month < 3:
        return current_year
    
    if current_season == "winter" and datetime.now().month == 12:
        return current_year + 1
        
    return current_year

def get_next_season():
    """Determine the upcoming season."""
    current = get_current_season()
    seasons_list = list(SEASONS.keys())
    current_index = seasons_list.index(current)
    next_index = (current_index + 1) % len(seasons_list)
    return seasons_list[next_index]

def get_next_season_date():
    """Get the date of the next season change."""
    next_season = get_next_season()
    current_year = datetime.now().year
    month, day = SEASONS[next_season]
    
    # Handle year boundaries for different seasons
    if next_season == "spring" and datetime.now().month > month:
        # If we're past March and looking for spring, it's next year's spring
        year = current_year + 1
    elif next_season == "winter":
        # For winter, if we're in fall (Sep-Nov), winter starts in current year (Dec)
        # but is labeled as next year's winter
        if datetime.now().month >= 9 and datetime.now().month <= 11:
            # Winter 2025 starts in Dec 2024
            year = current_year + 1
        else:
            # If we're in winter/spring/summer looking for next winter,
            # it starts in Dec of current year but is labeled as next year's winter
            year = current_year + 1
    else:
        # For summer and fall, or if we're in winter/spring looking for summer/fall,
        # they occur in the current year
        year = current_year
        
    return datetime(year, month, day)

def find_or_create_seasonal_playlist(sp, season, year):
    """Find an existing seasonal playlist or create a new one."""
    playlist_name = f"archie + kotoha {season} {year}"
    
    # Check if playlist already exists
    playlists = sp.current_user_playlists()
    for playlist in playlists["items"]:
        if playlist["name"] == playlist_name and playlist["owner"]["id"] == USER_ID:
            print(f"Found existing playlist: {playlist_name}")
            return playlist["id"]
    
    # Create new playlist if it doesn't exist
    print(f"Creating new playlist: {playlist_name}")
    description = f"songs from our playlist during {season} {year}"
    new_playlist = sp.user_playlist_create(
        user=USER_ID,
        name=playlist_name,
        public=False,
        description=description
    )
    
    # Share the playlist with another user
    playlist_id = new_playlist["id"]
    share_playlist_with_user(sp, playlist_id, os.getenv("SPOTIPY_GIRLFRIEND_USER_ID"))  # Replace with actual Spotify user ID
    
    return playlist_id

# TODO: this is a temporary function to share the playlist - does not currently work as intended
def share_playlist_with_user(sp, playlist_id, user_id):
    """Share a playlist with another user by adding them as a collaborator."""
    try:
        if ":" in playlist_id:
            playlist_id = playlist_id.split(":")[-1]
            
        # Add the user as a collaborator
        sp._put(f"playlists/{playlist_id}/followers", payload={"public": False})
        
        print(f"Shared playlist with user: {user_id}")
        return True
    except Exception as e:
        print(f"Error sharing playlist: {e}")
        return False

def get_tracks_added_since(sp, playlist_id, since_date=None):
    """Get tracks from a playlist that were added after a certain date."""
    tracks = []
    offset = 0
    limit = 100 
    
    # Loop until we've retrieved all tracks
    while True:
        results = sp.playlist_items(
            playlist_id,
            fields="items(added_at,track(id,name,artists)),total,next",
            additional_types=["track"],
            offset=offset,
            limit=limit
        )
        
        print(f"Retrieved batch of {len(results['items'])} tracks (offset: {offset})")
        
        for item in results["items"]:
            # Skip None tracks (can happen with local files)
            if not item["track"]:
                continue
                
            added_at = datetime.strptime(item["added_at"], "%Y-%m-%dT%H:%M:%SZ")
            
            # If since_date is None, get all tracks
            # Otherwise, only get tracks added since the specified date
            if since_date is None or added_at >= since_date:
                track_id = item["track"]["id"]
                if track_id:  # Skip local tracks which have no Spotify ID
                    tracks.append({
                        "id": track_id,
                        "name": item["track"]["name"],
                        "added_at": added_at,
                        "uri": f"spotify:track:{track_id}"
                    })
        
        # If there are no more tracks to retrieve, break the loop
        if results["next"] is None:
            break
            
        # Otherwise, update the offset and continue
        offset += limit
    
    # Sort tracks by added date (most recent first)
    tracks.sort(key=lambda x: x["added_at"], reverse=True)
    
    # Print the 5 most recently added tracks for debugging
    if tracks:
        print("Most recently added tracks:")
        for i, track in enumerate(tracks[:5]):
            print(f"  {i+1}. {track['name']} (added {track['added_at']})")
    
    return tracks

def update_seasonal_playlist(sp):
    """Update the current seasonal playlist with new tracks from the main playlist."""
    current_season = get_current_season()
    current_season_year = get_current_season_year()
    
    print(f"Current season: {current_season} {current_season_year}")
    
    # Find or create the seasonal playlist
    seasonal_playlist_id = find_or_create_seasonal_playlist(sp, current_season, current_season_year)
    
    # Get tracks already in the seasonal playlist
    existing_tracks = sp.playlist_items(
        seasonal_playlist_id, 
        fields="items(track(id))",
        additional_types=["track"],
        limit=100
    )
    
    # Get all existing tracks with pagination
    existing_track_ids = []
    results = existing_tracks
    
    while True:
        # Add track IDs from current batch
        for item in results["items"]:
            if item["track"] and item["track"]["id"]:
                existing_track_ids.append(item["track"]["id"])
        
        # Check if there are more tracks to retrieve
        if results.get("next"):
            results = sp.next(results)
        else:
            break
    
    print(f"Found {len(existing_track_ids)} existing tracks in the seasonal playlist")
    
    # Calculate the current season's start date
    month, day = SEASONS[current_season]
    
    # For winter, we need to handle the year differently
    if current_season == "winter":
        # Winter 2024 starts in December 2023
        season_start = datetime(current_season_year - 1, month, day)
    else:
        season_start = datetime(current_season_year, month, day)
    
    # Calculate the next season's start date (which is the end date for current season)
    seasons_list = list(SEASONS.keys())
    current_index = seasons_list.index(current_season)
    next_index = (current_index + 1) % len(seasons_list)
    next_season = seasons_list[next_index]
    next_month, next_day = SEASONS[next_season]
    
    # Next season is always in the current_season_year, except when winter transitions to spring
    if current_season == "winter" and next_season == "spring":
        season_end = datetime(current_season_year, next_month, next_day)
    else:
        season_end = datetime(current_season_year, next_month, next_day)
    
    print(f"Season date range: {season_start} to {season_end}")
    
    # Get tracks from the main playlist
    main_tracks = get_tracks_added_since(sp, MAIN_PLAYLIST_ID)
    print(f"Retrieved {len(main_tracks)} tracks from main playlist")
    
    # Filter tracks to only include those added during the current season
    current_season_tracks = []
    for track in main_tracks:
        added_at = track["added_at"]
        if season_start <= added_at < season_end:
            current_season_tracks.append(track)
    
    print(f"Found {len(current_season_tracks)} tracks for current season")
    
    # Debug: Print all existing track IDs
    print("First few existing track IDs in seasonal playlist:")
    for i, track_id in enumerate(existing_track_ids[:5]):
        print(f"  {i+1}. {track_id}")
    
    # Filter out tracks that are already in the seasonal playlist
    new_tracks = []
    for track in current_season_tracks:
        if track["id"] not in existing_track_ids:
            new_tracks.append(track)
            print(f"New track detected: {track['name']} (ID: {track['id']})")
    
    if new_tracks:
        print(f"New tracks to add: {len(new_tracks)}")
        for track in new_tracks:
            print(f"  - {track['name']} (added {track['added_at']})")
        
        # Add new tracks to the seasonal playlist
        track_uris = [track["uri"] for track in new_tracks]
        
        # Spotify has a limit of 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            sp.playlist_add_items(seasonal_playlist_id, batch)
            
        print(f"Added {len(new_tracks)} new tracks to {current_season} {current_season_year} playlist")
    else:
        print("No new tracks to add")
        
        # Debug: Print the first few tracks from the main playlist that fall within the season
        if current_season_tracks:
            print("Tracks from main playlist that fall within the current season:")
            for i, track in enumerate(current_season_tracks[:5]):
                print(f"  {i+1}. {track['name']} (added {track['added_at']})")
                print(f"     Track ID: {track['id']}")
                
            # Debug: Check if these tracks are actually in the existing_track_ids
            for i, track in enumerate(current_season_tracks[:5]):
                is_in_playlist = track["id"] in existing_track_ids
                print(f"  {i+1}. {track['name']} - In playlist: {is_in_playlist}")

def check_for_season_change(sp):
    """Check if it's time to create the next season's playlist."""
    next_season = get_next_season()
    next_season_date = get_next_season_date()
    today = datetime.now()
    
    # If we're within 1 day of the season change, create the next season's playlist
    if abs((next_season_date - today).days) <= 1:
        # Calculate the correct year for the next season
        year = next_season_date.year
        
        # If it's winter starting in December, the year should be the current year
        if next_season == "winter" and next_season_date.month == 12:
            year = today.year
            
        find_or_create_seasonal_playlist(sp, next_season, year)
        print(f"Created playlist for upcoming season: {next_season} {year}")

def create_retroactive_seasonal_playlists(sp, start_year=None):
    """
    Create seasonal playlists retroactively based on when songs were added to the main playlist.
    
    Args:
        sp: Spotify client
        start_year: The year to start creating playlists from (defaults to current year - 1)
    """
    if start_year is None:
        start_year = datetime.now().year - 1
    
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    
    # Get all tracks from the main playlist with their added dates
    all_tracks = get_tracks_added_since(sp, MAIN_PLAYLIST_ID)
    
    print(f"Retrieved {len(all_tracks)} tracks from main playlist")
    
    # Sort tracks by added date
    all_tracks.sort(key=lambda x: x["added_at"])
    
    if not all_tracks:
        print("No tracks found in the main playlist")
        return
    
    # Get the earliest and latest dates
    earliest_date = all_tracks[0]["added_at"]
    latest_date = all_tracks[-1]["added_at"]
    
    print(f"Earliest track date: {earliest_date}")
    print(f"Latest track date: {latest_date}")
    
    # Ensure we don't go earlier than the start_year
    earliest_year = max(earliest_date.year, start_year)
    
    # Reorder seasons to start with winter
    ordered_seasons = ["winter", "spring", "summer", "fall"]
    
    # Create a list of season boundaries
    season_boundaries = []
    
    # Generate all season boundaries from earliest year to current year
    for year in range(earliest_year - 1, current_year + 2):  # Add buffer years
        for season in ordered_seasons:
            month, day = SEASONS[season]
            
            # For winter, associate it with the following year
            # (e.g., Winter 2023 starts in Dec 2022 and ends in Mar 2023)
            if season == "winter":
                # Winter that starts in December of the previous year
                season_year = year + 1
                season_boundaries.append({
                    'name': season,
                    'year': season_year,
                    'date': datetime(year, month, day)  # December of previous year
                })
            else:
                season_boundaries.append({
                    'name': season,
                    'year': year,
                    'date': datetime(year, month, day)
                })
    
    # Sort boundaries by date
    season_boundaries.sort(key=lambda x: x['date'])
    
    # Filter out boundaries that are too early or too late
    season_boundaries = [b for b in season_boundaries 
                         if b['date'] >= datetime(earliest_year - 1, 1, 1) and 
                            b['date'] <= datetime(current_year + 1, 12, 31)]
    
    # Create a dictionary to hold tracks for each season period
    seasonal_tracks = {}
    
    # Process each season period
    for i in range(len(season_boundaries) - 1):
        current_boundary = season_boundaries[i]
        next_boundary = season_boundaries[i + 1]
        
        season_start = current_boundary['date']
        season_end = next_boundary['date']
        season = current_boundary['name']
        year = current_boundary['year']
        
        # Skip if this period is entirely in the future
        if season_start > datetime.now():
            continue
        
        # Skip if this period is entirely before our earliest track
        if season_end < earliest_date:
            continue
        
        # Create a key for this season period
        season_key = f"{season}_{year}"
        
        print(f"Processing {season_key}: {season_start} to {season_end}")
        
        # Find tracks added during this season
        seasonal_tracks[season_key] = []
        
        for track in all_tracks:
            added_at = track["added_at"]
            # Include tracks added during this season period
            # Note: We use >= for start and < for end to avoid double-counting
            if season_start <= added_at < season_end:
                seasonal_tracks[season_key].append(track)
        
        print(f"Found {len(seasonal_tracks[season_key])} tracks for {season} {year}")
    
    # Create playlists for each season that has tracks
    for season_key, tracks in seasonal_tracks.items():
        if not tracks:
            continue
            
        season, year = season_key.split("_")
        year = int(year)
        
        # Create the seasonal playlist
        playlist_id = find_or_create_seasonal_playlist(sp, season, year)
        
        # Get existing tracks in the playlist
        existing_tracks = sp.playlist_items(
            playlist_id, 
            fields="items(track(id))"
        )
        existing_track_ids = [item["track"]["id"] for item in existing_tracks["items"] if item["track"]]
        
        # Filter out tracks that are already in the playlist
        new_tracks = [track for track in tracks if track["id"] not in existing_track_ids]
        
        if new_tracks:
            # Add tracks to the playlist
            track_uris = [track["uri"] for track in new_tracks]
            
            # Spotify has a limit of 100 tracks per request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                sp.playlist_add_items(playlist_id, batch)
            
            print(f"Added {len(new_tracks)} tracks to {season} {year} playlist")
        else:
            print(f"No new tracks to add to {season} {year} playlist")

def main():
    """Main function to run the bot."""
    sp = get_spotify_client()
    
    # Check for command line arguments
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--retroactive":
        # If a start year is provided, use it
        start_year = int(sys.argv[2]) if len(sys.argv) > 2 else None
        create_retroactive_seasonal_playlists(sp, start_year)
        print("Retroactive playlist creation completed")
        return
    
    # Update the current seasonal playlist
    update_seasonal_playlist(sp)
    
    # Check if we need to create the next season's playlist
    check_for_season_change(sp)
    
    print(f"Bot run completed at {datetime.now()}")

if __name__ == "__main__":
    main()
