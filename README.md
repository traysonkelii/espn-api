# ESPN Fantasy Football REST API

A production-ready REST API for accessing ESPN Fantasy Football league data, built with FastAPI.

## Frameworks & Tech

- **FastAPI** (web framework)
- **Uvicorn** (ASGI server)
- **Gunicorn** (production process manager)
- **requests** (HTTP client, used internally)

## Authentication & Security

- **API Key Required:** All endpoints require an `X-API-KEY` header. The value must match the `API_KEY` environment variable (set in your `.env` file or on Render).
- **ESPN Cookies:** The API uses `ESPN_S2` and `SWID` from environment variables by default. You can override these with query parameters for testing.
- **CORS:** By default, only requests from localhost are allowed. Update the CORS settings in `api_server.py` for your production frontend domain.

## .env Setup Example

Create a `.env` file in your project root:

```
ESPN_S2=your_espn_s2_cookie_here
SWID=your_swid_cookie_here
API_KEY=your_api_key_or_jwt_here
```

- On Render, add these as environment variables in the dashboard.
- The `API_KEY` can be a long random string or a JWT.

## API Usage

All requests must include:

- `X-API-KEY` header (required)
- ESPN cookies are read from environment variables, but can be overridden with `espn_s2` and `swid` query parameters if needed.

## API Endpoints

### League

- `GET /league/{league_id}/{year}`
  - League summary/info
- `GET /league/{league_id}/{year}/standings`
  - Current standings
- `GET /league/{league_id}/{year}/standings/{week}`
  - Standings for a specific week
- `GET /league/{league_id}/{year}/power_rankings`
  - Power rankings (optionally pass `week` as a query param)

### Teams

- `GET /league/{league_id}/{year}/teams`
  - List all teams (basic info)
- `GET /league/{league_id}/{year}/teams/{team_id}`
  - Team details, including roster and player injury status

### Players

- `GET /league/{league_id}/{year}/players/{player_id}`
  - Player info and stats by player ID
- `GET /league/{league_id}/{year}/players/by_name/{player_name}`
  - Player info and stats by player name
- `GET /league/{league_id}/{year}/free_agents`
  - List of available free agents
    - Query params: `week` (int), `size` (int), `position` (str)

### Matchups & Scores

- `GET /league/{league_id}/{year}/scoreboard/{week}`
  - Weekly matchups and scores
- `GET /league/{league_id}/{year}/boxscores/{week}`
  - Detailed box scores for a week
- `GET /league/{league_id}/{year}/matchup/{week}/{home_team_id}/{away_team_id}`
  - Detailed info for a specific matchup

### Activity & Messages

- `GET /league/{league_id}/{year}/activity`
  - Recent league activity (add/drop/trade)
  - Query param: `size` (int)
- `GET /league/{league_id}/{year}/messages`
  - League message board

## Query Parameters

- `espn_s2` and `swid` are optional query parameters (for override/testing). By default, the API uses the values from environment variables.

## Running the REST API server

Install dependencies:

    pip install -r requirements.txt

Run the FastAPI server locally:

    uvicorn espn_api.api_server:app --reload

The API will be available at http://127.0.0.1:8000

Interactive docs: http://127.0.0.1:8000/docs

## Deploying to Render

1. Push your code to GitHub.
2. Create a new Web Service on [Render.com](https://render.com/).
3. Set the build command:
   pip install -r requirements.txt
4. Set the start command:
   gunicorn -k uvicorn.workers.UvicornWorker espn_api.api_server:app
5. Add your environment variables (`API_KEY`, `ESPN_S2`, `SWID`) in the Render dashboard.
6. Deploy and access your API at the provided URL.

## Securing Your API

- **API Key:** Only requests with the correct `X-API-KEY` header will be processed.
- **CORS:** Update the allowed origins in `api_server.py` to restrict which frontends can access your API.
- **ESPN Cookies:** Keep your ESPN cookies and API key secret. Never expose them in client-side code or public repos.
