import os
import requests
import math
from datetime import datetime

class GameIntegration:
    def fetch_stats(self, username, platform=None):
        raise NotImplementedError
        
    def get_insights(self, stats_data):
        raise NotImplementedError

    def get_future_predictions(self, prediction, stats_data):
        return []


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

    def get_insights(self, stats_data):
        m1_val = float(stats_data.get('m1', 0))
        m2_val = float(stats_data.get('m2', 0))
        m3_val = float(stats_data.get('m3', 0))
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
        return {"norms": [norm_m1, norm_m2, norm_m3], "insights": insights}

    def get_future_predictions(self, prediction, stats_data):
        current_m1 = float(stats_data.get('m1', 0))
        current_m2 = float(stats_data.get('m2', 0))
        current_m3 = float(stats_data.get('m3', 0))
        kd = current_m1 + ((prediction.get('future_m1', 0) / 10.0) * 5.0)
        win_rate = current_m2 + ((prediction.get('future_m2', 0) / 10.0) * 20.0)
        wins = current_m3 + ((prediction.get('future_m3', 0) / 10.0) * 1000.0)
        return [
            {"label": "Projected Future K/D", "value": round(kd, 2)},
            {"label": "Projected Future Win Rate", "value": f"{round(win_rate, 1)}%"},
            {"label": "Projected Future Wins", "value": int(wins)}
        ]

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

    def get_insights(self, stats_data):
        m1_val = float(stats_data.get('m1', 0))
        m2_val = float(stats_data.get('m2', 0))
        m3_val = float(stats_data.get('m3', 0))
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
        return {"norms": [norm_m1, norm_m2, norm_m3], "insights": insights}

    def get_future_predictions(self, prediction, stats_data):
        current_m1 = float(stats_data.get('m1', 0))
        current_m2 = float(stats_data.get('m2', 0))
        current_m3 = float(stats_data.get('m3', 0))
        th = current_m1 + ((prediction.get('future_m1', 0) / 10.0) * 16.0)
        trophies = current_m2 + ((prediction.get('future_m2', 0) / 10.0) * 5000.0)
        stars = current_m3 + ((prediction.get('future_m3', 0) / 10.0) * 2000.0)
        return [
            {"label": "Projected Town Hall", "value": int(th)},
            {"label": "Projected Trophies", "value": int(trophies)},
            {"label": "Projected War Stars", "value": int(stars)}
        ]

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

    def get_insights(self, stats_data):
        m1_val = float(stats_data.get('m1', 0))
        norm_m1 = min(m1_val / 100.0, 1.0) * 10
        insights = []
        if m1_val > 50: 
            insights.append("Engagement: High Steam level. Active community participant.")
        else: 
            insights.append("Engagement: Craft badges during seasonal sales to efficiently level up.")
        return {"norms": [norm_m1, 0, 0], "insights": insights}

    def get_future_predictions(self, prediction, stats_data):
        current_m1 = float(stats_data.get('m1', 0))
        level = current_m1 + ((prediction.get('future_m1', 0) / 10.0) * 100.0)
        return [
            {"label": "Projected Steam Level", "value": int(level)}
        ]

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
            
            url_stats = f"https://api.hypixel.net/v2/skyblock/profiles?uuid={uuid}"
            headers = {"API-Key": api_key}
            r_stats = requests.get(url_stats, headers=headers, timeout=10)
            data = r_stats.json()
            
            profiles = data.get("profiles")
            if not profiles:
                return None, "Player has no Skyblock data."
                
            profile = next((p for p in profiles if p.get("selected")), profiles[0])
            clean_uuid = uuid.replace("-", "")
            member = profile.get("members", {}).get(clean_uuid, {})
            
            if not member:
                return None, "No member data found in profile."
                
            player_data = member.get("player_data", {})
            exp_data = player_data.get("experience", {})
            
            sb_xp = member.get("leveling", {}).get("experience", 0)
            combat_xp = exp_data.get("SKILL_COMBAT", 0)
            mining_xp = exp_data.get("SKILL_MINING", 0)
            farming_xp = exp_data.get("SKILL_FARMING", 0)
            foraging_xp = exp_data.get("SKILL_FORAGING", 0)
            fishing_xp = exp_data.get("SKILL_FISHING", 0)
            cata_xp = member.get("dungeons", {}).get("dungeon_types", {}).get("catacombs", {}).get("experience", 0)
            
            purse = member.get("coin_purse", 0)
            bank = profile.get("banking", {}).get("balance", 0.0)
            # 1. Safely extract purse (checks new 'currencies' object, falls back to old)
            currencies = member.get("currencies", {})
            purse = currencies.get("coin_purse") if currencies.get("coin_purse") is not None else member.get("coin_purse", 0.0)
            
            # 2. Extract Co-op Bank
            coop_bank = profile.get("banking", {}).get("balance", 0.0)
            if coop_bank is None: coop_bank = 0.0
            
            # 3. Extract Personal Bank (Check new currencies object first, then old)
            personal_bank = currencies.get("bank")
            if personal_bank is None:
                personal_bank = member.get("profile", {}).get("personal_bank_account", 0.0)
            if personal_bank is None: personal_bank = 0.0
            
            bank = float(coop_bank) + float(personal_bank)
            total_wealth = purse + bank
            
            sb_level = sb_xp / 100
            
            return {
                "main_stat": f"Skyblock Level {math.floor(sb_level)}",
                "detail_label": "Combat XP",
                "detail_value": f"{int(combat_xp):,}",
                "m1": float(sb_xp),
                "m2": float(combat_xp),
                "m3": float(total_wealth),
                "m4": float(mining_xp),
                "m5": float(farming_xp),
                "m6": float(foraging_xp),
                "m7": float(fishing_xp),
                "m8": float(cata_xp),
                "raw_stats": [
                    {"key": "Skyblock XP", "value": f"{int(sb_xp):,}"},
                    {"key": "Combat XP", "value": f"{int(combat_xp):,}"},
                    {"key": "Mining XP", "value": f"{int(mining_xp):,}"},
                    {"key": "Farming XP", "value": f"{int(farming_xp):,}"},
                    {"key": "Foraging XP", "value": f"{int(foraging_xp):,}"},
                    {"key": "Fishing XP", "value": f"{int(fishing_xp):,}"},
                    {"key": "Catacombs XP", "value": f"{int(cata_xp):,}"}
                ]
            }, None
        except Exception as e:
            return None, str(e)

    def get_insights(self, stats_data):
        m1_val = float(stats_data.get('m1', 0))
        m2_val = float(stats_data.get('m2', 0))
        m3_val = float(stats_data.get('m3', 0))
        m4_val = float(stats_data.get('m4', 0))
        m5_val = float(stats_data.get('m5', 0))
        m6_val = float(stats_data.get('m6', 0))
        m7_val = float(stats_data.get('m7', 0))
        m8_val = float(stats_data.get('m8', 0))
        
        norm_m1 = min(m1_val / 50000.0, 1.0) * 10
        norm_m2 = min(m2_val / 100000000.0, 1.0) * 10
        norm_m3 = min(m3_val / 5000000000.0, 1.0) * 10
        norm_m4 = min(m4_val / 100000000.0, 1.0) * 10
        norm_m5 = min(m5_val / 100000000.0, 1.0) * 10
        norm_m6 = min(m6_val / 50000000.0, 1.0) * 10
        norm_m7 = min(m7_val / 50000000.0, 1.0) * 10
        norm_m8 = min(m8_val / 500000000.0, 1.0) * 10
        
        insights = []
        if m1_val > 20000: 
            insights.append("Progression: High Skyblock XP indicates strong mid-to-endgame status.")
        else: 
            insights.append("Progression: Focus on fairy souls and cheap accessories to gain early XP.")
        if m3_val > 500000000: 
            insights.append("Economy: Strong wealth generation. Consider investing in minion upgrades.")
        return {"norms": [norm_m1, norm_m2, norm_m3, norm_m4, norm_m5, norm_m6, norm_m7, norm_m8], "insights": insights}

    def get_future_predictions(self, prediction, stats_data):
        c_m1, c_m2, c_m3 = float(stats_data.get('m1', 0)), float(stats_data.get('m2', 0)), float(stats_data.get('m3', 0))
        c_m4, c_m5, c_m6 = float(stats_data.get('m4', 0)), float(stats_data.get('m5', 0)), float(stats_data.get('m6', 0))
        c_m7, c_m8 = float(stats_data.get('m7', 0)), float(stats_data.get('m8', 0))
        
        sb_xp = c_m1 + ((prediction.get('future_m1', 0) / 10.0) * 50000.0)
        combat_xp = c_m2 + ((prediction.get('future_m2', 0) / 10.0) * 100000000.0)
        wealth = c_m3 + ((prediction.get('future_m3', 0) / 10.0) * 5000000000.0)
        mining_xp = c_m4 + ((prediction.get('future_m4', 0) / 10.0) * 100000000.0)
        farming_xp = c_m5 + ((prediction.get('future_m5', 0) / 10.0) * 100000000.0)
        foraging_xp = c_m6 + ((prediction.get('future_m6', 0) / 10.0) * 50000000.0)
        fishing_xp = c_m7 + ((prediction.get('future_m7', 0) / 10.0) * 50000000.0)
        cata_xp = c_m8 + ((prediction.get('future_m8', 0) / 10.0) * 500000000.0)
        
        sb_level = sb_xp / 100
        return [
            {"label": "7-Day Projected SB Level", "value": f"{int(sb_level)}"},
            {"label": "7-Day Projected Combat XP", "value": f"{int(combat_xp):,}"},
            {"label": "7-Day Projected Mining XP", "value": f"{int(mining_xp):,}"},
            {"label": "7-Day Projected Farming XP", "value": f"{int(farming_xp):,}"},
            {"label": "7-Day Projected Foraging XP", "value": f"{int(foraging_xp):,}"},
            {"label": "7-Day Projected Fishing XP", "value": f"{int(fishing_xp):,}"},
            {"label": "7-Day Projected Cata XP", "value": f"{int(cata_xp):,}"}
        ]

GAME_REGISTRY = {
    'fortnite': FortniteIntegration(),
    'clash': ClashIntegration(),
    'steam': SteamIntegration(),
    'hypixel': HypixelIntegration(),
}