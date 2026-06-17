import os
import requests
import math
import hashlib
import numpy as np
from datetime import datetime
import concurrent.futures
from django.core.cache import cache

def get_euclidean_similarity(v1, v2):
    v1 = np.array(v1, dtype=float)
    v2 = np.array(v2, dtype=float)
    max_len = max(len(v1), len(v2), 1)
    if max_len > 12:
        max_len = 12
    v1 = v1[:12]
    v2 = v2[:12]
    v1 = np.pad(v1, (0, max_len - len(v1)))
    v2 = np.pad(v2, (0, max_len - len(v2)))
    dist = np.linalg.norm(v1 - v2)
    sim = 1.0 / (1.0 + dist)
    return round(sim * 100, 1)

class GameIntegration:
    def fetch_stats(self, username, platform=None):
        raise NotImplementedError
        
    def get_insights(self, stats_data):
        raise NotImplementedError

    def get_future_predictions(self, prediction, stats_data):
        return []

    def normalize_metrics(self, stats_data, max_values):
        norms = []
        for i, max_val in enumerate(max_values):
            val = float(stats_data.get(f'm{i+1}', 0))
            norms.append(min(val / max_val, 1.0) * 10 if max_val else 0)
        return norms
        
    def calculate_future(self, stats_data, prediction, max_values):
        futures = []
        for i, max_val in enumerate(max_values):
            current = float(stats_data.get(f'm{i+1}', 0))
            diff = (prediction.get(f'future_m{i+1}', 0) / 10.0) * max_val
            futures.append(current + diff)
        return futures

    def get_comparison_vector(self, stats_data):
        return []

    def get_comparison_display(self, stats_data):
        return stats_data.get('raw_stats', [])

    def generate_llm_insights(self, game_name, stats_data):
        stats_str = ", ".join([f"{s['key']}: {s['value']}" for s in stats_data.get('raw_stats', [])])
        stats_hash = hashlib.md5(stats_str.encode()).hexdigest()
        cache_key = f"llm_insight_{stats_hash}"
        
        cached_insights = cache.get(cache_key)
        if cached_insights:
            return cached_insights
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return ["GEMINI_API_KEY not configured in .env file."]
            
        try:
            prompt = f"You are an aggressive, hyper-competitive esports coach. Analyze these {game_name} player stats: {stats_str}. Provide exactly 2 distinct, brutally honest tactical insights or tips (max 1 sentence each) to make the player better. Format them as plain text lines separated by a newline, with no bullet points, no markdown, and no asterisks."
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code != 200:
                print(f"Gemini HTTP Error: {response.text}")
                if response.status_code == 429:
                    return ["AI Rate Limit Reached.", "Please wait about 30 seconds before analyzing another profile."]
                try:
                    error_details = response.json().get("error", {}).get("message", "Unknown error")
                except:
                    error_details = "Invalid API Key or Server Error"
                return [f"API Error {response.status_code}:", error_details]
                
            resp_json = response.json()
            text_output = resp_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            insights = [line.strip('- *') for line in text_output.strip().split('\n') if line.strip()][:2]
            cache.set(cache_key, insights, 3600)
            return insights
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return ["Tactical AI analysis currently offline due to server load."]

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
        norms = self.normalize_metrics(stats_data, [5.0, 20.0, 1000.0])
        insights = self.generate_llm_insights("Fortnite", stats_data)
        return {"norms": norms, "insights": insights}

    def get_comparison_vector(self, stats_data):
        norms = self.normalize_metrics(stats_data, [5.0, 20.0, 1000.0])
        return [n / 10.0 for n in norms]

    def get_comparison_display(self, stats_data):
        return [
            {"key": "K/D Ratio", "value": f"{float(stats_data.get('m1', 0)):.2f}"},
            {"key": "Win Rate", "value": f"{float(stats_data.get('m2', 0)):.1f}%"},
            {"key": "Total Wins", "value": f"{int(stats_data.get('m3', 0)):,}"}
        ]

    def get_future_predictions(self, prediction, stats_data):
        f = self.calculate_future(stats_data, prediction, [5.0, 20.0, 1000.0])
        return [
            {"label": "Projected Future K/D", "value": round(f[0], 2)},
            {"label": "Projected Future Win Rate", "value": f"{round(f[1], 1)}%"},
            {"label": "Projected Future Wins", "value": int(f[2])}
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
        norms = self.normalize_metrics(stats_data, [16.0, 5000.0, 2000.0])
        insights = self.generate_llm_insights("Clash of Clans", stats_data)
        return {"norms": norms, "insights": insights}

    def get_comparison_vector(self, stats_data):
        norms = self.normalize_metrics(stats_data, [16.0, 5000.0, 2000.0])
        return [n / 10.0 for n in norms]

    def get_comparison_display(self, stats_data):
        return [
            {"key": "Town Hall", "value": f"{int(stats_data.get('m1', 0))}"},
            {"key": "Trophies", "value": f"{int(stats_data.get('m2', 0)):,}"},
            {"key": "War Stars", "value": f"{int(stats_data.get('m3', 0)):,}"}
        ]

    def get_future_predictions(self, prediction, stats_data):
        f = self.calculate_future(stats_data, prediction, [16.0, 5000.0, 2000.0])
        return [
            {"label": "Projected Town Hall", "value": int(f[0])},
            {"label": "Projected Trophies", "value": int(f[1])},
            {"label": "Projected War Stars", "value": int(f[2])}
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
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                f_summary = executor.submit(requests.get, url_summary, timeout=10)
                f_level = executor.submit(requests.get, url_level, timeout=10)
                r_summary = f_summary.result()
                r_level = f_level.result()
                
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
        norms = self.normalize_metrics(stats_data, [100.0, 0, 0])
        insights = self.generate_llm_insights("Steam", stats_data)
        return {"norms": norms, "insights": insights}

    def get_comparison_vector(self, stats_data):
        norms = self.normalize_metrics(stats_data, [100.0])
        return [n / 10.0 for n in norms]

    def get_comparison_display(self, stats_data):
        return [
            {"key": "Steam Level", "value": f"{int(stats_data.get('m1', 0))}"}
        ]

    def get_future_predictions(self, prediction, stats_data):
        f = self.calculate_future(stats_data, prediction, [100.0, 0, 0])
        return [
            {"label": "Projected Steam Level", "value": int(f[0])}
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
            
            sb_level = sb_xp / 100
            
            return {
                "main_stat": f"Skyblock Level {math.floor(sb_level)}",
                "detail_label": "Combat XP",
                "detail_value": f"{int(combat_xp):,}",
                "m1": float(sb_xp),
                "m2": float(combat_xp),
                "m3": float(cata_xp),
                "m4": float(mining_xp),
                "m5": float(farming_xp),
                "m6": float(foraging_xp),
                "m7": float(fishing_xp),
                "m8": 0.0,
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
        max_vals = [50000.0, 111672425.0, 5698096400.0, 111672425.0, 111672425.0, 111672425.0, 111672425.0, 0.0]
        norms = self.normalize_metrics(stats_data, max_vals)
        insights = self.generate_llm_insights("Minecraft Hypixel Skyblock", stats_data)
        return {"norms": norms, "insights": insights}

    SKILL_XP = [
        0, 50, 175, 375, 675, 1175, 1925, 2925, 4425, 6425,
        9925, 14925, 22425, 32425, 47425, 67425, 97425, 147425, 222425, 322425,
        522425, 822425, 1222425, 1722425, 2322425, 3022425, 3822425, 4722425, 5722425, 6822425,
        8022425, 9322425, 10722425, 12222425, 13822425, 15522425, 17322425, 19222425, 21222425, 23322425,
        25522425, 27822425, 30222425, 32722425, 35322425, 38072425, 40972425, 44072425, 47472425, 51172425,
        55172425, 59472425, 64072425, 68972425, 74172425, 79672425, 85472425, 91572425, 97972425, 104672425,
        111672425
    ]

    CATA_XP = [
        0, 50, 125, 235, 395, 625, 955, 1425, 2095, 3045,
        4385, 6275, 8940, 12700, 17960, 25340, 35640, 50040, 70040, 97640,
        135640, 188140, 259640, 356640, 488640, 668640, 911640, 1239640, 1684640, 2284640,
        3084640, 4149640, 5559640, 7459640, 9959640, 13259640, 17559640, 23159640, 30359640, 39559640,
        51559640, 66559640, 85559640, 109559640, 139559640, 177559640, 225559640, 285559640, 360559640, 453559640,
        569809640
    ]

    def _get_level(self, xp, table):
        if xp <= 0: return 0.0
        if xp >= table[-1]: return float(len(table) - 1)
        for i in range(1, len(table)):
            if xp < table[i]:
                return float(i - 1) + ((xp - table[i-1]) / (table[i] - table[i-1]))
        return 0.0

    def get_comparison_vector(self, stats_data):
        sb_lvl = min(float(stats_data.get('m1', 0)) / 100.0, 600.0)
        combat_lvl = min(self._get_level(float(stats_data.get('m2', 0)), self.SKILL_XP), 60.0)
        cata_lvl = min(self._get_level(float(stats_data.get('m3', 0)), self.CATA_XP), 50.0)
        mining_lvl = min(self._get_level(float(stats_data.get('m4', 0)), self.SKILL_XP), 60.0)
        farming_lvl = min(self._get_level(float(stats_data.get('m5', 0)), self.SKILL_XP), 60.0)
        foraging_lvl = min(self._get_level(float(stats_data.get('m6', 0)), self.SKILL_XP), 60.0)
        fishing_lvl = min(self._get_level(float(stats_data.get('m7', 0)), self.SKILL_XP), 60.0)

        return [sb_lvl / 600.0, combat_lvl / 60.0, mining_lvl / 60.0, farming_lvl / 60.0, foraging_lvl / 60.0, fishing_lvl / 60.0, cata_lvl / 50.0]

    def get_comparison_display(self, stats_data):
        sb_lvl = float(stats_data.get('m1', 0)) / 100.0
        combat_lvl = self._get_level(float(stats_data.get('m2', 0)), self.SKILL_XP)
        cata_lvl = min(self._get_level(float(stats_data.get('m3', 0)), self.CATA_XP), 50.0)
        mining_lvl = self._get_level(float(stats_data.get('m4', 0)), self.SKILL_XP)
        farming_lvl = self._get_level(float(stats_data.get('m5', 0)), self.SKILL_XP)
        foraging_lvl = min(self._get_level(float(stats_data.get('m6', 0)), self.SKILL_XP), 60.0)
        fishing_lvl = min(self._get_level(float(stats_data.get('m7', 0)), self.SKILL_XP), 60.0)

        return [
            {"key": "Skyblock Level", "value": f"{int(sb_lvl)}"},
            {"key": "Combat Level", "value": f"{combat_lvl:.1f}"},
            {"key": "Mining Level", "value": f"{mining_lvl:.1f}"},
            {"key": "Farming Level", "value": f"{farming_lvl:.1f}"},
            {"key": "Foraging Level", "value": f"{foraging_lvl:.1f}"},
            {"key": "Fishing Level", "value": f"{fishing_lvl:.1f}"},
            {"key": "Catacombs Level", "value": f"{cata_lvl:.1f}"}
        ]

    def get_future_predictions(self, prediction, stats_data):
        max_vals = [50000.0, 111672425.0, 5698096400.0, 111672425.0, 111672425.0, 111672425.0, 111672425.0, 0.0]
        f = self.calculate_future(stats_data, prediction, max_vals)
        sb_level = f[0] / 100
        return [
            {"label": "7-Day Projected SB Level", "value": f"{int(sb_level)}"},
            {"label": "7-Day Projected Combat XP", "value": f"{int(f[1]):,}"},
            {"label": "7-Day Projected Cata XP", "value": f"{int(f[2]):,}"},
            {"label": "7-Day Projected Mining XP", "value": f"{int(f[3]):,}"},
            {"label": "7-Day Projected Farming XP", "value": f"{int(f[4]):,}"},
            {"label": "7-Day Projected Foraging XP", "value": f"{int(f[5]):,}"},
            {"label": "7-Day Projected Fishing XP", "value": f"{int(f[6]):,}"}
        ]

GAME_REGISTRY = {
    'fortnite': FortniteIntegration(),
    'clash': ClashIntegration(),
    'steam': SteamIntegration(),
    'hypixel': HypixelIntegration(),
}