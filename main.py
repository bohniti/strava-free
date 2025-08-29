import os
import json
import webbrowser
import http.server
import socketserver
import urllib.parse
from datetime import datetime
from collections import defaultdict
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_FILE = "strava_token.json"

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in query_params:
                self.server.auth_code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authorization successful! You can close this window.</h1></body></html>")
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authorization failed!</h1></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

def save_token(token_data):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

def load_token():
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def refresh_access_token(refresh_token):
    token_url = "https://www.strava.com/oauth/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    response = httpx.post(token_url, data=token_data)
    if response.status_code == 200:
        token_data = response.json()
        save_token(token_data)
        return token_data["access_token"]
    else:
        return None

def get_access_token():
    # Try to use saved token first
    token_data = load_token()
    if token_data:
        # Check if token is still valid by making a test request
        test_response = httpx.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        
        if test_response.status_code == 200:
            print("Using saved access token...")
            return token_data["access_token"]
        elif test_response.status_code == 401 and "refresh_token" in token_data:
            print("Access token expired, trying to refresh...")
            refreshed_token = refresh_access_token(token_data["refresh_token"])
            if refreshed_token:
                return refreshed_token
    
    # Need fresh authorization
    print("Need fresh authorization...")
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=read,activity:read_all"
    
    print(f"Opening browser for authorization: {auth_url}")
    webbrowser.open(auth_url)
    
    with socketserver.TCPServer(("", 8000), CallbackHandler) as httpd:
        httpd.auth_code = None
        print("Waiting for authorization callback...")
        while httpd.auth_code is None:
            httpd.handle_request()
        
        auth_code = httpd.auth_code
    
    token_url = "https://www.strava.com/oauth/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code"
    }
    
    response = httpx.post(token_url, data=token_data)
    if response.status_code == 200:
        token_data = response.json()
        save_token(token_data)
        return token_data["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

def fetch_activities(access_token):
    activities = []
    page = 1
    per_page = 200
    
    while True:
        url = f"https://www.strava.com/api/v3/athlete/activities"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"page": page, "per_page": per_page}
        
        response = httpx.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch activities: {response.text}")
        
        batch = response.json()
        if not batch:
            break
            
        activities.extend(batch)
        page += 1
        print(f"Fetched {len(activities)} activities so far...")
    
    return activities

def group_activities_by_week(activities):
    weekly_stats = defaultdict(lambda: defaultdict(lambda: {"count": 0, "time": 0, "distance": 0}))
    
    for activity in activities:
        start_date = datetime.fromisoformat(activity["start_date_local"].replace("Z", "+00:00"))
        year, week, _ = start_date.isocalendar()
        week_key = f"{year}-W{week:02d}"
        
        activity_type = activity["type"]
        moving_time_minutes = activity["moving_time"] / 60
        distance_km = activity["distance"] / 1000
        
        weekly_stats[week_key][activity_type]["count"] += 1
        weekly_stats[week_key][activity_type]["time"] += moving_time_minutes
        weekly_stats[week_key][activity_type]["distance"] += distance_km
    
    return weekly_stats

def display_results(weekly_stats):
    sorted_weeks = sorted(weekly_stats.keys())
    
    print("\n" + "="*80)
    print("STRAVA ACTIVITIES BY WEEK AND TYPE")
    print("="*80)
    
    for week in sorted_weeks:
        print(f"\n📅 Week {week}")
        print("-" * 40)
        
        for activity_type, stats in weekly_stats[week].items():
            time_hours = stats["time"] / 60
            print(f"  🏃 {activity_type:15} | {stats['count']:2} activities | {time_hours:5.1f}h | {stats['distance']:6.1f}km")

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Please set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in your .env file")
        return
    
    try:
        print("Getting Strava access token...")
        access_token = get_access_token()
        
        print("Fetching all activities...")
        activities = fetch_activities(access_token)
        print(f"Found {len(activities)} total activities")
        
        print("Grouping activities by week and type...")
        weekly_stats = group_activities_by_week(activities)
        
        display_results(weekly_stats)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
