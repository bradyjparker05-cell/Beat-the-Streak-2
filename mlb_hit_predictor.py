"""
MLB Daily Hit Predictor
Analyzes today's games and predicts top 5 players most likely to get a hit
Based on: pitching matchups, team matchups, recent form, away team bias
"""

import requests
from datetime import datetime
from typing import List, Dict
import time


class MLBHitPredictor:
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.cache = {}
    
    def get_todays_games(self) -> List[Dict]:
        """Fetch today's schedule"""
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.base_url}/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if 'dates' in data and len(data['dates']) > 0:
                games = data['dates'][0].get('games', [])
            
            print(f"Found {len(games)} games today")
            return games
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []
    
    def get_player_season_stats(self, player_id: int) -> Dict:
        """
        Get player's season batting stats
    
        """
        cache_key = f"stats_{player_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        
        # Try current season first
        url = f"{self.base_url}/people/{player_id}/stats?stats=season&season={current_year}&group=hitting"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current_stats = {}
            current_abs = 0
            
            if 'stats' in data and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stat_data = splits[0].get('stat', {})
                    current_abs = stat_data.get('atBats', 0)
                    current_stats = {
                        'avg': float(stat_data.get('avg', 0)),
                        'obp': float(stat_data.get('obp', 0)),
                        'ops': float(stat_data.get('ops', 0)),
                        'hits': stat_data.get('hits', 0),
                        'atBats': current_abs,
                        'homeRuns': stat_data.get('homeRuns', 0),
                    }
            
            # Early season: blend with last year's stats
            # < 50 ABs: use mostly last year
            # 50-150 ABs: blend 
            # > 150 ABs: use mostly this year
            if current_abs < 150:
                last_year_stats = self._get_last_season_stats(player_id, current_year - 1)
                
                if last_year_stats and last_year_stats.get('atBats', 0) >= 100:
                    # Calculate blend weight (0 = all last year, 1 = all this year)
                    blend_weight = min(current_abs / 150.0, 1.0)
                    
                    # Blend the stats
                    blended_stats = {
                        'avg': (current_stats.get('avg', 0) * blend_weight + 
                               last_year_stats.get('avg', 0) * (1 - blend_weight)),
                        'obp': (current_stats.get('obp', 0) * blend_weight + 
                               last_year_stats.get('obp', 0) * (1 - blend_weight)),
                        'ops': (current_stats.get('ops', 0) * blend_weight + 
                               last_year_stats.get('ops', 0) * (1 - blend_weight)),
                        'hits': current_stats.get('hits', 0),
                        'atBats': current_abs,
                        'homeRuns': current_stats.get('homeRuns', 0),
                        'blended': True,
                        'blend_pct': int(blend_weight * 100)
                    }
                    
                    self.cache[cache_key] = blended_stats
                    return blended_stats
            
            self.cache[cache_key] = current_stats
            return current_stats
            
        except Exception as e:
            print(f"Error fetching stats for player {player_id}: {e}")
            return {}
    
    def _get_last_season_stats(self, player_id: int, year: int) -> Dict:
        """Get player's stats from a specific past season"""
        cache_key = f"stats_{player_id}_{year}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/people/{player_id}/stats?stats=season&season={year}&group=hitting"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            stats = {}
            if 'stats' in data and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stat_data = splits[0].get('stat', {})
                    stats = {
                        'avg': float(stat_data.get('avg', 0)),
                        'obp': float(stat_data.get('obp', 0)),
                        'ops': float(stat_data.get('ops', 0)),
                        'atBats': stat_data.get('atBats', 0),
                    }
            
            self.cache[cache_key] = stats
            return stats
        except Exception as e:
            return {}
    
    def get_player_recent_stats(self, player_id: int, days: int = 7) -> Dict:
        """
        Get player's recent performance (last N days)
        Used for hot streak detection
        """
        cache_key = f"recent_{player_id}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        url = f"{self.base_url}/people/{player_id}/stats?stats=lastXGames&limit={days}&season={current_year}&group=hitting"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            recent_stats = {}
            if 'stats' in data and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stat_data = splits[0].get('stat', {})
                    recent_stats = {
                        'avg': float(stat_data.get('avg', 0)),
                        'hits': stat_data.get('hits', 0),
                        'atBats': stat_data.get('atBats', 0),
                        'games': stat_data.get('gamesPlayed', 0),
                    }
            
            self.cache[cache_key] = recent_stats
            return recent_stats
        except Exception as e:
            print(f"Error fetching recent stats for player {player_id}: {e}")
            # Return empty dict instead of failing - we can still use season stats
            return {}
    
    def get_pitcher_stats(self, pitcher_id: int) -> Dict:
        """Get pitcher's season stats"""
        cache_key = f"pitcher_{pitcher_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        url = f"{self.base_url}/people/{pitcher_id}/stats?stats=season&season={current_year}&group=pitching"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            stats = {}
            if 'stats' in data and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stat_data = splits[0].get('stat', {})
                    stats = {
                        'era': float(stat_data.get('era', 5.00)),
                        'whip': float(stat_data.get('whip', 1.50)),
                        'avg_against': float(stat_data.get('avg', .250)),
                        'strikeouts': stat_data.get('strikeOuts', 0),
                        'walks': stat_data.get('baseOnBalls', 0),
                    }
            
            self.cache[cache_key] = stats
            return stats
        except Exception as e:
            print(f"Error fetching pitcher stats for {pitcher_id}: {e}")
            return {}
    
    def get_starting_lineup(self, game_id: int, team_type: str) -> List[Dict]:
        """
        Get starting lineup for a team
        team_type: 'away' or 'home'
        """
        url = f"{self.base_url}/game/{game_id}/boxscore"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            teams_data = data.get('teams', {})
            team_data = teams_data.get(team_type, {})
            batters = team_data.get('batters', [])
            players_info = team_data.get('players', {})
            
            lineup = []
            for batter_id in batters[:9]:  # First 9 are starters
                player_key = f"ID{batter_id}"
                if player_key in players_info:
                    player = players_info[player_key]
                    person = player.get('person', {})
                    lineup.append({
                        'id': batter_id,
                        'name': person.get('fullName', 'Unknown'),
                        'position': player.get('position', {}).get('abbreviation', 'Unknown')
                    })
            
            return lineup
        except Exception as e:
            print(f"Error fetching lineup for game {game_id}: {e}")
            return []
    
    def get_team_roster(self, team_id: int) -> List[Dict]:
        """Get current roster for a team"""
        cache_key = f"roster_{team_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/teams/{team_id}/roster"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            roster = response.json().get('roster', [])
            self.cache[cache_key] = roster
            return roster
        except Exception as e:
            print(f"Error fetching roster for team {team_id}: {e}")
            return []
    
    def _get_pitcher_hand(self, pitcher_id: int) -> str:
        """Get pitcher's throwing hand (L or R)"""
        cache_key = f"pitcher_hand_{pitcher_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/people/{pitcher_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            people = data.get('people', [])
            if people:
                hand = people[0].get('pitchHand', {}).get('code', 'R')
                self.cache[cache_key] = hand
                return hand
        except:
            pass
        
        return 'R'  # Default to RHP if unknown
    
    def get_probable_lineup(self, team_id: int, opponent_pitcher_hand: str = None) -> List[Dict]:
        """
        Predict probable lineup - FAST VERSION
        Uses roster order as simple prediction to avoid 100s of API calls
        """
        cache_key = f"probable_lineup_{team_id}_{opponent_pitcher_hand}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Get roster
        roster = self.get_team_roster(team_id)
        
        # Get injured players to filter out
        injured_ids = self.get_team_injuries(team_id)
        
        # Simple approach: take first 9 non-pitcher, non-injured position players
        position_players = []
        for player_info in roster:
            player_id = player_info.get('person', {}).get('id')
            if not player_id:
                continue
            
            # Skip pitchers
            primary_position = player_info.get('position', {}).get('type', 'Unknown')
            if primary_position == 'Pitcher':
                continue
            
            # Skip injured
            if player_id in injured_ids:
                continue
            
            position_players.append({
                'id': player_id,
                'name': player_info.get('person', {}).get('fullName', 'Unknown'),
                'position': player_info.get('position', {}).get('abbreviation', 'Unknown')
            })
            
            # Stop once we have 9
            if len(position_players) >= 9:
                break
        
        self.cache[cache_key] = position_players
        return position_players
    
    def _get_player_batting_order_stats(self, player_id: int) -> Dict:
        """
        Get player's career batting order tendencies
        Returns: {1: 0.45, 2: 0.30, 3: 0.15, ...} showing fraction of PAs at each spot
        """
        cache_key = f"order_stats_{player_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        
        # Collect data from last 2 seasons to get recent tendencies
        all_order_data = {}
        total_pas = 0
        
        for year in [current_year - 1, current_year]:
            url = f"{self.base_url}/people/{player_id}/stats?stats=season&season={year}&group=hitting&sitCodes=1,2,3,4,5,6,7,8,9&gameType=R"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'stats' in data:
                    for stat_group in data['stats']:
                        for split in stat_group.get('splits', []):
                            sit_code = split.get('split', {}).get('sitCode')
                            if sit_code and sit_code.isdigit():
                                pos = int(sit_code)
                                pas = split.get('stat', {}).get('plateAppearances', 0)
                                
                                if pos not in all_order_data:
                                    all_order_data[pos] = 0
                                all_order_data[pos] += pas
                                total_pas += pas
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                continue
        
        # Convert to fractions
        if total_pas > 50:  # Need meaningful sample
            order_fractions = {pos: (pas / total_pas) for pos, pas in all_order_data.items()}
            self.cache[cache_key] = order_fractions
            return order_fractions
        
        # Not enough data
        return {}
    
    def _get_player_platoon_data(self, player_id: int) -> Dict:
        """
        Get player's performance and usage vs LHP and RHP
        Returns: {
            'vs_LHP': {'starts': 50, 'avg': .280, 'ops': .750},
            'vs_RHP': {'starts': 100, 'avg': .310, 'ops': .850},
            'platoon_advantage': 'R'  # or 'L' or None
        }
        """
        cache_key = f"platoon_{player_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        
        platoon_data = {
            'vs_LHP': {'starts': 0, 'pas': 0, 'avg': 0, 'ops': 0},
            'vs_RHP': {'starts': 0, 'pas': 0, 'avg': 0, 'ops': 0},
            'platoon_advantage': None
        }
        
        # Get data from last 2 seasons
        for year in [current_year - 1, current_year]:
            # vs LHP
            url_lhp = f"{self.base_url}/people/{player_id}/stats?stats=season&season={year}&group=hitting&opposingPlayer=L&gameType=R"
            
            try:
                response = requests.get(url_lhp, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'stats' in data and len(data['stats']) > 0:
                    splits = data['stats'][0].get('splits', [])
                    if splits:
                        stat = splits[0].get('stat', {})
                        platoon_data['vs_LHP']['pas'] += stat.get('plateAppearances', 0)
                        platoon_data['vs_LHP']['starts'] += stat.get('gamesPlayed', 0)
                        
                        # Weight recent avg/ops by PAs
                        pas = stat.get('plateAppearances', 0)
                        if pas > 0:
                            platoon_data['vs_LHP']['avg'] += float(stat.get('avg', 0)) * pas
                            platoon_data['vs_LHP']['ops'] += float(stat.get('ops', 0)) * pas
                
                time.sleep(0.1)
            except:
                pass
            
            # vs RHP
            url_rhp = f"{self.base_url}/people/{player_id}/stats?stats=season&season={year}&group=hitting&opposingPlayer=R&gameType=R"
            
            try:
                response = requests.get(url_rhp, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'stats' in data and len(data['stats']) > 0:
                    splits = data['stats'][0].get('splits', [])
                    if splits:
                        stat = splits[0].get('stat', {})
                        platoon_data['vs_RHP']['pas'] += stat.get('plateAppearances', 0)
                        platoon_data['vs_RHP']['starts'] += stat.get('gamesPlayed', 0)
                        
                        pas = stat.get('plateAppearances', 0)
                        if pas > 0:
                            platoon_data['vs_RHP']['avg'] += float(stat.get('avg', 0)) * pas
                            platoon_data['vs_RHP']['ops'] += float(stat.get('ops', 0)) * pas
                
                time.sleep(0.1)
            except:
                pass
        
        # Calculate weighted averages
        if platoon_data['vs_LHP']['pas'] > 0:
            platoon_data['vs_LHP']['avg'] /= platoon_data['vs_LHP']['pas']
            platoon_data['vs_LHP']['ops'] /= platoon_data['vs_LHP']['pas']
        
        if platoon_data['vs_RHP']['pas'] > 0:
            platoon_data['vs_RHP']['avg'] /= platoon_data['vs_RHP']['pas']
            platoon_data['vs_RHP']['ops'] /= platoon_data['vs_RHP']['pas']
        
        # Determine platoon advantage (needs significant difference)
        total_starts = platoon_data['vs_LHP']['starts'] + platoon_data['vs_RHP']['starts']
        
        if total_starts > 20:  # Need meaningful sample
            lhp_pct = platoon_data['vs_LHP']['starts'] / total_starts
            rhp_pct = platoon_data['vs_RHP']['starts'] / total_starts
            
            # If player starts <30% vs one side, they're platooned
            if lhp_pct < 0.30:
                platoon_data['platoon_advantage'] = 'R'  # Only plays vs RHP
            elif rhp_pct < 0.30:
                platoon_data['platoon_advantage'] = 'L'  # Only plays vs LHP
        
        self.cache[cache_key] = platoon_data
        return platoon_data
    
    def _get_player_batting_order_stats(self, player_id: int) -> Dict:
        """
        Get player's career batting order tendencies
        Returns: {1: 0.45, 2: 0.30, 3: 0.15, ...} showing fraction of PAs at each spot
        """
        cache_key = f"order_stats_{player_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        current_year = datetime.now().year
        
        # Collect data from last 2 seasons to get recent tendencies
        all_order_data = {}
        total_pas = 0
        
        for year in [current_year - 1, current_year]:
            url = f"{self.base_url}/people/{player_id}/stats?stats=season&season={year}&group=hitting&sitCodes=1,2,3,4,5,6,7,8,9&gameType=R"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'stats' in data:
                    for stat_group in data['stats']:
                        for split in stat_group.get('splits', []):
                            sit_code = split.get('split', {}).get('sitCode')
                            if sit_code and sit_code.isdigit():
                                pos = int(sit_code)
                                pas = split.get('stat', {}).get('plateAppearances', 0)
                                
                                if pos not in all_order_data:
                                    all_order_data[pos] = 0
                                all_order_data[pos] += pas
                                total_pas += pas
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                continue
        
        # Convert to fractions
        if total_pas > 50:  # Need meaningful sample
            order_fractions = {pos: (pas / total_pas) for pos, pas in all_order_data.items()}
            self.cache[cache_key] = order_fractions
            return order_fractions
        
        # Not enough data
        return {}
    
    def _construct_probable_lineup(self, player_order_data: List[Dict], opponent_pitcher_hand: str = None, team_id: int = None) -> List[Dict]:
        """
        Construct most probable 9-man lineup based on career tendencies
        Filters out injured players
        """
        if not player_order_data:
            return []
        
        # Get injured players to filter out
        injured_ids = self.get_team_injuries(team_id) if team_id else []
        
        # Filter out pitchers and injured players
        position_players = [
            p for p in player_order_data 
            if p['primary_position'] != 'Pitcher' and p['id'] not in injured_ids
        ]
        
        # Sort by total career PAs (more experienced = more reliable)
        for player in position_players:
            tendencies = player['order_tendencies']
            player['total_tendency_weight'] = sum(tendencies.values()) if tendencies else 0
        
        position_players.sort(key=lambda x: x['total_tendency_weight'], reverse=True)
        
        # Build lineup - assign players to their most common spots
        lineup_slots = [None] * 9
        assigned_players = set()
        
        # First pass: assign players to their primary batting order spot
        for player in position_players:
            if len(assigned_players) >= 9:
                break
            
            tendencies = player['order_tendencies']
            if not tendencies:
                continue
            
            # Find their most common batting order position
            primary_spot = max(tendencies.items(), key=lambda x: x[1])[0]
            
            # Adjust for 0-indexing (API returns 1-9, we need 0-8)
            slot_idx = primary_spot - 1
            
            if 0 <= slot_idx < 9 and lineup_slots[slot_idx] is None:
                lineup_slots[slot_idx] = player
                assigned_players.add(player['id'])
        
        # Second pass: fill empty slots with best available players
        available_players = [p for p in position_players if p['id'] not in assigned_players]
        
        for idx in range(9):
            if lineup_slots[idx] is None and available_players:
                # Find player whose tendencies best match this spot
                best_match = None
                best_score = -1
                
                for player in available_players:
                    tendencies = player['order_tendencies']
                    score = tendencies.get(idx + 1, 0)  # Convert back to 1-9
                    
                    if score > best_score:
                        best_score = score
                        best_match = player
                
                if best_match:
                    lineup_slots[idx] = best_match
                    available_players.remove(best_match)
                    assigned_players.add(best_match['id'])
                elif available_players:
                    # No tendency data, just use next best available
                    lineup_slots[idx] = available_players.pop(0)
        
        # Convert to lineup format, filtering out None values
        probable_lineup = []
        for player in lineup_slots:
            if player:
                probable_lineup.append({
                    'id': player['id'],
                    'name': player['name'],
                    'position': player['position']
                })
        
        return probable_lineup
    
    def get_team_injuries(self, team_id: int) -> List[int]:
        """Get list of injured player IDs for a team"""
        cache_key = f"injuries_{team_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/team/{team_id}/roster/40Man"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            injured_player_ids = []
            roster = data.get('roster', [])
            
            for player_info in roster:
                status = player_info.get('status', {})
                status_code = status.get('code')
                
                # Status codes for injured list: IL, IL10, IL15, IL60
                if status_code in ['IL', 'IL10', 'IL15', 'IL60']:
                    player_id = player_info.get('person', {}).get('id')
                    if player_id:
                        injured_player_ids.append(player_id)
            
            self.cache[cache_key] = injured_player_ids
            return injured_player_ids
            
        except Exception as e:
            print(f"Error fetching injuries for team {team_id}: {e}")
            return []
    
    def calculate_hit_probability(self, player: Dict, pitcher_stats: Dict, 
                                   is_away: bool, batting_order: int) -> float:
        """
        Calculate probability score for a player getting a hit
        Higher score = more likely to get a hit
        NOW WITH HOT STREAK DETECTION
        """
        score = 0.0
        player_stats = player.get('stats', {})
        recent_7day = player.get('recent_7day', {})
        recent_14day = player.get('recent_14day', {})
        
        # Season stats (reduced weight - 30% instead of 75%)
        avg = player_stats.get('avg', 0)
        obp = player_stats.get('obp', 0)
        ops = player_stats.get('ops', 0)
        
        score += avg * 100 * 0.25  # Season avg: 0-25 points
        score += obp * 100 * 0.1   # Season OBP: 0-10 points
        score += (ops / 10) * 10   # Season OPS: 0-10 points
        
        # HOT STREAK ANALYSIS (New - 40 points possible!)
        # Last 7 days gets HEAVY weight
        if recent_7day and recent_7day.get('atBats', 0) >= 10:
            last_7_avg = recent_7day.get('avg', 0)
            score += last_7_avg * 100 * 0.3  # Up to 30 points for hot 7-day avg
            
            # Bonus for being really hot (avg > .350 last 7 days)
            if last_7_avg > 0.350:
                score += 10  # Extra 10 points for being scorching hot
            elif last_7_avg > 0.300:
                score += 5   # Extra 5 points for being hot
        
        # Last 14 days (moderate weight)
        if recent_14day and recent_14day.get('atBats', 0) >= 20:
            last_14_avg = recent_14day.get('avg', 0)
            score += last_14_avg * 100 * 0.15  # Up to 15 points for 14-day avg
        
        # Away team bonus (guaranteed extra AB)
        if is_away:
            score += 5
        
        # Batting order bonus (leadoff/2-hole get more ABs)
        if batting_order == 1:
            score += 4
        elif batting_order == 2:
            score += 3
        elif batting_order == 3:
            score += 2
        
        # Pitcher matchup analysis
        pitcher_era = pitcher_stats.get('era', 4.50)
        pitcher_avg_against = pitcher_stats.get('avg_against', 0.250)
        
        # Bad pitcher = easier to hit (0-15 points)
        if pitcher_era > 5.00:
            score += 15
        elif pitcher_era > 4.50:
            score += 10
        elif pitcher_era > 4.00:
            score += 5
        
        # High avg against = easier to hit (0-10 points)
        if pitcher_avg_against > 0.280:
            score += 10
        elif pitcher_avg_against > 0.260:
            score += 5
        
        return round(score, 2)
    
    def get_top_picks(self, limit: int = 5) -> List[Dict]:
        """Get top N players most likely to get a hit today"""
        try:
            games = self.get_todays_games()
            
            if not games:
                print("No games found for today")
                return []
            
            all_candidates = []
            
            for game in games:
                try:
                    game_id = game.get('gamePk')
                    status = game.get('status', {}).get('abstractGameState', '')
                    
                    teams = game.get('teams', {})
                    away_team = teams.get('away', {}).get('team', {})
                    home_team = teams.get('home', {}).get('team', {})
                    
                    game_desc = f"{away_team.get('name')} @ {home_team.get('name')}"
                    
                    # Skip games that already started or are postponed
                    if status not in ['Preview', 'Pre-Game']:
                        continue
                    
                    # Get probable pitchers
                    away_pitcher_data = teams.get('away', {}).get('probablePitcher')
                    home_pitcher_data = teams.get('home', {}).get('probablePitcher')
                    
                    if not away_pitcher_data or not home_pitcher_data:
                        continue
                    
                    away_pitcher_id = away_pitcher_data.get('id')
                    home_pitcher_id = home_pitcher_data.get('id')
                    
                    # Get pitcher stats
                    home_pitcher_stats = self.get_pitcher_stats(home_pitcher_id)
                    away_pitcher_stats = self.get_pitcher_stats(away_pitcher_id)
                    
                    # Rate limiting - be nice to the API
                    time.sleep(0.5)
                    
                    # ALWAYS predict lineups based on career + pitcher matchup
                    # This ensures we get picks for ALL games, not just ones with posted lineups
                    away_team_id = away_team.get('id')
                    home_team_id = home_team.get('id')
                    
                    # Try to get official lineups first
                    official_away = self.get_starting_lineup(game_id, 'away')
                    official_home = self.get_starting_lineup(game_id, 'home')
                    
                    # Use official if available, otherwise use intelligent prediction
                    away_lineup = official_away if official_away else self.get_probable_lineup(away_team_id, None)
                    home_lineup = official_home if official_home else self.get_probable_lineup(home_team_id, None)
                    
                    # Skip only if we can't predict anything (shouldn't happen)
                    if not away_lineup and not home_lineup:
                        continue
                    
                    time.sleep(0.5)
                    
                    # Process away team (vs home pitcher)
                    for idx, player in enumerate(away_lineup, 1):
                        try:
                            player_stats = self.get_player_season_stats(player['id'])
                            
                            # Check if we have enough data (current + last year combined)
                            current_abs = player_stats.get('atBats', 0) if player_stats else 0
                            
                            # If blended, we have last year's data backing it up
                            has_sufficient_data = (
                                player_stats and 
                                (current_abs >= 20 or player_stats.get('blended', False))
                            )
                            
                            if not has_sufficient_data:
                                continue
                            
                            # Get recent performance (hot streak detection)
                            recent_7 = self.get_player_recent_stats(player['id'], days=7)
                            recent_14 = self.get_player_recent_stats(player['id'], days=14)
                            
                            player['stats'] = player_stats
                            player['recent_7day'] = recent_7
                            player['recent_14day'] = recent_14
                            
                            score = self.calculate_hit_probability(
                                player, home_pitcher_stats, is_away=True, batting_order=idx
                            )
                            
                            all_candidates.append({
                                'name': player['name'],
                                'team': away_team.get('name'),
                                'opponent': home_team.get('name'),
                                'vs_pitcher': home_pitcher_data.get('fullName'),
                                'batting_avg': player_stats.get('avg', 0),
                                'last_7_avg': recent_7.get('avg', 0) if recent_7 else 0,
                                'score': score,
                                'position': player['position'],
                                'order': idx,
                                'location': 'Away',
                                'blended': player_stats.get('blended', False),
                                'blend_pct': player_stats.get('blend_pct', 0)
                            })
                        except Exception as e:
                            print(f"Error processing away player {player.get('name', 'Unknown')}: {e}")
                            continue
                    
                    # Process home team (vs away pitcher)
                    for idx, player in enumerate(home_lineup, 1):
                        try:
                            player_stats = self.get_player_season_stats(player['id'])
                            
                            # Check if we have enough data (current + last year combined)
                            current_abs = player_stats.get('atBats', 0) if player_stats else 0
                            
                            # If blended, we have last year's data backing it up
                            has_sufficient_data = (
                                player_stats and 
                                (current_abs >= 20 or player_stats.get('blended', False))
                            )
                            
                            if not has_sufficient_data:
                                continue
                            
                            # Get recent performance (hot streak detection)
                            recent_7 = self.get_player_recent_stats(player['id'], days=7)
                            recent_14 = self.get_player_recent_stats(player['id'], days=14)
                            
                            player['stats'] = player_stats
                            player['recent_7day'] = recent_7
                            player['recent_14day'] = recent_14
                            
                            score = self.calculate_hit_probability(
                                player, away_pitcher_stats, is_away=False, batting_order=idx
                            )
                            
                            all_candidates.append({
                                'name': player['name'],
                                'team': home_team.get('name'),
                                'opponent': away_team.get('name'),
                                'vs_pitcher': away_pitcher_data.get('fullName'),
                                'batting_avg': player_stats.get('avg', 0),
                                'last_7_avg': recent_7.get('avg', 0) if recent_7 else 0,
                                'score': score,
                                'position': player['position'],
                                'order': idx,
                                'location': 'Home',
                                'blended': player_stats.get('blended', False),
                                'blend_pct': player_stats.get('blend_pct', 0)
                            })
                        except Exception as e:
                            print(f"Error processing home player {player.get('name', 'Unknown')}: {e}")
                            continue
                
                except Exception as e:
                    print(f"Error processing game: {e}")
                    continue
            
            # Sort by score and get top picks
            all_candidates.sort(key=lambda x: x['score'], reverse=True)
            top_picks = all_candidates[:limit]
            
            return top_picks
        
        except Exception as e:
            print(f"Fatal error in get_top_picks: {e}")
            return []
    
    def format_picks_message(self, picks: List[Dict], previous_picks: List[Dict] = None) -> str:
        """Format the top picks into a readable SMS message"""
        if not picks:
            return None  # Return None instead of message when no picks
        
        # Check if picks are identical to previous run (avoid duplicate texts)
        if previous_picks and len(picks) == len(previous_picks):
            # Compare player IDs in order
            current_ids = [p['name'] for p in picks]
            previous_ids = [p['name'] for p in previous_picks]
            
            if current_ids == previous_ids:
                print("Picks unchanged from previous run - skipping SMS to avoid duplicate")
                return None
        
        from datetime import timezone, timedelta
        
        # Get current time in ET (UTC - 5 for EST, UTC - 4 for EDT)
        # Assuming EDT (daylight time) for baseball season
        et_offset = timedelta(hours=-4)
        et_time = datetime.now(timezone.utc) + et_offset
        
        today = et_time.strftime('%A, %b %d')
        current_time = et_time.strftime('%I:%M %p ET')
        run_id = et_time.strftime('%H%M')  # Add unique identifier per run
        message = f"TOP 5 HIT PICKS - {today} ({current_time})\n\n"
        
        for i, pick in enumerate(picks, 1):
            message += f"{i}. {pick['name']} ({pick['team'][:3]})\n"
            message += f"   vs {pick['vs_pitcher']}\n"
            
            # Show hot streak indicator
            last_7 = pick.get('last_7_avg', 0)
            if last_7 > 0.350:
                hot_indicator = "🔥🔥🔥"  # Scorching hot
            elif last_7 > 0.300:
                hot_indicator = "🔥🔥"    # Hot
            elif last_7 > 0.250:
                hot_indicator = "🔥"      # Warm
            else:
                hot_indicator = ""
            
            # Show if stats are blended with last year
            blend_note = ""
            if pick.get('blended', False):
                blend_pct = pick.get('blend_pct', 0)
                blend_note = f" ({blend_pct}% '25)"
            
            message += f"   AVG: {pick['batting_avg']:.3f}{blend_note}"
            if last_7 > 0:
                message += f" | L7: {last_7:.3f} {hot_indicator}"
            message += f"\n   {pick['location']} | #{pick['order']} | Score: {pick['score']}\n\n"
        
        message += "🔥 = Hot last 7 days"
        if any(p.get('blended') for p in picks):
            message += "\n(X% '25) = Blended with 2025 stats"
        message += "\nGood luck!"
        
        return message


if __name__ == "__main__":
    predictor = MLBHitPredictor()
    picks = predictor.get_top_picks(5)
    print(predictor.format_picks_message(picks))
