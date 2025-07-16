import os
from fastapi import FastAPI, Query, HTTPException, Path, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from espn_api.football import League
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Allow only localhost for CORS (customize for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

def get_api_key(x_api_key: str = Header(...)):
    api_key = os.environ.get("API_KEY")
    if not api_key or x_api_key != api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")
    return x_api_key

def get_espn_cookies(
    espn_s2: Optional[str] = Query(None),
    swid: Optional[str] = Query(None)
):
    env_espn_s2 = os.environ.get("ESPN_S2")
    env_swid = os.environ.get("SWID")
    s2 = espn_s2 or env_espn_s2
    s = swid or env_swid
    if not s2 or not s:
        raise HTTPException(status_code=400, detail="Missing ESPN authentication cookies.")
    return s2, s

@app.get("/league/{league_id}/{year}")
def get_league_info(league_id: int, year: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        print(league)
        return {
            "league_id": league_id,
            "year": year,
            "name": getattr(league, "league_name", None),
            "current_week": getattr(league, "current_week", None),
            "num_teams": len(league.teams),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/standings")
def get_standings(league_id: int, year: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        standings = league.standings()
        return [
            {
                "team_id": t.team_id,
                "team_name": t.team_name,
                "wins": t.wins,
                "losses": t.losses,
                "ties": t.ties,
                "points_for": t.points_for,
                "points_against": t.points_against,
                "standing": t.standing,
                "final_standing": t.final_standing,
            }
            for t in standings
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/teams")
def get_teams(league_id: int, year: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        return [
            {
                "team_id": t.team_id,
                "team_name": t.team_name,
                "owners": t.owners,
                "roster": [p.name for p in t.roster],
            }
            for t in league.teams
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/teams/{team_id}")
def get_team_info(league_id: int, year: int, team_id: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        team = next((t for t in league.teams if t.team_id == team_id), None)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team_to_dict(team)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/matchup/{week}/{home_team_id}/{away_team_id}")
def get_matchup_info(league_id: int, year: int, week: int, home_team_id: int, away_team_id: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        matchups = league.scoreboard(week=week)
        for m in matchups:
            if hasattr(m, 'home_team') and hasattr(m, 'away_team'):
                if getattr(m.home_team, 'team_id', None) == home_team_id and getattr(m.away_team, 'team_id', None) == away_team_id:
                    return matchup_to_dict(m)
        raise HTTPException(status_code=404, detail="Matchup not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/free_agents")
def get_free_agents(league_id: int, year: int, week: Optional[int] = None, size: int = 50, position: Optional[str] = None, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        free_agents = league.free_agents(week=week, size=size, position=position)
        return [
            {
                "name": p.name,
                "playerId": p.playerId,
                "position": getattr(p, "position", None),
                "proTeam": getattr(p, "proTeam", None),
                "avg_points": getattr(p, "avg_points", None),
                "projected_avg_points": getattr(p, "projected_avg_points", None),
            }
            for p in free_agents
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/players/{player_id}")
def get_player_info_by_id(league_id: int, year: int, player_id: int = Path(...), api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        player = league.player_info(playerId=player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        return player_to_dict(player)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/players/by_name/{player_name}")
def get_player_info_by_name(league_id: int, year: int, player_name: str, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        player = league.player_info(name=player_name)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        if isinstance(player, list):
            return [player_to_dict(p) for p in player]
        return player_to_dict(player)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/scoreboard/{week}")
def get_scoreboard(league_id: int, year: int, week: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        matchups = league.scoreboard(week=week)
        return [matchup_to_dict(m) for m in matchups]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/boxscores/{week}")
def get_box_scores(league_id: int, year: int, week: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        boxscores = league.box_scores(week=week)
        return [boxscore_to_dict(b) for b in boxscores]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/activity")
def get_activity(league_id: int, year: int, size: int = 25, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        activity = league.recent_activity(size=size)
        return [activity_to_dict(a) for a in activity]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/messages")
def get_messages(league_id: int, year: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        messages = league.message_board()
        return messages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/power_rankings")
def get_power_rankings(league_id: int, year: int, week: Optional[int] = None, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        rankings = league.power_rankings(week=week)
        return [team_to_dict(t) for t in rankings]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/league/{league_id}/{year}/standings/{week}")
def get_standings_weekly(league_id: int, year: int, week: int, api_key: str = Depends(get_api_key), cookies: tuple = Depends(get_espn_cookies)):
    espn_s2, swid = cookies
    try:
        league = League(league_id, year, espn_s2=espn_s2, swid=swid)
        standings = league.standings_weekly(week)
        return [team_to_dict(t) for t in standings]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Serialization helpers ---
def player_to_dict(p):
    return {
        "name": getattr(p, "name", None),
        "playerId": getattr(p, "playerId", None),
        "position": getattr(p, "position", None),
        "proTeam": getattr(p, "proTeam", None),
        "injuryStatus": getattr(p, "injuryStatus", None),
        "injured": getattr(p, "injured", None),
        "onTeamId": getattr(p, "onTeamId", None),
        "lineupSlot": getattr(p, "lineupSlot", None),
        "stats": getattr(p, "stats", None),
        "schedule": getattr(p, "schedule", None),
        "total_points": getattr(p, "total_points", None),
        "projected_total_points": getattr(p, "projected_total_points", None),
        "avg_points": getattr(p, "avg_points", None),
        "projected_avg_points": getattr(p, "projected_avg_points", None),
        "percent_owned": getattr(p, "percent_owned", None),
        "percent_started": getattr(p, "percent_started", None),
        "active_status": getattr(p, "active_status", None),
    }

def team_to_dict(t):
    return {
        "team_id": getattr(t, "team_id", None),
        "team_name": getattr(t, "team_name", None),
        "owners": getattr(t, "owners", None),
        "wins": getattr(t, "wins", None),
        "losses": getattr(t, "losses", None),
        "ties": getattr(t, "ties", None),
        "points_for": getattr(t, "points_for", None),
        "points_against": getattr(t, "points_against", None),
        "standing": getattr(t, "standing", None),
        "final_standing": getattr(t, "final_standing", None),
        "waiver_rank": getattr(t, "waiver_rank", None),
        "logo_url": getattr(t, "logo_url", None),
        "roster": [player_to_dict(p) for p in getattr(t, "roster", [])],
    }

def matchup_to_dict(m):
    return {
        "home_team": team_to_dict(getattr(m, "home_team", None)) if hasattr(m, "home_team") else None,
        "away_team": team_to_dict(getattr(m, "away_team", None)) if hasattr(m, "away_team") else None,
        "home_score": getattr(m, "home_score", None),
        "away_score": getattr(m, "away_score", None),
        "is_playoff": getattr(m, "is_playoff", None),
        "matchup_type": getattr(m, "matchup_type", None),
    }

def boxscore_to_dict(b):
    return {
        "home_team": b.home_team,
        "home_score": b.home_score,
        "home_projected": b.home_projected,
        "home_lineup": [player_to_dict(p) for p in getattr(b, "home_lineup", [])],
        "away_team": b.away_team,
        "away_score": b.away_score,
        "away_projected": b.away_projected,
        "away_lineup": [player_to_dict(p) for p in getattr(b, "away_lineup", [])],
        "is_playoff": getattr(b, "is_playoff", None),
        "matchup_type": getattr(b, "matchup_type", None),
    }

def activity_to_dict(a):
    return {
        "date": getattr(a, "date", None),
        "actions": [
            {
                "team": team_to_dict(act[0]) if act[0] else None,
                "action": act[1],
                "player": player_to_dict(act[2]) if act[2] else None,
                "bid_amount": act[3],
            }
            for act in getattr(a, "actions", [])
        ],
    } 