import os
import requests
import math
from datetime import datetime

class GameIntegration:
    def fetch_stats(self, username, platform=None):
        raise NotImplementedError
        
    def get_insights(self, m1, m2, m3):
        raise NotImplementedError


class FortniteIntegration(GameIntegration):
    def fetch_stats(self, username, platform=None):
        api_key = (os.getenv("FORTNITE_API_KEY") or "").strip()
        url = "https://fortnite-api.com/v2/stats/br/v2"
        account_type_map = {"pc": "epic", "epic": "epic", "xbl": "xbl", "psn": "psn"}
        account_type = account_type_map.get(platform, "epic")
        params = {"name": username, "accountType": account_type}
        headers = {"Authorization": api_key} if api_key else {}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                return None, f"User Not Found ({r.status_code})"
            data = r.json()
            overall = data.get("data", {}).get("stats", {}).get("all", {}).get("overall", {})
            minutes = overall.get("minutesPlayed") or 0
            time_played = f"{round(minutes / 60)} Hours" if minutes else "Private"
            return {
                "main_stat": time_played,
                "detail_label": "Lifetime Wins",
                "detail_value": overall.get("wins", 0),
                "m1": float(overall.get("kd", 0)),
                "m2": float(overall.get("winRate", 0)),
                "m3": float(overall.get("wins", 0)),
                "raw_stats": [{"key": k, "value": v} for k, v in overall.items()]
            }, None
        except Exception as e:
            return None, str(e)

    def get_insights(self, m1_val, m2_val, m3_val):
        norm_m1 = min(m1_val / 5.0, 1.0) * 10
        norm_m2 = min(m2_val / 20.0, 1.0) * 10
        norm_m3 = min(m3_val / 1000.0, 1.0) * 10
        insights = []
        if m1_val > 2.0: 
            insights.append("Combat: K/D ratio suggests high mechanical skill.")
        else: 
            insights.append("Combat: Focus on positioning and survival to increase K/D.")
        if m2_val > 10.0: 
            insights.append("Strategy: Excellent win rate. Strong late-game execution.")
        return norm_m1, norm_m2, norm_m3, insights


class ClashIntegration(GameIntegration):
    def fetch_stats(self, username, platform=None):
        api_key = os.getenv("CLASH_API_KEY")
        if not api_key:
            return None, "Clash API Key missing."
        clean_tag = username.replace("#", "").upper()
        url = f"https://cocproxy.royaleapi.dev/v1/players/%23{clean_tag}"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return None, f"Clash Player Not Found ({r.status_code})"
            data = r.json()
            return {
                "main_stat": f"Town Hall {data.get('townHallLevel')}",
                "detail_label": "Trophies",
                "detail_value": data.get("trophies"),
                "m1": float(data.get("townHallLevel", 0)),
                "m2": float(data.get("trophies", 0)),
                "m3": float(data.get("warStars", 0)),
                "raw_stats": [
                    {"key": "Best Trophies", "value": data.get("bestTrophies")},
                    {"key": "War Stars", "value": data.get("warStars")},
                    {"key": "Exp Level", "value": data.get("expLevel")},
                    {"key": "Attack Wins", "value": data.get("attackWins")},
                    {"key": "Defense Wins", "value": data.get("defenseWins")}
                ]
            }, None
        except Exception as e:
            return None, str(e)

    def get_insights(self, m1_val, m2_val, m3_val):
        norm_m1 = min(m1_val / 16.0, 1.0) * 10
        norm_m2 = min(m2_val / 5000.0, 1.0) * 10
        norm_m3 = min(m3_val / 2000.0, 1.0) * 10
        insights = []
        if m1_val >= 11: 
            insights.append("Progression: High Town Hall level. Prioritize hero upgrades.")
        else: 
            insights.append("Progression: Focus on maxing resource collectors before upgrading Town Hall.")
        if m3_val > 500: 
            insights.append("Clan Wars: Veteran war attacker with high star count.")
        return norm_m1, norm_m2, norm_m3, insights


class SteamIntegration(GameIntegration):
    def fetch_stats(self, username, platform=None):
        api_key = os.getenv("STEAM_API_KEY")
        steam_id = None
        if username.isdigit() and len(username) == 17:
            steam_id = username
        else:
            url_id = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={api_key}&vanityurl={username}"
            r_id = requests.get(url_id, timeout=10)
            steam_id = r_id.json().get("response", {}).get("steamid")
        if not steam_id:
            return None, "Steam User Not Found"
        try:
            url_summary = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={api_key}&steamids={steam_id}"
            url_level = f"https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key={api_key}&steamid={steam_id}"
            r_summary = requests.get(url_summary, timeout=10)
            r_level = requests.get(url_level, timeout=10)
            player = r_summary.json().get("response", {}).get("players", [{}])[0]
            level = r_level.json().get("response", {}).get("player_level", 0)
            state_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze"}
            created_ts = player.get("timecreated")
            created_date = datetime.fromtimestamp(created_ts).strftime('%d %b %Y') if created_ts else "Hidden"
            return {
                "main_stat": f"Steam Level {level}",
                "detail_label": "Status",
                "detail_value": state_map.get(player.get("personastate"), "Private"),
                "m1": float(level),
                "m2": float(player.get("personastate", 0)),
                "m3": float(player.get("timecreated", 0)) / 1000000,
                "raw_stats": [
                    {"key": "Real Name", "value": player.get("realname", "N/A")},
                    {"key": "Country", "value": player.get("loccountrycode", "N/A")},
                    {"key": "Account Created", "value": created_date},
                    {"key": "SteamID64", "value": steam_id}
                ]
            }, None
        except Exception as e:
            return None, str(e)

    def get_insights(self, m1_val, m2_val, m3_val):
        norm_m1 = min(m1_val / 100.0, 1.0) * 10
        norm_m2 = min(m2_val / 4.0, 1.0) * 10
        norm_m3 = min(m3_val / 2000.0, 1.0) * 10
        insights = []
        if m1_val > 50: 
            insights.append("Engagement: High Steam level. Active community participant.")
        else: 
            insights.append("Engagement: Craft badges during seasonal sales to efficiently level up.")
        return norm_m1, norm_m2, norm_m3, insights


class HypixelIntegration(GameIntegration):
    def fetch_stats(self, username, platform=None):
        api_key = os.getenv("HYPIXEL_API_KEY")
        if not api_key:
            return None, "Hypixel API Key missing."
        url_uuid = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        try:
            r_uuid = requests.get(url_uuid, timeout=10)
            if r_uuid.status_code != 200:
                return None, "Minecraft Account Not Found"
            uuid = r_uuid.json().get("id")
            url_stats = f"https://api.hypixel.net/v2/player?uuid={uuid}"
            headers = {"API-Key": api_key}
            r_stats = requests.get(url_stats, headers=headers, timeout=10)
            data = r_stats.json()
            player = data.get("player")
            if not player:
                return None, "Player has no Hypixel data."
            exp = player.get("networkExp") or 0
            lvl = (math.sqrt(2 * exp + 15312.5) - 125) / 50
            login_ms = player.get("firstLogin") or 0
            login_date = datetime.fromtimestamp(login_ms / 1000.0).strftime('%d %b %Y') if login_ms else "Unknown"
            karma = player.get("karma") or 0
            achievement_points = player.get("achievementPoints") or 0
            return {
                "main_stat": f"Network Level {max(1, math.floor(lvl))}",
                "detail_label": "Karma",
                "detail_value": f"{karma:,}",
                "m1": float(lvl),
                "m2": float(karma) / 1000,
                "m3": float(achievement_points),
                "raw_stats": [
                    {"key": "Achievement Points", "value": achievement_points},
                    {"key": "First Joined", "value": login_date},
                    {"key": "Recent Game", "value": player.get("mostRecentGameType", "None")}
                ]
            }, None
        except Exception as e:
            return None, str(e)

    def get_insights(self, m1_val, m2_val, m3_val):
        norm_m1 = min(m1_val / 250.0, 1.0) * 10
        norm_m2 = min(m2_val / 5000.0, 1.0) * 10
        norm_m3 = min(m3_val / 15000.0, 1.0) * 10
        insights = []
        if m1_val > 100: 
            insights.append("Dedication: Veteran Hypixel player with high Network Level.")
        else: 
            insights.append("Progression: Complete daily challenges across minigames to boost Network Level.")
        if m2_val > 1000: 
            insights.append("Community: High Karma indicates positive player interactions.")
        return norm_m1, norm_m2, norm_m3, insights


GAME_REGISTRY = {
    'fortnite': FortniteIntegration(),
    'clash': ClashIntegration(),
    'steam': SteamIntegration(),
    'hypixel': HypixelIntegration(),
}