import json
from typing import List, Set, Union

from ..base_league import BaseLeague
from .team import Team
from .player import Player
from .matchup import Matchup
from .box_score import get_box_scoring_type_class, BoxScore
from .activity import Activity
from .transaction import Transaction
from .constant import POSITION_MAP, ACTIVITY_MAP, TRANSACTION_TYPES

class League(BaseLeague):
    teams: List[Team]
    '''Creates a League instance for Public/Private ESPN league'''
    def __init__(self, league_id: int, year: int, espn_s2=None, swid=None, fetch_league=True, debug=False):
        super().__init__(league_id=league_id, year=year, sport='nba', espn_s2=espn_s2, swid=swid, debug=debug)

        if fetch_league:
            self.fetch_league()

    def fetch_league(self):
        data = self._fetch_league()
        self._fetch_teams(data)
        super()._fetch_draft()

        self.BoxScoreClass = get_box_scoring_type_class(self.settings.scoring_type)

    def _fetch_league(self):
        data = super()._fetch_league()

        self._fetch_players()
        self._map_matchup_ids(data['schedule'])
        return(data)

    def _map_matchup_ids(self, schedule):
        self.matchup_ids = {}
        for match in schedule:
            matchup_period = match.get('matchupPeriodId')
            scoring_periods = match.get('home', {}).get('pointsByScoringPeriod', {}).keys()
            if len(scoring_periods) > 0:
                if matchup_period not in self.matchup_ids:
                    self.matchup_ids[matchup_period] = sorted(scoring_periods)
                else:
                    self.matchup_ids[matchup_period] = sorted(set(self.matchup_ids[matchup_period] + list(scoring_periods)))


    def _fetch_teams(self, data):
        '''Fetch teams in league'''
        self.pro_schedule = self._get_all_pro_schedule()
        super()._fetch_teams(data, TeamClass=Team, pro_schedule=self.pro_schedule)

        # replace opponentIds in schedule with team instances
        for team in self.teams:
            team.division_name = self.settings.division_map.get(team.division_id, '')
            for week, matchup in enumerate(team.schedule):
                for opponent in self.teams:
                    if matchup.away_team == opponent.team_id:
                        matchup.away_team = opponent
                    if matchup.home_team == opponent.team_id:
                        matchup.home_team = opponent

    def standings(self) -> List[Team]:
        standings = sorted(self.teams, key=lambda x: x.final_standing if x.final_standing != 0 else x.standing, reverse=False)
        return standings

    def scoreboard(self, matchupPeriod: int = None) -> List[Matchup]:
        '''Returns list of matchups for a given matchup period'''
        if not matchupPeriod:
            matchupPeriod=self.currentMatchupPeriod

        params = {
            'view': 'mMatchup',
        }
        data = self.espn_request.league_get(params=params)
        schedule = data['schedule']
        matchups = [Matchup(matchup) for matchup in schedule if matchup['matchupPeriodId'] == matchupPeriod]

        for team in self.teams:
            for matchup in matchups:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team

        return matchups

    def recent_activity(self, size: int = 25, msg_type: str = None, offset: int = 0, include_moved=False) -> List[Activity]:
        '''Returns a list of recent league activities (Add, Drop, Trade)'''
        if self.year < 2019:
            raise Exception('Cant use recent activity before 2019')

        msg_types = [178,180,179,239,181,244,188]
        if msg_type in ACTIVITY_MAP:
            msg_types = [ACTIVITY_MAP[msg_type]]
        params = {
            'view': 'kona_league_communication'
        }

        filters = {"topics":{"filterType":{"value":["ACTIVITY_TRANSACTIONS"]},"limit":size,"limitPerMessageSet":{"value":25},"offset":offset,"sortMessageDate":{"sortPriority":1,"sortAsc":False},"sortFor":{"sortPriority":2,"sortAsc":False},"filterIncludeMessageTypeIds":{"value":msg_types}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}
        data = self.espn_request.league_get(extend='/communication/', params=params, headers=headers)
        data = data['topics']
        activity = [Activity(topic, self.player_map, self.get_team_data, include_moved=include_moved) for topic in data]

        return activity

    def transactions(self, scoring_period: int = None, types: Set[str] = {"FREEAGENT","WAIVER","WAIVER_ERROR"}) -> List[Transaction]:
        '''Returns a list of recent transactions'''
        if not scoring_period:
            scoring_period = self.scoringPeriodId

        if types > TRANSACTION_TYPES:
            raise Exception('Invalid transaction type')

        params = {
            'view': 'mTransactions2',
            'scoringPeriodId': scoring_period,
        }

        filters = {"transactions":{"filterType":{"value":list(types)}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}

        data = self.espn_request.league_get(params=params, headers=headers)
        transactions = data['transactions']

        return [Transaction(transaction, self.player_map, self.get_team_data) for transaction in transactions]

    def free_agents(self, week: int=None, size: int=50, position: str=None, position_id: int=None) -> List[Player]:
        '''Returns a List of Free Agents for a Given Week\n
        Should only be used with most recent season'''

        if self.year < 2019:
            raise Exception('Cant use free agents before 2019')
        if not week:
            week = self.current_week

        slot_filter = []
        if position and position in POSITION_MAP:
            slot_filter = [POSITION_MAP[position]]
        if position_id:
            slot_filter.append(position_id)


        params = {
            'view': 'kona_player_info',
            'scoringPeriodId': week,
        }
        filters = {"players":{"filterStatus":{"value":["FREEAGENT","WAIVERS"]},"filterSlotIds":{"value":slot_filter},"limit":size,"sortPercOwned":{"sortPriority":1,"sortAsc":False},"sortDraftRanks":{"sortPriority":100,"sortAsc":True,"value":"STANDARD"}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}

        data = self.espn_request.league_get(params=params, headers=headers)
        players = data['players']

        return [Player(player, self.year) for player in players]

    def box_scores(self, matchup_period: int = None, scoring_period: int = None, matchup_total: bool = True) -> List[BoxScore]:
        '''Returns list of box score for a given matchup or scoring period'''
        if self.year < 2019:
            raise Exception('Cant use box score before 2019')

        matchup_id = self.currentMatchupPeriod
        scoring_id = self.current_week
        if matchup_period and scoring_period:
            matchup_id = matchup_period
            scoring_id = scoring_period
        elif matchup_period and matchup_period < matchup_id:
            matchup_id = matchup_period
            scoring_id = self.matchup_ids[matchup_period][-1] if matchup_period in self.matchup_ids else 1
        elif scoring_period and scoring_period <= scoring_id:
            scoring_id = scoring_period
            for matchup in self.matchup_ids.keys():
                if str(scoring_id) in self.matchup_ids[matchup]:
                    matchup_id = matchup
                    break

        params = {
            'view': ['mMatchupScore', 'mScoreboard'],
            'scoringPeriodId': scoring_id
        }

        filters = {"schedule":{"filterMatchupPeriodIds":{"value":[matchup_id]}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}
        data = self.espn_request.league_get(params=params, headers=headers)

        schedule = data['schedule']
        box_data = [self.BoxScoreClass(matchup, self.pro_schedule, matchup_total, self.year, scoring_id) for matchup in schedule]

        for team in self.teams:
            for matchup in box_data:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team
        return box_data

    def player_info(self, name: str = None, playerId: Union[int, list] = None, include_news = False) -> Union[Player, List[Player]]:
        ''' Returns Player class if name found '''

        if name:
            playerId = self.player_map.get(name)
        if playerId is None or isinstance(playerId, str):
            return None
        if not isinstance(playerId, list):
            playerId = [playerId]

        data = self.espn_request.get_player_card(playerId, self.finalScoringPeriod)

        if include_news:
            news = {}
            for id in playerId:
                news[id] = self.espn_request.get_player_news(id)

        if len(data['players']) == 1:
            return Player(data['players'][0], self.year, self.pro_schedule, news=news.get(playerId[0], []) if include_news else None)
        if len(data['players']) > 1:
            return [Player(player, self.year, self.pro_schedule, news=news.get(player['id'], []) if include_news else None) for player in data['players']]