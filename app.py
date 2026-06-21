import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import json
from collections import Counter
import altair as alt
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# 1. PAGE SETUP & "POCKET GARDEN" GLASSMORPHISM STYLING
# ==========================================
st.set_page_config(page_title="Addu's Garden", page_icon="🌷", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,500&family=Quicksand:wght@400;500;600;700&display=swap');

    :root {
        --emerald: #1fa97a;
        --emerald-deep: #168a63;
        --emerald-soft: #8fe3c4;
        --rose: #ef6f93;
        --rose-deep: #e0527b;
        --rose-soft: #ffd1de;
        --gold: #f4b942;
        --cream: #fffaf6;
        --ink: #34313c;
        --ink-soft: #8a8694;
        --lotus-light: #ffb7c5;
        --lotus-deep: #fa8072;
    }

    html, body, [class*="css"], .stMarkdown {
        font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: linear-gradient(160deg, #e1f8ee 0%, #fdeef4 42%, #fff3e6 75%, #ffe7ef 100%);
        background-attachment: fixed;
    }

    @keyframes floatIn {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes blossom {
        from { opacity: 0; transform: scale(0.86); }
        to   { opacity: 1; transform: scale(1); }
    }
    @keyframes flicker {
        0%, 100% { transform: scale(1) rotate(0deg); }
        50% { transform: scale(1.15) rotate(-4deg); }
    }

    /* ---- Title ---- */
    .app-title {
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 30px;
        text-align: center;
        margin: 4px 0 0 0;
        background: linear-gradient(100deg, var(--emerald-deep) 0%, var(--rose-deep) 35%, var(--gold) 50%, var(--rose-deep) 65%, var(--emerald-deep) 100%);
        background-size: 250% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: floatIn 0.6s ease both, shimmerText 7s linear infinite 0.6s;
    }
    @keyframes shimmerText {
        0% { background-position: 0% 50%; }
        100% { background-position: 250% 50%; }
    }
    .app-subtitle {
        text-align: center;
        font-size: 12px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--ink-soft);
        margin-bottom: 18px;
        animation: floatIn 0.6s ease both;
    }

    /* ---- Greeting "note" card ---- */
    .note-card {
        background: rgba(255,255,255,0.55);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.7);
        border-radius: 22px;
        padding: 24px 26px 20px 26px;
        margin-bottom: 16px;
        position: relative;
        animation: floatIn 0.7s ease both, breathe 5s ease-in-out infinite 0.7s;
    }
    @keyframes breathe {
        0%, 100% { box-shadow: 0 10px 30px rgba(239,111,147,0.14); }
        50% { box-shadow: 0 16px 40px rgba(239,111,147,0.24); }
    }
    .note-card::before {
        content: "🌿";
        position: absolute;
        top: -15px; left: 22px;
        font-size: 18px;
        background: var(--cream);
        border-radius: 50%;
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    }
    .note-text {
        font-family: 'Fraunces', serif;
        font-style: italic;
        font-weight: 500;
        font-size: 17px;
        line-height: 1.65;
        color: #4a4654;
        text-align: center;
        margin: 0;
    }

    /* ---- Streak pill ---- */
    .streak-pill {
        display: inline-flex; align-items: center; gap: 7px;
        background: linear-gradient(135deg, #fff3e0, #ffe3ec);
        border-radius: 999px;
        padding: 7px 18px;
        font-weight: 700;
        font-size: 13.5px;
        box-shadow: 0 4px 14px rgba(244,185,66,0.22);
        margin-bottom: 8px;
        animation: floatIn 0.7s ease both;
    }
    .streak-pill .flame { display: inline-block; animation: flicker 1.8s ease-in-out infinite; }

    .milestone-line {
        font-size: 13.5px;
        color: var(--ink-soft);
        margin: 3px 2px;
        animation: floatIn 0.6s ease both;
    }

    /* ---- Section labels ---- */
    .section-eyebrow {
        font-weight: 700;
        font-size: 12.5px;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: var(--ink-soft);
        margin: 26px 2px 12px 2px;
    }

    /* ---- Bloom macro cards ---- */
    .bloom-card {
        background: rgba(255,255,255,0.55);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.65);
        border-radius: 20px;
        padding: 18px 8px 14px 8px;
        text-align: center;
        margin: 6px 0 10px 0;
        box-shadow: 0 8px 22px rgba(0,0,0,0.05);
        animation: blossom 0.5s ease both;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .bloom-card:hover { transform: translateY(-3px); box-shadow: 0 14px 28px rgba(0,0,0,0.08); }
    .bloom-ring {
        width: 72px; height: 72px;
        border-radius: 50%;
        margin: 0 auto 10px auto;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 0 5px rgba(255,255,255,0.55);
    }
    .bloom-inner {
        width: 54px; height: 54px;
        border-radius: 50%;
        background: var(--cream);
        display: flex; align-items: center; justify-content: center;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
    }
    .bloom-icon { font-size: 21px; }
    .bloom-label { font-weight: 700; font-size: 13px; color: var(--ink); margin-top: 1px; letter-spacing: 0.01em; }
    .bloom-value { font-family: 'Fraunces', serif; font-weight: 600; font-size: 19px; color: var(--ink); margin-top: 1px; }
    .bloom-unit { font-size: 11.5px; font-weight: 500; color: var(--ink-soft); margin-left: 2px; }
    .bloom-target { font-size: 11px; color: var(--ink-soft); margin-top: 1px; }

    /* ---- Flourish divider ---- */
    .bloom-divider {
        display: flex; align-items: center; justify-content: center;
        margin: 8px 0 6px 0;
        color: var(--ink-soft);
    }
    .bloom-divider::before, .bloom-divider::after {
        content: ""; flex: 1; height: 1px;
        background: linear-gradient(to right, transparent, rgba(0,0,0,0.12), transparent);
    }
    .bloom-divider span { padding: 0 12px; font-size: 14px; }

    /* ---- Cycle companion card with Shifting Skin-Tone Flow Gradient ---- */
    .cycle-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 20px;
        padding: 16px 18px;
        margin-bottom: 10px;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.65);
        box-shadow: 0 8px 20px rgba(0,0,0,0.04);
        animation: floatIn 0.6s ease both;
    }
    
    .cycle-idle { 
        background: linear-gradient(90deg, 
            rgba(143, 227, 196, 0.45) 0%, 
            rgba(255, 250, 246, 0.70) 60%, 
            rgba(255, 209, 222, 0.60) 100%
        ) !important;
    }
    
    .cycle-active { 
        background: linear-gradient(90deg, 
            rgba(255, 182, 200, 0.55) 0%, 
            rgba(255, 250, 246, 0.70) 60%, 
            rgba(143, 227, 196, 0.50) 100%
        ) !important;
    }
    
    .cycle-left-layout {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .cycle-icon { font-size: 27px; }
    .cycle-title { font-weight: 700; font-size: 14.5px; color: var(--ink); }
    .cycle-sub { font-size: 12.5px; color: var(--ink-soft); margin-top: 1px; }

    /* Translucent Right Aligned Countdown Badge */
    .cycle-countdown-pill {
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-style: italic;
        font-size: 14px;
        color: #5a5465;
        background: rgba(255, 255, 255, 0.5);
        padding: 5px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        white-space: nowrap;
    }

    /* Cycle outlook banner */
    .cycle-outlook {
        border-radius: 14px;
        padding: 10px 16px;
        margin-bottom: 10px;
        font-weight: 600;
        font-size: 13px;
        animation: floatIn 0.5s ease both;
    }
    .outlook-late { background: linear-gradient(135deg, rgba(239,111,147,0.20), rgba(239,111,147,0.08)); color: var(--rose-deep); border: 1px solid rgba(239,111,147,0.25); }
    .outlook-due  { background: linear-gradient(135deg, rgba(244,185,66,0.22), rgba(244,185,66,0.08)); color: #8a6512; border: 1px solid rgba(244,185,66,0.3); }
    .outlook-warn { background: linear-gradient(135deg, rgba(239,111,147,0.16), rgba(255,255,255,0.3)); color: var(--rose-deep); border: 1px solid rgba(239,111,147,0.2); }
    .outlook-good { background: linear-gradient(135deg, rgba(31,169,122,0.18), rgba(31,169,122,0.06)); color: var(--emerald-deep); border: 1px solid rgba(31,169,122,0.25); }

    /* ---- Buttons ---- */
    .stButton>button, .stFormSubmitButton>button {
        border-radius: 999px;
        font-weight: 700;
        font-family: 'Quicksand', sans-serif;
        border: none;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { transform: translateY(-1px); }
    .stButton>button:active, .stFormSubmitButton>button:active { transform: translateY(0px); }

    div[class*="st-key-start_cycle_btn"] button {
        background: linear-gradient(135deg, var(--lotus-light) 0%, var(--lotus-deep) 100%) !important;
        color: white !important;
        padding: 0 24px; height: 2.5em;
        box-shadow: 0 6px 16px rgba(255,183,197,0.32);
        position: relative; overflow: hidden;
    }
    div[class*="st-key-end_cycle_btn"] button {
        background: linear-gradient(135deg, var(--lotus-light) 0%, var(--lotus-deep) 100%) !important;
        color: white !important;
        padding: 0 24px; height: 2.5em;
        box-shadow: 0 6px 16px rgba(255,183,197,0.32);
        position: relative; overflow: hidden;
    }

    div[class*="st-key-cta_"] button {
        width: 100%;
        height: 2.9em;
        background: linear-gradient(135deg, var(--emerald) 0%, var(--rose) 100%) !important;
        color: white !important;
        box-shadow: 0 8px 18px rgba(239,111,147,0.24);
        position: relative; overflow: hidden;
    }

    div[class*="st-key-start_cycle_btn"] button::after,
    div[class*="st-key-end_cycle_btn"] button::after,
    div[class*="st-key-cta_"] button::after {
        content: "";
        position: absolute; top: 0; left: -60%;
        width: 45%; height: 100%;
        background: linear-gradient(120deg, transparent, rgba(255,255,255,0.5), transparent);
        transform: skewX(-20deg);
        transition: left 0.6s ease;
    }
    div[class*="st-key-start_cycle_btn"] button:hover::after,
    div[class*="st-key-end_cycle_btn"] button:hover::after,
    div[class*="st-key-cta_"] button:hover::after {
        left: 130%;
    }

    div[class*="st-key-btn_"] button {
        background: rgba(255,255,255,0.6) !important;
        color: var(--ink) !important;
        border: 1px solid rgba(0,0,0,0.07) !important;
        padding: 0 14px; height: 2.15em;
        font-size: 12.5px;
        font-weight: 600;
        box-shadow: none;
    }
    div[class*="st-key-btn_"] button:hover { background: rgba(255,255,255,0.92) !important; }

    div[data-testid="stExpander"] {
        background: rgba(255,255,255,0.42) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,0.6) !important;
        backdrop-filter: blur(8px);
        margin-bottom: 12px;
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary { font-weight: 700 !important; }

    hr { border-color: rgba(0,0,0,0.06) !important; }
    </style>
""", unsafe_allow_html=True)

class MacroData(BaseModel):
    calories: float = Field(description="Total energy value in kcal")
    protein: float = Field(description="Protein content in grams")
    carbs: float = Field(description="Carbohydrates content in grams")
    fats: float = Field(description="Fats content in grams")

# Initialize Secrets
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# TIME SYNCHRONIZATION SYSTEM VARIABLES
IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str = now.strftime("%Y-%m-%d")
current_hour = now.hour
day_of_year = now.timetuple().tm_yday

# ==========================================
# AIRTABLE WRITE HELPERS
# ==========================================
def airtable_post(table, fields):
    try:
        resp = requests.post(
            f"https://api.airtable.com/v0/{BASE_ID}/{table}",
            headers=headers,
            json={"records": [{"fields": fields}], "typecast": True}
        )
        if resp.ok: return True, None
        try: err = resp.json().get("error", {}).get("message", resp.text)
        except Exception: err = resp.text
        return False, err
    except Exception as e: return False, str(e)

def airtable_patch(table, record_id, fields):
    try:
        resp = requests.patch(
            f"https://api.airtable.com/v0/{BASE_ID}/{table}",
            headers=headers,
            json={"records": [{"id": record_id, "fields": fields}], "typecast": True}
        )
        if resp.ok: return True, None
        try: err = resp.json().get("error", {}).get("message", resp.text)
        except Exception: err = resp.text
        return False, err
    except Exception as e: return False, str(e)

# ==========================================
# 2. DATA ACQUISITION PIPELINE
# ==========================================
@st.cache_data(ttl=3)
def fetch_airtable_all(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}?maxRecords=100"
        if table_name in ["Diet", "Weight"]:
            url += "&sort[0][field]=Timestamp&sort[0][direction]=desc"
        elif table_name == "Cycles":
            url += "&sort[0][field]=Start Date&sort[0][direction]=desc"
        res = requests.get(url, headers=headers).json()
        return res.get("records", [])
    except Exception: return []

diet_records = fetch_airtable_all("Diet")
weight_records = fetch_airtable_all("Weight")
moments_records = fetch_airtable_all("Moments")
cycle_records = fetch_airtable_all("Cycles")
profile_records = fetch_airtable_all("Profile")

# Parse Profile Map
profile_map = {}
profile_row_ids = {}
for r in profile_records:
    f_name = r.get("fields", {}).get("Field")
    f_val = r.get("fields", {}).get("Value")
    if f_name:
        profile_map[f_name] = f_val
        profile_row_ids[f_name] = r.get("id")

# ==========================================
# 3. HORIZONTAL TRACKING CYCLE ENGINE 
# ==========================================
is_period_active = False
last_start_date = None
last_end_date = None
active_row_id = None

if cycle_records:
    latest_row = cycle_records[0]
    active_row_id = latest_row.get("id")
    latest_fields = latest_row.get("fields", {})
    
    s_str = latest_fields.get("Start Date", "")
    e_str = latest_fields.get("End Date", "")
    
    if s_str:
        try: last_start_date = datetime.strptime(s_str, "%Y-%m-%d").date()
        except Exception: pass
    if e_str:
        try: last_end_date = datetime.strptime(e_str, "%Y-%m-%d").date()
        except Exception: pass
        
    if s_str and not e_str:
        is_period_active = True

# ==========================================
# 4. ONBOARDING WIZARD INTERFACE
# ==========================================
is_onboarded = bool(profile_map.get("Calories"))

if not is_onboarded:
    st.markdown('<div class="note-card"><p class="note-text">🌸 Welcome to Addu\'s Garden 🧸<br>Let\'s set up your custom health parameters baseline right now.</p></div>', unsafe_allow_html=True)
    with st.form("onboarding_form"):
        h_in = st.number_input("Height (cm)", min_value=100, max_value=250, value=160)
        w_in = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=55.0, step=0.1)
        act_in = st.selectbox("Exercise Frequency / Activity Level", [
            "Sedentary (Little or no exercise)",
            "Lightly Active (Light exercise 1-3 days/week)",
            "Moderately Active (Moderate exercise 3-5 days/week)",
            "Very Active (Hard exercise 6-7 days/week)"
        ])
        submit_setup = st.form_submit_button("Generate My Custom Dashboard", key="cta_onboard")

        if submit_setup:
            try:
                bmr = 447.593 + (9.247 * w_in) + (3.098 * h_in) - (4.330 * 23)
                multiplier = 1.2
                if "Lightly" in act_in: multiplier = 1.375
                elif "Moderately" in act_in: multiplier = 1.55
                elif "Very" in act_in: multiplier = 1.725

                tdee = bmr * multiplier
                target_cal = round(tdee - 350)
                target_carbs = round((target_cal * 0.40) / 4)
                target_protein = round((target_cal * 0.30) / 4)
                target_fats = round((target_cal * 0.30) / 9)

                updates = {
                    "Height": str(h_in), "Weight": str(w_in), "ActivityLevel": act_in,
                    "Calories": str(target_cal), "Carbs": str(target_carbs),
                    "Protein": str(target_protein), "Fats": str(target_fats)
                }

                failures = []
                for field_key, field_val in updates.items():
                    r_id = profile_row_ids.get(field_key)
                    if r_id:
                        ok, err = airtable_patch("Profile", r_id, {"Value": field_val})
                        if not ok: failures.append(f"{field_key}: {err}")
                if failures:
                    st.error("Some values didn't save: " + " | ".join(failures))
                else:
                    st.success("Your customized dashboard has been calculated and initialized! Loading...")
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Setup Error: {e}")
    st.stop()

THRESHOLDS = {
    "Calories": {"low": float(profile_map.get("Calories", 1400)) - 50, "high": float(profile_map.get("Calories", 1400)), "reverse": False},
    "Carbs": {"low": float(profile_map.get("Carbs", 130)) - 10, "high": float(profile_map.get("Carbs", 130)), "reverse": False},
    "Fats": {"low": float(profile_map.get("Fats", 40)) - 5, "high": float(profile_map.get("Fats", 40)), "reverse": False},
    "Protein": {"low": float(profile_map.get("Protein", 80)), "high": float(profile_map.get("Protein", 80)) + 15, "reverse": True}
}

# ==========================================
# 5. HIGH-END ROTATING PHRASE COMPLIMENTS ENGINE
# ==========================================
st.markdown('<div class="app-title">🌷 Addu\'s Garden 🧸</div>', unsafe_allow_html=True)
st.markdown(f'<div class="app-subtitle">{now.strftime("%A · %B %d")}</div>', unsafe_allow_html=True)

# Calculate Streak
logged_dates = set()
for r in diet_records:
    ts = r.get("fields", {}).get("Timestamp", "")
    if ts: logged_dates.add(ts.split(" ")[0])
for r in weight_records:
    ts = r.get("fields", {}).get("Timestamp", "")
    if ts: logged_dates.add(ts.split(" ")[0])

streak = 0
check_date = now
while check_date.strftime("%Y-%m-%d") in logged_dates:
    streak += 1
    check_date -= timedelta(days=1)

# Phrase matrices mapping
phrases_morning = [
    "Good morning, beautiful! 🧸 Wish you have a great day ahead...",
    "Morning sunshine! You look absolutely radiant today, time to conquer the day!",
    "Good morning, prettiest lady! Hoping your morning coffee is as sweet and amazing as you are.",
    "Wake up, darling! The world gets a little brighter the moment you open those gorgeous eyes."
]
phrases_afternoon = [
    "How has your day been, princess? If you ever want to talk or vent, remember I'm always just one call away...",
    "Hope your shifts and classes are treating you well! You look super hottttt today, keep killing it!",
    "Just a midday reminder that you are the most brilliant and stunning girl I know.",
    "Sending you some afternoon energy, beautiful. Keep smiling, you've completely got this!"
]
phrases_evening = [
    "You look so breathtakingly beautiful tonight. Rest that brilliant mind of yours.",
    "You did incredibly today, darling. You are genuinely the prettiest lady I have ever talked to.",
    "Time to wind down and relax, princess. You look incredibly gorgeous even at the end of a long day.",
    "Sleep early tonight and get some sweet dreams, darling. Good night 🧸"
]
phrases_global = [
    "Honestly, you look so super hottttt it's distracting.",
    "Just in case no one told you yet today: you are absolutely perfect in every single way.",
    "You have the most beautiful soul and the prettiest face I've ever seen.",
    "Genuinely so proud of how hard you work. You're beautiful and brilliant.",
    "You make everything better just by being you, darling.",
    "You are the absolute finest, prettiest lady ever.",
    "Hope you're looking in the mirror today, because you look jaw-droppingly gorgeous.",
    "My absolute favorite person to see tracking. Keep shining, beautiful."
]

if 5 <= current_hour < 12: selected_greeting = phrases_morning[day_of_year % 4]
elif 12 <= current_hour < 17: selected_greeting = phrases_afternoon[day_of_year % 4]
elif 17 <= current_hour < 22: selected_greeting = phrases_evening[day_of_year % 4]
else: selected_greeting = phrases_global[day_of_year % 8]

if is_period_active:
    selected_greeting = [
        "I know today might feel physically heavy, beautiful. Please make sure to drink some warm water and rest up. Remember I'm always just one call away if you need anything.",
        "Take it slow today, darling. You're doing amazing, and your health comes first. Warm tea and cozy blankets only.",
        "Sending you the biggest comforting vibes. Rest your mind and body today, you look beautiful as always.",
        "Listen to your body today, princess. Don't stress about targets; comfort, warm water, and self-care are your only goals right now."
    ][day_of_year % 4]

st.markdown(f'<div class="note-card"><p class="note-text">{selected_greeting}</p></div>', unsafe_allow_html=True)

# Build Horizontal Prediction Regularity Messages
all_starts = []
for r in reversed(cycle_records):
    s = r.get("fields", {}).get("Start Date", "")
    if s:
        try: all_starts.append(datetime.strptime(s, "%Y-%m-%d").date())
        except Exception: pass

avg_cycle_len = 28
if len(all_starts) >= 2:
    gaps = [(all_starts[i] - all_starts[i-1]).days for i in range(1, len(all_starts))]
    clean_gaps = [g for g in gaps if 15 <= g <= 50]
    if clean_gaps: avg_cycle_len = round(sum(clean_gaps) / len(clean_gaps))

today_date = now.date()
cycle_banner = None

if all_starts:
    last_start = all_starts[-1]
    if is_period_active:
        if len(all_starts) >= 2:
            predicted_current = all_starts[-2] + timedelta(days=avg_cycle_len)
            diff = (last_start - predicted_current).days
            if diff <= 1: cycle_banner = ("good", "Perfect cycle — started right on time 💚")
            elif diff <= 4: cycle_banner = ("warn", f"Started {diff} days later than usual — hope you're doing okay 🩷")
            else: cycle_banner = ("warn", f"Sorry love, this one took {diff} days longer than usual to start 🩷")
        else:
            cycle_banner = ("good", "First cycle logged — I'll start tracking her rhythm from here 🌱")
    else:
        predicted_next = last_start + timedelta(days=avg_cycle_len)
        if today_date > predicted_next:
            days_late = (today_date - predicted_next).days
            cycle_banner = ("late", f"Running late by {days_late} day{'s' if days_late != 1 else ''} — no pressure, log it whenever it starts 💗")
        elif today_date == predicted_next:
            cycle_banner = ("due", "Expected to start today 🌷")
        else:
            days_until = (predicted_next - today_date).days
            cycle_banner = ("upcoming", f"Expected around {predicted_next.strftime('%b %d')} · {days_until} day{'s' if days_until != 1 else ''} away")

# ==========================================
# 6. CHROMATIC METRIC BOARDS ("Bloom" rings)
# ==========================================
today_cal, today_protein, today_carbs, today_fats = 0.0, 0.0, 0.0, 0.0
food_history_pool = []

for record in diet_records:
    fields = record.get("fields", {})
    ts = fields.get("Timestamp", "")
    food_item = fields.get("Food Items", "")
    if food_item: food_history_pool.append(food_item.strip())
    if ts and ts.startswith(today_str):
        today_cal += float(fields.get("Calories", 0))
        today_protein += float(fields.get("Protein", 0))
        today_carbs += float(fields.get("Carbs", 0))
        today_fats += float(fields.get("Fats", 0))

if streak > 0:
    st.markdown(f'<div class="streak-pill"><span class="flame">🔥</span> {streak} Day Consistency Streak — you are doing incredible</div>', unsafe_allow_html=True)

# Pinned Moments
for record in moments_records:
    fields = record.get("fields", {})
    if fields.get("Show On Top") is True:
        m_date_str = fields.get("Date", "")
        m_text = fields.get("Moment", "")
        if m_date_str and m_text:
            try:
                days_since = (now.date() - datetime.strptime(m_date_str, "%Y-%m-%d").date()).days
                st.markdown(f'<div class="milestone-line">✨ <b>{m_text}:</b> {days_since} days running! Phenomenal work.</div>', unsafe_allow_html=True)
            except Exception: continue

cal_color = get_status_color(today_cal, **THRESHOLDS["Calories"])
carb_color = get_status_color(today_carbs, **THRESHOLDS["Carbs"])
fat_color = get_status_color(today_fats, **THRESHOLDS["Fats"])
prot_color = get_status_color(today_protein, **THRESHOLDS["Protein"])

cal_target = THRESHOLDS["Calories"]["high"]
carb_target = THRESHOLDS["Carbs"]["high"]
fat_target = THRESHOLDS["Fats"]["high"]
prot_target = THRESHOLDS["Protein"]["low"]

def render_bloom_card(icon, label, value, unit, target, color, delay=0.0):
    try: pct = max(0, min((value / target) * 100, 100)) if target else 0
    except Exception: pct = 0
    st.markdown(f"""
        <div class="bloom-card" style="animation-delay:{delay}s;">
            <div class="bloom-ring" style="background: conic-gradient({color} {pct:.1f}%, rgba(0,0,0,0.07) 0);">
                <div class="bloom-inner"><span class="bloom-icon">{icon}</span></div>
            </div>
            <div class="bloom-label">{label}</div>
            <div class="bloom-value">{value:.0f}<span class="bloom-unit">{unit}</span></div>
            <div class="bloom-target">of {target:.0f}{unit} goal</div>
        </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    render_bloom_card("🔥", "Calories", today_cal, " kcal", cal_target, cal_color, delay=0.00)
    render_bloom_card("🍞", "Carbs", today_carbs, "g", carb_target, carb_color, delay=0.10)
with col2:
    render_bloom_card("💪", "Protein", today_protein, "g", prot_target, prot_color, delay=0.05)
    render_bloom_card("🥑", "Fats", today_fats, "g", fat_target, fat_color, delay=0.15)

st.markdown('<div class="bloom-divider"><span>🌿</span></div>', unsafe_allow_html=True)

# ==========================================
# 7. INTERACTIVE STREAMS & HORIZONTAL CONTROLS
# ==========================================
st.markdown('<div class="section-eyebrow">🩷 Cycle Companion</div>', unsafe_allow_html=True)

if cycle_banner:
    tone, text = cycle_banner
    if tone == "upcoming": st.markdown(f'<div class="milestone-line">🗓️ {text}</div>', unsafe_allow_html=True)
    else: st.markdown(f'<div class="cycle-outlook outlook-{tone}">{text}</div>', unsafe_allow_html=True)

# --- DYNAMIC X DAYS COUNTDOWN CALCULATOR ---
days_display_text = ""
if all_starts:
    last_start = all_starts[-1]
    if is_period_active:
        expected_end = last_start + timedelta(days=5)
        if today_date <= expected_end:
            days_left = (expected_end - today_date).days
            days_display_text = f"~{days_left} day{'s' if days_left != 1 else ''} left"
        else:
            days_over = (today_date - expected_end).days
            days_display_text = f"Day {5 + days_over}"
    else:
        predicted_next = last_start + timedelta(days=avg_cycle_len)
        if today_date < predicted_next:
            days_until = (predicted_next - today_date).days
            days_display_text = f"{days_until} day{'s' if days_until != 1 else ''} away"
        elif today_date == predicted_next:
            days_display_text = "Due today 🌷"
        else:
            days_late = (today_date - predicted_next).days
            days_display_text = f"{days_late} day{'s' if days_late != 1 else ''} late"

current_date_obj = now.date()

if is_period_active:
    st.markdown(f"""
        <div class="cycle-card cycle-active">
            <div class="cycle-left-layout">
                <div class="cycle-icon">🌷</div>
                <div>
                    <div class="cycle-title">Cycle is active</div>
                    <div class="cycle-sub">Take it slow today, love — warm tea, rest, zero pressure.</div>
                </div>
            </div>
            {"<div class='cycle-countdown-pill'>" + days_display_text + "</div>" if days_display_text else ""}
        </div>
    """, unsafe_allow_html=True)
    
    active_btn_label = "🌸 Ended today" if last_start_date == current_date_obj else "🌸 Mark as ended"
    
    if st.button(active_btn_label, key="end_cycle_btn"):
        ok, err = airtable_patch("Cycles", active_row_id, {"End Date": today_str})
        if ok: st.cache_data.clear(); st.rerun()
        else: st.error(f"Error updating cycle: {err}")
else:
    st.markdown(f"""
        <div class="cycle-card cycle-idle">
            <div class="cycle-left-layout">
                <div class="cycle-icon">🌿</div>
                <div>
                    <div class="cycle-title">No active cycle</div>
                    <div class="cycle-sub">Log it here when it starts — I'll take it from there.</div>
                </div>
            </div>
            {"<div class='cycle-countdown-pill'>" + days_display_text + "</div>" if days_display_text else ""}
        </div>
    """, unsafe_allow_html=True)
    
    idle_btn_label = "🩸 Started today" if last_end_date == current_date_obj else "🩸 Period started today"
    
    if st.button(idle_btn_label, key="start_cycle_btn"):
        ok, err = airtable_post("Cycles", {"Start Date": today_str, "Notes": "Logged via Companion App Dashboard"})
        if ok: st.cache_data.clear(); st.rerun()
        else: st.error(f"Error saving cycle start: {err}")

# Backdate Cycle Fallback Manual Overrides
with st.expander("🗓️ Retroactively log cycle dates"):
    with st.form("manual_cycle_form"):
        c_start = st.date_input("Cycle Start Date", value=now.date())
        c_end = st.date_input("Cycle End Date (Leave blank if ongoing)", value=None)
        c_notes = st.text_input("Notes", placeholder="e.g., Heavy cramps, PCOD symptoms light")
        submit_c = st.form_submit_button("Save Cycle Log", key="cta_cycle_manual")
        if submit_c:
            payload = {"Start Date": c_start.strftime("%Y-%m-%d"), "Notes": c_notes}
            if c_end: payload["End Date"] = c_end.strftime("%Y-%m-%d")
            
            ok, err = airtable_post("Cycles", payload)
            if ok:
                st.success("Cycle history updated!")
                st.cache_data.clear(); st.rerun()
            else: st.error(f"Error saving log: {err}")

st.markdown('<div class="bloom-divider"><span>🌸</span></div>', unsafe_allow_html=True)

# Meals and Weight Logging Accordions
repeated_foods = [food for food, count in Counter(food_history_pool).items() if count >= 3]

with st.expander("📝 Log food entries", expanded=False):
    log_date_target = st.date_input("Logging for which day?", value=now.date(), key="diet_log_date")

    if repeated_foods:
        st.caption("⚡ Quick Log Favorites:")
        cols = st.columns(min(len(repeated_foods), 3))
        for idx, food in enumerate(repeated_foods[:6]):
            if cols[idx % 3].button(f"➕ {food[:18]}", key=f"btn_{idx}"):
                st.session_state["her_meal_input"] = food.strip().title()
                st.rerun()

    default_text = st.session_state.get("her_meal_input", "")
    meal_input = st.text_area("What did you eat?", value=default_text, placeholder="e.g., 1 Banana, 2 Roti, 2 Eggs")
    submit_meal = st.button("Log Daily Meal Block", key="cta_meal")

    if submit_meal and meal_input:
        with st.spinner("AI calculating customized macros..."):
            try:
                clean_meal_text = meal_input.strip().title()
                res = client.models.generate_content(
                    model='gemini-2.5-flash', contents=f"Analyze macros for this description: {clean_meal_text}",
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=MacroData, temperature=0.1),
                )
                macros = json.loads(res.text)

                current_time = now.strftime("%Y-%m-%d %I:%M %p") if log_date_target.strftime("%Y-%m-%d") == today_str else f"{log_date_target.strftime('%Y-%m-%d')} 10:00 PM"
                data = {
                    "Timestamp": current_time, "Food Items": clean_meal_text,
                    "Calories": float(macros["calories"]), "Protein": float(macros["protein"]),
                    "Carbs": float(macros["carbs"]), "Fats": float(macros["fats"])
                }
                ok, err = airtable_post("Diet", data)
                if "her_meal_input" in st.session_state: del st.session_state["her_meal_input"]
                if ok: st.success("Macros tracked successfully!"); st.cache_data.clear(); st.rerun()
                else: st.error(f"Error saving to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

with st.expander("⚖️ Log weight metric", expanded=False):
    with st.form("weight_form", clear_on_submit=True):
        weight_date_target = st.date_input("Logging for which day?", value=now.date(), key="w_date_track")
        weight_input = st.number_input("Weight (kg)", min_value=10.0, max_value=250.0, step=0.05, format="%.2f")
        submit_weight = st.form_submit_button("Log Weight", key="cta_weight")

        if submit_weight and weight_input > 10.0:
            try:
                current_time = now.strftime("%Y-%m-%d %I:%M %p") if weight_date_target.strftime("%Y-%m-%d") == today_str else f"{weight_date_target.strftime('%Y-%m-%d')} 10:00 PM"
                ok, err = airtable_post("Weight", {"Timestamp": current_time, "Weight": float(weight_input)})
                if ok: st.success("Weight recorded!"); st.cache_data.clear(); st.rerun()
                else: st.error(f"Error saving to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

with st.expander("✨ Log a milestone / moment", expanded=False):
    with st.form("moments_form", clear_on_submit=True):
        moment_date = st.date_input("When did this happen?", value=now.date())
        moment_text = st.text_input("What did you achieve?", placeholder="e.g., Left Sugar, Finished Exam Block")
        show_on_top_check = st.checkbox("Pin to top highlight banner?", value=True)
        if st.form_submit_button("Save Moment", key="cta_moment"):
            try:
                clean_moment = moment_text.strip().title()
                ok, err = airtable_post("Moments", {"Date": moment_date.strftime("%Y-%m-%d"), "Moment": clean_moment, "Show On Top": show_on_top_check})
                if ok: st.success("Milestone saved!"); st.cache_data.clear(); st.rerun()
                else: st.error(f"Error saving to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

st.markdown('<div class="bloom-divider"><span>🌼</span></div>', unsafe_allow_html=True)

# ==========================================
# 8. ANALYTICS VISUALIZATIONS & TREND CURVES
# ==========================================
st.markdown('<div class="section-eyebrow">📈 Trends & Milestones</div>', unsafe_allow_html=True)
CHART_FONT = "Quicksand"

# Milestone Mapping Calendar - Customized with fresh grass-green background fill and sunflower elements
milestone_dates = {r.get("fields", {}).get("Date"): r.get("fields", {}).get("Moment") for r in moments_records if r.get("fields", {}).get("Date")}
if milestone_dates:
    st.caption("🌻 Milestone calendar")
    df_milestones = pd.DataFrame(list(milestone_dates.items()), columns=["Date", "Milestone"])
    df_milestones["Marker"] = "🌻"

    cal_dots = alt.Chart(df_milestones).mark_text(size=22, baseline='middle').encode(
        x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', grid=True)), text='Marker:N', tooltip='Milestone:N'
    ).properties(height=80).configure_axis(labelFont=CHART_FONT, labelColor="#8a8694", gridColor="#00000010").configure_view(strokeOpacity=0, fill='rgba(143, 227, 196, 0.25)')
    st.altair_chart(cal_dots, use_container_width=True)

# Calorie Intake Curves
chart_diet_data = {}
for record in reversed(diet_records):
    fields = record.get("fields", {})
    ts = fields.get("Timestamp", "")
    if ts: chart_diet_data[ts.split(" ")[0]] = chart_diet_data.get(ts.split(" ")[0], 0.0) + float(fields.get("Calories", 0))

if chart_diet_data:
    st.caption("🔥 Calorie consumption curve")
    df_cal = pd.DataFrame(list(chart_diet_data.items()), columns=["Date", "Calories"]).sort_values("Date")
    cal_line_color = "#ef6f93" if today_cal > THRESHOLDS["Calories"]["high"] else "#1fa97a"

    cal_chart = alt.Chart(df_cal).mark_area(
        line={'color': cal_line_color, 'width': 2.5}, interpolate='monotone',
        color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color=cal_line_color, offset=0), alt.GradientStop(color='rgba(0,0,0,0)', offset=1)], x1=1, y1=1, x2=1, y2=0)
    ).encode(x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)), y=alt.Y('Calories:Q', title=None, scale=alt.Scale(zero=False))).properties(height=160).configure_axis(labelFont=CHART_FONT, labelColor="#8a8694").configure_view(strokeOpacity=0)
    st.altair_chart(cal_chart, use_container_width=True)

# Weight Line Curves
chart_weight_data = {r.get("fields", {}).get("Timestamp", "").split(" ")[0]: float(r.get("fields", {}).get("Weight", 0)) for r in reversed(weight_records) if r.get("fields", {}).get("Timestamp", "")}
if chart_weight_data:
    st.caption("⚖️ Weight tracking trend (kg)")
    df_weight = pd.DataFrame(list(chart_weight_data.items()), columns=["Date", "Weight"]).sort_values("Date")
    trend_color = "#1fa97a" if len(df_weight) < 2 or df_weight["Weight"].iloc[-1] <= df_weight["Weight"].iloc[-2] else "#ef6f93"
    weight_chart = alt.Chart(df_weight).mark_line(
        color=trend_color, point=alt.OverlayMarkDef(color=trend_color, size=40, filled=True), strokeWidth=3, interpolate='monotone'
    ).encode(x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)), y=alt.Y('Weight:Q', title=None, scale=alt.Scale(zero=False))).properties(height=160).configure_axis(labelFont=CHART_FONT, labelColor="#8a8694").configure_view(strokeOpacity=0)
    st.altair_chart(weight_chart, use_container_width=True)
