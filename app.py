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
st.set_page_config(page_title="Pocket Health Tracker", page_icon="🌷", layout="centered")

# Design tokens: emerald + rose, warm serif for the "love note" voice,
# rounded sans for everything functional. Two soft blurred blobs give the
# background depth instead of a flat gradient. Animation is one-shot
# (fade/bloom on load) rather than looping, so it reads considered, not busy.
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
    }

    html, body, [class*="css"], .stMarkdown {
        font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: linear-gradient(160deg, #e1f8ee 0%, #fdeef4 42%, #fff3e6 75%, #ffe7ef 100%);
        background-attachment: fixed;
    }
    .stApp::before, .stApp::after {
        content: "";
        position: fixed;
        border-radius: 50%;
        filter: blur(75px);
        opacity: 0.42;
        z-index: 0;
        pointer-events: none;
    }
    .stApp::before { width: 380px; height: 380px; background: radial-gradient(circle, var(--emerald-soft), transparent 70%); top: -130px; left: -110px; animation: drift 15s ease-in-out infinite; }
    .stApp::after { width: 440px; height: 440px; background: radial-gradient(circle, var(--rose-soft), transparent 70%); bottom: -150px; right: -130px; animation: drift 18s ease-in-out infinite reverse; }

    @keyframes drift {
        0%, 100% { transform: translate(0,0) scale(1); }
        50% { transform: translate(20px, -16px) scale(1.08); }
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

    /* ---- Cycle companion card ---- */
    .cycle-card {
        display: flex; align-items: center; gap: 14px;
        border-radius: 20px;
        padding: 16px 18px;
        margin-bottom: 10px;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        animation: floatIn 0.6s ease both;
    }
    .cycle-active { background: linear-gradient(135deg, rgba(255,182,200,0.5), rgba(255,255,255,0.5)); box-shadow: 0 8px 20px rgba(239,111,147,0.16); }
    .cycle-idle { background: linear-gradient(135deg, rgba(143,227,196,0.4), rgba(255,255,255,0.5)); box-shadow: 0 8px 20px rgba(31,169,122,0.11); }
    .cycle-icon { font-size: 27px; }
    .cycle-title { font-weight: 700; font-size: 14.5px; color: var(--ink); }
    .cycle-sub { font-size: 12.5px; color: var(--ink-soft); margin-top: 1px; }

    /* Cycle outlook banner — predicted-vs-actual regularity message */
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

    /* ---- Buttons: auto-width pills by default ---- */
    .stButton>button, .stFormSubmitButton>button {
        border-radius: 999px;
        font-weight: 700;
        font-family: 'Quicksand', sans-serif;
        border: none;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { transform: translateY(-1px); }
    .stButton>button:active, .stFormSubmitButton>button:active { transform: translateY(0px); }

    /* Period toggle — small pill, NOT full width */
    div[class*="st-key-start_cycle_btn"] button {
        background: linear-gradient(135deg, var(--rose) 0%, var(--rose-deep) 100%) !important;
        color: white !important;
        padding: 0 24px; height: 2.5em;
        box-shadow: 0 6px 16px rgba(239,111,147,0.32);
        position: relative; overflow: hidden;
    }
    div[class*="st-key-end_cycle_btn"] button {
        background: linear-gradient(135deg, var(--emerald) 0%, var(--emerald-deep) 100%) !important;
        color: white !important;
        padding: 0 24px; height: 2.5em;
        box-shadow: 0 6px 16px rgba(31,169,122,0.28);
        position: relative; overflow: hidden;
    }

    /* Primary CTAs (form submits) — full width gradient */
    div[class*="st-key-cta_"] button {
        width: 100%;
        height: 2.9em;
        background: linear-gradient(135deg, var(--emerald) 0%, var(--rose) 100%) !important;
        color: white !important;
        box-shadow: 0 8px 18px rgba(239,111,147,0.24);
        position: relative; overflow: hidden;
    }

    /* Shine sweep on hover for the gradient pill/CTA buttons */
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

    /* Quick-log favorite chips — small + light */
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

    /* Expanders */
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

# India is a single timezone (UTC+5:30, no DST), so a fixed offset is exact —
# this is the fix for the "good morning at 1pm" bug, which happened because
# datetime.now() was reading the server's UTC clock instead of her local time.
IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str = now.strftime("%Y-%m-%d")

# ==========================================
# AIRTABLE WRITE HELPERS
# ==========================================
# Centralized POST/PATCH with typecast=True (lets Airtable accept a value like
# "Started"/"Ended" on a Single Select field even if that exact option hasn't
# been created yet — the most common reason a record silently fails to save)
# and actual response checking, since requests.post() never raises on its own
# for a 4xx/5xx response. This is what was causing the cycle log to fail with
# zero feedback: the POST was firing, Airtable was rejecting it, and the code
# never looked at the response to notice.
def airtable_post(table, fields):
    try:
        resp = requests.post(
            f"https://api.airtable.com/v0/{BASE_ID}/{table}",
            headers=headers,
            json={"records": [{"fields": fields}], "typecast": True}
        )
        if resp.ok:
            return True, None
        try:
            err = resp.json().get("error", {})
            msg = err.get("message") if isinstance(err, dict) else str(err)
        except Exception:
            msg = resp.text
        return False, msg or f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

def airtable_patch(table, record_id, fields):
    try:
        resp = requests.patch(
            f"https://api.airtable.com/v0/{BASE_ID}/{table}",
            headers=headers,
            json={"records": [{"id": record_id, "fields": fields}], "typecast": True}
        )
        if resp.ok:
            return True, None
        try:
            err = resp.json().get("error", {})
            msg = err.get("message") if isinstance(err, dict) else str(err)
        except Exception:
            msg = resp.text
        return False, msg or f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. DATA ACQUISITION PIPELINE
# ==========================================
@st.cache_data(ttl=5)
def fetch_airtable_all(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}?maxRecords=100"
        if table_name in ["Diet", "Weight"]:
            url += "&sort[0][field]=Timestamp&sort[0][direction]=desc"
        elif table_name == "Cycles":
            url += "&sort[0][field]=Date&sort[0][direction]=desc"
        res = requests.get(url, headers=headers).json()
        return res.get("records", [])
    except Exception:
        return []

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

# Determine Period Active Status
is_period_active = False
if cycle_records:
    latest_event = cycle_records[0].get("fields", {}).get("EventType", "")
    if latest_event == "Started":
        is_period_active = True

# ==========================================
# 3. ONBOARDING & AUTOMATIC MACRO MACHINE
# ==========================================
# Show setup wizard if Profile values are missing
is_onboarded = bool(profile_map.get("Calories"))

if not is_onboarded:
    st.markdown('<div class="note-card"><p class="note-text">🌸 Welcome to your pocket companion 🧸<br>Let\'s set up her custom health parameters baseline right now.</p></div>', unsafe_allow_html=True)
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
                # Harris-Benedict BMR Calculation for Female Baseline
                bmr = 447.593 + (9.247 * w_in) + (3.098 * h_in) - (4.330 * 23) # Assuming general early 20s age step
                multiplier = 1.2
                if "Lightly" in act_in: multiplier = 1.375
                elif "Moderately" in act_in: multiplier = 1.55
                elif "Very" in act_in: multiplier = 1.725

                tdee = bmr * multiplier
                # Set a healthy, elegant sustainable fitness deficit
                target_cal = round(tdee - 350)
                target_carbs = round((target_cal * 0.40) / 4)
                target_protein = round((target_cal * 0.30) / 4)
                target_fats = round((target_cal * 0.30) / 9)

                updates = {
                    "Height": str(h_in), "Weight": str(w_in), "ActivityLevel": act_in,
                    "Calories": str(target_cal), "Carbs": str(target_carbs),
                    "Protein": str(target_protein), "Fats": str(target_fats)
                }

                # Push values seamlessly back to Airtable Profile Table rows
                failures = []
                for field_key, field_val in updates.items():
                    r_id = profile_row_ids.get(field_key)
                    if r_id:
                        ok, err = airtable_patch("Profile", r_id, {"Value": field_val})
                        if not ok:
                            failures.append(f"{field_key}: {err}")
                if failures:
                    st.error("Some values didn't save: " + " | ".join(failures))
                else:
                    st.success("Your customized dashboard has been calculated and initialized! Loading...")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Setup Error: {e}")
    st.stop()

# Load targets dynamically from Airtable Profile
THRESHOLDS = {
    "Calories": {"low": float(profile_map.get("Calories", 1400)) - 50, "high": float(profile_map.get("Calories", 1400)), "reverse": False},
    "Carbs": {"low": float(profile_map.get("Carbs", 130)) - 10, "high": float(profile_map.get("Carbs", 130)), "reverse": False},
    "Fats": {"low": float(profile_map.get("Fats", 40)) - 5, "high": float(profile_map.get("Fats", 40)), "reverse": False},
    "Protein": {"low": float(profile_map.get("Protein", 80)), "high": float(profile_map.get("Protein", 80)) + 15, "reverse": True}
}

# ==========================================
# 4. GREETING MACHINE & SUPPORT COMPLIMENTS
# ==========================================
st.markdown('<div class="app-title">🌷 Aduu\'s Garden 🧸</div>', unsafe_allow_html=True)
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

# Interactive Index Mapping for Compliment Rotations
day_of_year = now.timetuple().tm_yday
current_hour = now.hour

# 20 Specialized Compliments & Supportive Sentences
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

# Pick Base greeting based on timing
if 6 <= current_hour < 12:
    selected_greeting = phrases_morning[day_of_year % 4]
elif 12 <= current_hour < 17:
    selected_greeting = phrases_afternoon[day_of_year % 4]
elif 17 <= current_hour < 22:
    selected_greeting = phrases_evening[day_of_year % 4]
else:
    selected_greeting = phrases_global[day_of_year % 8]

# Period Overlay Overrides Greeting entirely with Medical Care messages
if is_period_active:
    period_phrases = [
        "I know today might feel physically heavy, beautiful. Please make sure to drink some warm water and rest up. Remember I'm always just one call away if you need anything.",
        "Take it slow today, darling. You're doing amazing, and your health comes first. Warm tea and cozy blankets only.",
        "Sending you the biggest comforting vibes. Rest your mind and body today, you look beautiful as always.",
        "Listen to your body today, princess. Don't stress about targets; comfort, warm water, and self-care are your only goals right now."
    ]
    selected_greeting = period_phrases[day_of_year % 4]

# Display Dynamic Header Note Card
st.markdown(f'<div class="note-card"><p class="note-text">{selected_greeting}</p></div>', unsafe_allow_html=True)

if streak > 0:
    st.markdown(f'<div class="streak-pill"><span class="flame">🔥</span> {streak} Day Consistency Streak — you are doing incredible</div>', unsafe_allow_html=True)

# Pinned Moments calculations
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

# ==========================================
# 5. DYNAMIC COLOR METRIC DASHBOARD ("Bloom" rings)
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

def get_status_color(val, low, high, reverse=False):
    if reverse:
        if val < low: return "#ef6f93"      # Rose (Under target for protein)
        if val <= high: return "#f4b942"    # Gold
        return "#1fa97a"                    # Emerald
    else:
        if val < low: return "#1fa97a"      # Emerald (Below ceiling limits)
        if val <= high: return "#f4b942"    # Gold Warning
        return "#ef6f93"                    # Rose crossed

cal_color = get_status_color(today_cal, **THRESHOLDS["Calories"])
carb_color = get_status_color(today_carbs, **THRESHOLDS["Carbs"])
fat_color = get_status_color(today_fats, **THRESHOLDS["Fats"])
prot_color = get_status_color(today_protein, **THRESHOLDS["Protein"])

cal_target = THRESHOLDS["Calories"]["high"]
carb_target = THRESHOLDS["Carbs"]["high"]
fat_target = THRESHOLDS["Fats"]["high"]
prot_target = THRESHOLDS["Protein"]["low"]

def render_bloom_card(icon, label, value, unit, target, color, delay=0.0):
    try:
        pct = max(0, min((value / target) * 100, 100)) if target else 0
    except Exception:
        pct = 0
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
# 6. MANAGEMENT & ENTRY INPUT MODULES
# ==========================================

# ---- Cycle regularity engine ----
# Reads her Started/Ended history to predict the next start date, then
# compares reality against that prediction so the banner can say "right on
# time", "X days late and still waiting", or "that one ran X days long".
def parse_cycle_events(records):
    events = []
    for r in records:
        f = r.get("fields", {})
        d, e = f.get("Date"), f.get("EventType")
        if d and e:
            try:
                events.append((datetime.strptime(d, "%Y-%m-%d").date(), e))
            except Exception:
                continue
    events.sort(key=lambda x: x[0])
    return events

cycle_events = parse_cycle_events(cycle_records)
start_dates = [d for d, e in cycle_events if e == "Started"]

DEFAULT_CYCLE_LEN = 28
avg_cycle_len = DEFAULT_CYCLE_LEN
if len(start_dates) >= 2:
    gaps = [(start_dates[i] - start_dates[i - 1]).days for i in range(1, len(start_dates))]
    recent_gaps = [g for g in gaps[-6:] if 10 <= g <= 60]
    if recent_gaps:
        avg_cycle_len = round(sum(recent_gaps) / len(recent_gaps))

today_date = now.date()
cycle_banner = None  # (tone, text)

if start_dates:
    last_start = start_dates[-1]
    if is_period_active:
        if len(start_dates) >= 2:
            predicted_for_this = start_dates[-2] + timedelta(days=avg_cycle_len)
            diff = (last_start - predicted_for_this).days
            if diff <= 1:
                cycle_banner = ("good", "Perfect cycle — started right on time 💚")
            elif diff <= 4:
                cycle_banner = ("warn", f"Started {diff} days later than usual — hope you're doing okay 🩷")
            else:
                cycle_banner = ("warn", f"Sorry love, this one took {diff} days longer than usual to start 🩷")
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

# Period Companion — redesigned as a soft status card with a small pill
# action button beside it (not a full-width CTA), so it sits in line with
# the rest of the UI instead of shouting over it.
st.markdown('<div class="section-eyebrow">🩷 Cycle Companion</div>', unsafe_allow_html=True)

if cycle_banner:
    tone, text = cycle_banner
    if tone == "upcoming":
        st.markdown(f'<div class="milestone-line">🗓️ {text}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="cycle-outlook outlook-{tone}">{text}</div>', unsafe_allow_html=True)

if is_period_active:
    st.markdown("""
        <div class="cycle-card cycle-active">
            <div class="cycle-icon">🌷</div>
            <div>
                <div class="cycle-title">Cycle is active</div>
                <div class="cycle-sub">Take it slow today, love — warm tea, rest, zero pressure.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🌸 Mark as ended", key="end_cycle_btn"):
        ok, err = airtable_post("Cycles", {"Date": today_str, "EventType": "Ended"})
        if ok:
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Couldn't save that to Airtable: {err}")
else:
    st.markdown("""
        <div class="cycle-card cycle-idle">
            <div class="cycle-icon">🌿</div>
            <div>
                <div class="cycle-title">No active cycle</div>
                <div class="cycle-sub">Tap below whenever it starts — I'll take it from there.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🩸 Period started today", key="start_cycle_btn"):
        ok, err = airtable_post("Cycles", {"Date": today_str, "EventType": "Started"})
        if ok:
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Couldn't save that to Airtable: {err}")

# Backdate Cycle Fallback Manual Overrides
with st.expander("🗓️ Retroactively log cycle dates"):
    with st.form("manual_cycle_form"):
        c_date = st.date_input("Event Date", value=now.date())
        c_type = st.selectbox("Action State", ["Started", "Ended"])
        submit_c = st.form_submit_button("Save Cycle Log", key="cta_cycle_manual")
        if submit_c:
            ok, err = airtable_post("Cycles", {"Date": c_date.strftime("%Y-%m-%d"), "EventType": c_type})
            if ok:
                st.success("Cycle history updated!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Couldn't save that to Airtable: {err}")

st.markdown('<div class="bloom-divider"><span>🌸</span></div>', unsafe_allow_html=True)

# Meals and Weight Logging Standard Accordions
repeated_foods = [food for food, count in Counter(food_history_pool).items() if count >= 3]

with st.expander("📝 Log food entries", expanded=False):
    log_date_target = st.date_input("Logging for which day?", value=now.date(), key="diet_log_date")

    if repeated_foods:
        st.caption("⚡ Quick Log Favorites:")
        cols = st.columns(min(len(repeated_foods), 3))
        for idx, food in enumerate(repeated_foods[:6]):
            col_target = cols[idx % 3]
            if col_target.button(f"➕ {food[:18]}", key=f"btn_{idx}"):
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
                    model='gemini-2.5-flash',
                    contents=f"Analyze macros for this description: {clean_meal_text}",
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=MacroData, temperature=0.1),
                )
                macros = json.loads(res.text)

                if log_date_target.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
                    current_time = now.strftime("%Y-%m-%d %I:%M %p")
                else:
                    current_time = f"{log_date_target.strftime('%Y-%m-%d')} 10:00 PM"

                data = {
                    "Timestamp": current_time, "Food Items": clean_meal_text,
                    "Calories": float(macros["calories"]), "Protein": float(macros["protein"]),
                    "Carbs": float(macros["carbs"]), "Fats": float(macros["fats"])
                }
                ok, err = airtable_post("Diet", data)
                if "her_meal_input" in st.session_state: del st.session_state["her_meal_input"]
                if ok:
                    st.success("Macros tracked successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Couldn't save that to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

with st.expander("⚖️ Log weight metric", expanded=False):
    with st.form("weight_form", clear_on_submit=True):
        weight_date_target = st.date_input("Logging for which day?", value=now.date(), key="w_date_track")
        weight_input = st.number_input("Weight (kg)", min_value=10.0, max_value=250.0, step=0.05, format="%.2f")
        submit_weight = st.form_submit_button("Log Weight", key="cta_weight")

        if submit_weight and weight_input > 10.0:
            try:
                if weight_date_target.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
                    current_time = now.strftime("%Y-%m-%d %I:%M %p")
                else:
                    current_time = f"{weight_date_target.strftime('%Y-%m-%d')} 10:00 PM"
                data = {"Timestamp": current_time, "Weight": float(weight_input)}
                ok, err = airtable_post("Weight", data)
                if ok:
                    st.success("Weight recorded!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Couldn't save that to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

with st.expander("✨ Log a milestone / moment", expanded=False):
    with st.form("moments_form", clear_on_submit=True):
        moment_date = st.date_input("When did this happen?", value=now.date())
        moment_text = st.text_input("What did you achieve?", placeholder="e.g., Left Sugar, Finished Exam Block")
        show_on_top_check = st.checkbox("Pin to top highlight banner?", value=True)
        submit_moment = st.form_submit_button("Save Moment", key="cta_moment")
        if submit_moment and moment_text:
            try:
                clean_moment = moment_text.strip().title()
                data = {
                    "Date": moment_date.strftime("%Y-%m-%d"), "Moment": clean_moment, "Show On Top": show_on_top_check
                }
                ok, err = airtable_post("Moments", data)
                if ok:
                    st.success("Milestone saved!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Couldn't save that to Airtable: {err}")
            except Exception as e: st.error(f"Error: {e}")

st.markdown('<div class="bloom-divider"><span>🌼</span></div>', unsafe_allow_html=True)

# ==========================================
# 7. ANALYTICS VISUALIZATIONS & CALENDAR MARKERS
# ==========================================
st.markdown('<div class="section-eyebrow">📈 Trends & Milestones</div>', unsafe_allow_html=True)

CHART_FONT = "Quicksand"

# Build data dictionary for active calendar visualization cells
milestone_dates = {}
for r in moments_records:
    dt = r.get("fields", {}).get("Date", "")
    txt = r.get("fields", {}).get("Moment", "")
    if dt: milestone_dates[dt] = txt

# Create a clean calendar layout mapping milestones to a floral element marker
if milestone_dates:
    st.caption("🌸 Milestone calendar")
    df_milestones = pd.DataFrame(list(milestone_dates.items()), columns=["Date", "Milestone"])
    df_milestones["Marker"] = "🌸"

    cal_dots = alt.Chart(df_milestones).mark_text(size=22, baseline='middle').encode(
        x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', grid=True)),
        text='Marker:N',
        tooltip='Milestone:N'
    ).properties(height=80).configure_axis(
        labelFont=CHART_FONT, labelColor="#8a8694", gridColor="#00000010"
    ).configure_view(strokeOpacity=0)
    st.altair_chart(cal_dots, use_container_width=True)

# Render Calorie Line Area Graph
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
    ).encode(
        x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)),
        y=alt.Y('Calories:Q', title=None, scale=alt.Scale(zero=False))
    ).properties(height=160).configure_axis(
        labelFont=CHART_FONT, labelColor="#8a8694"
    ).configure_view(strokeOpacity=0)
    st.altair_chart(cal_chart, use_container_width=True)

# Render Weight Line Graph
chart_weight_data = {}
for record in reversed(weight_records):
    fields = record.get("fields", {})
    ts = fields.get("Timestamp", "")
    if ts: chart_weight_data[ts.split(" ")[0]] = float(fields.get("Weight", 0))

if chart_weight_data:
    st.caption("⚖️ Weight tracking trend (kg)")
    df_weight = pd.DataFrame(list(chart_weight_data.items()), columns=["Date", "Weight"]).sort_values("Date")
    trend_color = "#1fa97a" if len(df_weight) < 2 or df_weight["Weight"].iloc[-1] <= df_weight["Weight"].iloc[-2] else "#ef6f93"
    weight_chart = alt.Chart(df_weight).mark_line(
        color=trend_color, point=alt.OverlayMarkDef(color=trend_color, size=40, filled=True), strokeWidth=3, interpolate='monotone'
    ).encode(
        x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)),
        y=alt.Y('Weight:Q', title=None, scale=alt.Scale(zero=False))
    ).properties(height=160).configure_axis(
        labelFont=CHART_FONT, labelColor="#8a8694"
    ).configure_view(strokeOpacity=0)
    st.altair_chart(weight_chart, use_container_width=True)
