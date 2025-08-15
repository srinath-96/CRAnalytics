import requests
import pandas as pd
import os
from datetime import datetime

# ==== CONFIG ====
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjljMThlYTRkLTI3OWQtNGQ5YS1iMTVmLWM4NmNhYWM4YTVhOCIsImlhdCI6MTc1NTE5NzYzMywic3ViIjoiZGV2ZWxvcGVyLzU4MTg1YjliLWQ4ODItMzQ1Ni0zZWEzLWMzYmIyY2QxNDM0MCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5OS43Mi4yMDcuNDIiXSwidHlwZSI6ImNsaWVudCJ9XX0.aE3TY9oRdE3SjFaYEwr44iaXwnStKE5cAibA-k4jzw-TRFcDNCq-EupEwdXRWbJLALLZ82aohdo0L301oX-7rQ"
PLAYER_TAG = "#89YC92L9"  # Include the #
OUTPUT_FILE = "battle_log.csv"
BATTLELOG_URL = f"https://api.clashroyale.com/v1/players/{PLAYER_TAG.replace('#', '%23')}/battlelog"

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def fetch_battles():
    """Fetch latest battles from Royale API."""
    resp = requests.get(BATTLELOG_URL, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()
# Add these near the top of your script (config/constants)
FULL_KING_HP = 4000          # placeholder default, adjust if you want a different baseline
FULL_PRINCESS_HP = 2534      # placeholder default, adjust if you want a different baseline

def process_battles(raw_data):
    import pandas as pd

    def safe_card_name(card):
        name_field = card.get("name", "")
        if isinstance(name_field, dict):
            return name_field.get("en", "") or next(iter(name_field.values()), "")
        return str(name_field)

    battles = []
    for b in raw_data:
        team = (b.get("team") or [{}])[0]
        opponent = (b.get("opponent") or [{}])[0]

        # Decks
        my_deck = [safe_card_name(c) for c in team.get("cards", [])]
        opp_deck = [safe_card_name(c) for c in opponent.get("cards", [])]

        # Remaining tower HP at end of match (API gives end-state)
        my_king_hp = team.get("kingTowerHitPoints", FULL_KING_HP) or FULL_KING_HP
        my_princess_hp = team.get("princessTowersHitPoints", []) or []
        opp_king_hp = opponent.get("kingTowerHitPoints", FULL_KING_HP) or FULL_KING_HP
        opp_princess_hp = opponent.get("princessTowersHitPoints", []) or []

        # Normalize princess arrays to length 2 for arithmetic
        def pad_princess(hps):
            hps = list(hps)
            if len(hps) == 0: return [FULL_PRINCESS_HP, FULL_PRINCESS_HP]
            if len(hps) == 1: return [hps[0], FULL_PRINCESS_HP]
            return hps[:2]
        my_princess_hp = pad_princess(my_princess_hp)
        opp_princess_hp = pad_princess(opp_princess_hp)

        # Approx damage using assumed full HP baselines
        my_damage_taken = (FULL_KING_HP - my_king_hp) + sum(FULL_PRINCESS_HP - hp for hp in my_princess_hp)
        my_damage_dealt = (FULL_KING_HP - opp_king_hp) + sum(FULL_PRINCESS_HP - hp for hp in opp_princess_hp)

        battles.append({
            "battleTime": pd.to_datetime(b.get("battleTime"), format="%Y%m%dT%H%M%S.%fZ", errors="coerce"),
            "battleType": b.get("type"),
            "my_crowns": team.get("crowns"),
            "opp_crowns": opponent.get("crowns"),
            "my_deck": ",".join(my_deck),
            "opp_deck": ",".join(opp_deck),
            "my_damage_dealt": my_damage_dealt,
            "my_damage_taken": my_damage_taken,
            "win": (team.get("crowns") is not None and opponent.get("crowns") is not None and team.get("crowns") > opponent.get("crowns"))
        })

    return pd.DataFrame(battles)

OUTPUT_FILE = "/Users/srinathmurali/Desktop/CRAnalytics/battles.csv"  # or whatever you're using

def append_new_battles(new_df):
    if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
        # Load existing data
        old_df = pd.read_csv(OUTPUT_FILE, parse_dates=["battleTime"])
        # Combine and drop duplicates by battleTime
        combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset=["battleTime"])
    else:
        # No file or empty file: just use the new data
        combined_df = new_df

    combined_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(combined_df)} total battles to {OUTPUT_FILE}")
def main():
    raw_data = fetch_battles()
    print(raw_data)
    new_df = process_battles(raw_data)
    append_new_battles(new_df)
    print(f"[{datetime.now()}] Logged {len(new_df)} battles.")

if __name__ == "__main__":
    main()
