# Strava Free

Simple Python script to fetch your Strava activities grouped by week and activity type.

## Setup

1. Create a Strava application at [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Set the Authorization Callback Domain to `localhost`
3. Add your credentials to `.env`:
   ```
   STRAVA_CLIENT_ID=your_client_id_here
   STRAVA_CLIENT_SECRET=your_client_secret_here
   ```

## Usage

```bash
uv run python main.py
```

On first run, it will open your browser for Strava authorization. Subsequent runs will use the saved token automatically.

## Output

The script displays your activities grouped by week (ISO format) and activity type, showing:
- Number of activities
- Total time in hours
- Total distance in kilometers

Example output:
```
📅 Week 2024-W25
----------------------------------------
  🏃 Ride            |  3 activities |   2.5h |   45.2km
  🏃 Run             |  2 activities |   1.2h |   12.4km
```
