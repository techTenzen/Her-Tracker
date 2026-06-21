import streamlit as st
import requests
from datetime import datetime, timedelta
import json
from collections import Counter
import altair as alt
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# 1. PAGE SETUP & GLASSMORPHISM STYLING
# ==========================================
st.set_page_config(page_title="Pocket Health Tracker", page_icon="🧸", layout="centered")

# Custom UI CSS for Emerald Green + Rose Pink Glassmorphism Look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Elegant Background Gradient for the page wrapper */
    .stApp {
        background: linear-gradient(135deg, #e8f5e9 0%, #fce4ec 100%);
    }
    
    /* Intro / Accent Box Styling */
    .intro-box {
        background: rgba(255, 255, 255, 0.45);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.6);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(244, 143, 177, 0.15);
    }
    
    /* Premium Glassmorphism Metric Cards */
    .glass-metric {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 18px;
        margin: 8px 0px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease;
    }
    .glass-metric:hover { transform: translateY(-2px); }
    .metric-title { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #2c3e50; }
    
    /* Buttons Custom Design (Emerald Green and Rose Pink styles) */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        height: 3em;
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
        color: white !important;
        border: none;
        box-shadow: 0 4px 10px rgba(46, 204, 113, 0.2);
    }
    
    /* Special Period Button Styles */
    .period-start-btn>button {
        background: linear-gradient(135deg, #ff7675 0%, #d63031 100%) !important;
        box-shadow: 0 4px 10px rgba(214, 48, 49, 0.2);
    }
    .period-end-btn>button {
        background: linear-gradient(135deg, #a29bfe 0%, #6c5ce7 100%) !important;
        box-shadow: 0 4px 10px rgba(108, 92, 231, 0.2);
    }
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
today_str = datetime.now().strftime("%Y-%m-%d")

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
    st.markdown('<div class="intro-box"><h3>🌸 Welcome to Your Companion Tracker 🧸</h3><p>Let\'s set up your custom health parameters baseline right now.</p></div>', unsafe_allow_html=True)
    with st.form("onboarding_form"):
        h_in = st.number_input("Height (cm)", min_value=100, max_value=250, value=160)
        w_in = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=55.0, step=0.1)
        act_in = st.selectbox("Exercise Frequency / Activity Level", [
            "Sedentary (Little or no exercise)",
            "Lightly Active (Light exercise 1-3 days/week)",
            "Moderately Active (Moderate exercise 3-5 days/week)",
            "Very Active (Hard exercise 6-7 days/week)"
        ])
        submit_setup = st.form_submit_button("Generate My Custom Dashboard")
        
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
                for field_key, field_val in updates.items():
                    r_id = profile_row_ids.get(field_key)
                    if r_id:
                        requests.patch(f"https://api.airtable.com/v0/{BASE_ID}/Profile", headers=headers, json={
                            "records": [{"id": r_id, "fields": {"Value": field_val}}]
                        })
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
st.title("🌸 Pocket Health Companion 🧸")

# Calculate Streak
logged_dates = set()
for r in diet_records:
    ts = r.get("fields", {}).get("Timestamp", "")
    if ts: logged_dates.add(ts.split(" ")[0])
for r in weight_records:
    ts = r.get("fields", {}).get("Timestamp", "")
    if ts: logged_dates.add(ts.split(" ")[0])

streak = 0
check_date = datetime.now()
while check_date.strftime("%Y-%m-%d") in logged_dates:
    streak += 1
    check_date -= timedelta(days=1)

# Interactive Index Mapping for Compliment Rotations
day_of_year = datetime.now().timetuple().tm_yday
current_hour = datetime.now().hour

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

# Display Dynamic Header Glass Card
st.markdown(f"""
    <div class="intro-box">
        <p style="font-size: 16px; font-weight: 600; color: #2c3e50; line-height: 1.5; margin: 0;">
            {selected_greeting}
        </p>
    </div>
""", unsafe_allow_html=True)

if streak > 0:
    st.markdown(f"🔥 **{streak} Day Consistency Streak!** You are doing incredible.")

# Pinned Moments calculations
for record in moments_records:
    fields = record.get("fields", {})
    if fields.get("Show On Top") is True:
        m_date_str = fields.get("Date", "")
        m_text = fields.get("Moment", "")
        if m_date_str and m_text:
            try:
                days_since = (datetime.now() - datetime.strptime(m_date_str, "%Y-%m-%d")).days
                st.markdown(f"✨ **{m_text}:** {days_since} days running! Phenomenal work.")
            except Exception: continue

# ==========================================
# 5. DYNAMIC COLOR METRIC DASHBOARD
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
        if val < low: return "#ff4b4b"     # Red (Under target for protein)
        if val <= high: return "#ffdd57"    # Yellow
        return "#2ecc71"                   # Green
    else:
        if val < low: return "#2ecc71"     # Green (Below ceiling limits)
        if val <= high: return "#ffdd57"    # Yellow Warning
        return "#ff4b4b"                   # Red crossed

cal_color = get_status_color(today_cal, **THRESHOLDS["Calories"])
carb_color = get_status_color(today_carbs, **THRESHOLDS["Carbs"])
fat_color = get_status_color(today_fats, **THRESHOLDS["Fats"])
prot_color = get_status_color(today_protein, **THRESHOLDS["Protein"])

col1, col2 = st.columns(2)
with col1:
    st.markdown(f'<div class="glass-metric" style="border-left: 5px solid {cal_color};"><div class="metric-title" style="color:{cal_color if cal_color!="#ffdd57" else "#bba000"}">🔥 Calories</div><div class="metric-value">{today_cal:.1f} / {profile_map.get("Calories")} kcal</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="glass-metric" style="border-left: 5px solid {carb_color};"><div class="metric-title" style="color:{carb_color if carb_color!="#ffdd57" else "#bba000"}">🍞 Carbs</div><div class="metric-value">{today_carbs:.1f}g</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="glass-metric" style="border-left: 5px solid {prot_color};"><div class="metric-title" style="color:{prot_color if prot_color!="#ffdd57" else "#bba000"}">💪 Protein</div><div class="metric-value">{today_protein:.1f}g</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="glass-metric" style="border-left: 5px solid {fat_color};"><div class="metric-title" style="color:{fat_color if fat_color!="#ffdd57" else "#bba000"}">🥑 Fats</div><div class="metric-value">{today_fats:.1f}g</div></div>', unsafe_allow_html=True)

st.divider()

# ==========================================
# 6. MANAGEMENT & ENTRY INPUT MODULES
# ==========================================

# Smart Period 2-Button Toggle Component
st.subheader("🩸 Cycle Companion Drawer")
if is_period_active:
    st.markdown("💬 *Cycle currently flagged as active. Take it easy today, princess.*")
    st.markdown('<div class="period-end-btn">', unsafe_allow_html=True)
    if st.button("🌸 Period Ended Today", key="end_cycle_btn"):
        requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Cycles", headers=headers, json={
            "records": [{"fields": {"Date": today_str, "EventType": "Ended"}}]
        })
        st.cache_data.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="period-start-btn">', unsafe_allow_html=True)
    if st.button("🩸 Period Started Today", key="start_cycle_btn"):
        requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Cycles", headers=headers, json={
            "records": [{"fields": {"Date": today_str, "EventType": "Started"}}]
        })
        st.cache_data.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Backdate Cycle Fallback Manual Overrides
with st.expander("🗓️ Retroactively Log Cycle Dates"):
    with st.form("manual_cycle_form"):
        c_date = st.date_input("Event Date", value=datetime.now())
        c_type = st.selectbox("Action State", ["Started", "Ended"])
        submit_c = st.form_submit_button("Save Cycle Log")
        if submit_c:
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Cycles", headers=headers, json={
                "records": [{"fields": {"Date": c_date.strftime("%Y-%m-%d"), "EventType": c_type}}]
            })
            st.success("Cycle history updated!")
            st.cache_data.clear()
            st.rerun()

st.divider()

# Meals and Weight Logging Standard Accordions
repeated_foods = [food for food, count in Counter(food_history_pool).items() if count >= 3]

with st.expander("📝 Log Food Entries", expanded=False):
    log_date_target = st.date_input("Logging for which day?", value=datetime.now(), key="diet_log_date")
    
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
    submit_meal = st.button("Log Daily Meal Block", key="main_meal_btn")
    
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
                
                if log_date_target.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d"):
                    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                else:
                    current_time = f"{log_date_target.strftime('%Y-%m-%d')} 10:00 PM"
                
                data = {"records": [{"fields": {
                    "Timestamp": current_time, "Food Items": clean_meal_text,
                    "Calories": float(macros["calories"]), "Protein": float(macros["protein"]),
                    "Carbs": float(macros["carbs"]), "Fats": float(macros["fats"])
                }}]}
                requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Diet", headers=headers, json=data)
                if "her_meal_input" in st.session_state: del st.session_state["her_meal_input"]
                st.success("Macros tracked successfully!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

with st.expander("⚖️ Log Weight Metric", expanded=False):
    with st.form("weight_form", clear_on_submit=True):
        weight_date_target = st.date_input("Logging for which day?", value=datetime.now(), key="w_date_track")
        weight_input = st.number_input("Weight (kg)", min_value=10.0, max_value=250.0, step=0.05, format="%.2f")
        submit_weight = st.form_submit_button("Log Weight")
        
        if submit_weight and weight_input > 10.0:
            try:
                if weight_date_target.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d"):
                    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                else:
                    current_time = f"{weight_date_target.strftime('%Y-%m-%d')} 10:00 PM"
                data = {"records": [{"fields": {"Timestamp": current_time, "Weight": float(weight_input)}}]}
                requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Weight", headers=headers, json=data)
                st.success("Weight recorded!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

with st.expander("✨ Log A Milestone / Moment", expanded=False):
    with st.form("moments_form", clear_on_submit=True):
        moment_date = st.date_input("When did this happen?", value=datetime.now())
        moment_text = st.text_input("What did you achieve?", placeholder="e.g., Left Sugar, Finished Exam Block")
        show_on_top_check = st.checkbox("Pin to top highlight banner?", value=True)
        submit_moment = st.form_submit_button("Save Moment")
        if submit_moment and moment_text:
            try:
                clean_moment = moment_text.strip().title()
                data = {"records": [{"fields": {
                    "Date": moment_date.strftime("%Y-%m-%d"), "Moment": clean_moment, "Show On Top": show_on_top_check
                }}]}
                requests.post(f"https://api.airtable.com/v0/{BASE_ID}/Moments", headers=headers, json=data)
                st.success("Milestone saved!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

st.divider()

# ==========================================
# 7. ANALYTICS VISUALIZATIONS & CALENDAR MARKERS
# ==========================================
st.subheader("Trends & Milestones")

# Build data dictionary for active calendar visualization cells
milestone_dates = {}
for r in moments_records:
    dt = r.get("fields", {}).get("Date", "")
    txt = r.get("fields", {}).get("Moment", "")
    if dt: milestone_dates[dt] = txt

# Create a clean calendar layout mapping milestones to a floral element marker
if milestone_dates:
    st.caption("🌸 Milestone Calendar Map View")
    df_milestones = pd.DataFrame(list(milestone_dates.items()), columns=["Date", "Milestone"])
    df_milestones["Marker"] = "🌸"
    
    cal_dots = alt.Chart(df_milestones).mark_text(size=22, baseline='middle').encode(
        x=alt.X('Date:T', title="Timeline Timeline Map", axis=alt.Axis(format='%b %d', grid=True)),
        text='Marker:N',
        tooltip='Milestone:N'
    ).properties(height=80)
    st.altair_chart(cal_dots, use_container_width=True)

# Render Calorie Line Area Graph
chart_diet_data = {}
for record in reversed(diet_records):
    fields = record.get("fields", {})
    ts = fields.get("Timestamp", "")
    if ts: chart_diet_data[ts.split(" ")[0]] = chart_diet_data.get(ts.split(" ")[0], 0.0) + float(fields.get("Calories", 0))

if chart_diet_data:
    st.caption("🔥 Calorie Consumption Curves")
    df_cal = pd.DataFrame(list(chart_diet_data.items()), columns=["Date", "Calories"]).sort_values("Date")
    cal_line_color = "#e91e63" if today_cal > THRESHOLDS["Calories"]["high"] else "#2ecc71"
    
    cal_chart = alt.Chart(df_cal).mark_area(
        line={'color': cal_line_color, 'width': 2.5},
        color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color=cal_line_color, offset=0), alt.GradientStop(color='rgba(0,0,0,0)', offset=1)], x1=1, y1=1, x2=1, y2=0)
    ).encode(x=alt.X('Date:T', axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)), y=alt.Y('Calories:Q', scale=alt.Scale(zero=False))).properties(height=160).configure_view(strokeOpacity=0)
    st.altair_chart(cal_chart, use_container_width=True)

# Render Weight Line Graph
chart_weight_data = {}
for record in reversed(weight_records):
    fields = record.get("fields", {})
    ts = fields.get("Timestamp", "")
    if ts: chart_weight_data[ts.split(" ")[0]] = float(fields.get("Weight", 0))

if chart_weight_data:
    st.caption("⚖️ Weight Tracking Trend (kg)")
    df_weight = pd.DataFrame(list(chart_weight_data.items()), columns=["Date", "Weight"]).sort_values("Date")
    trend_color = "#2ecc71" if len(df_weight) < 2 or df_weight["Weight"].iloc[-1] <= df_weight["Weight"].iloc[-2] else "#e91e63"
    weight_chart = alt.Chart(df_weight).mark_line(
        color=trend_color, point=alt.OverlayMarkDef(color=trend_color, size=40, filled=True), strokeWidth=3, interpolate='monotone'
    ).encode(x=alt.X('Date:T', axis=alt.Axis(format='%b %d', labelAngle=-45, grid=False)), y=alt.Y('Weight:Q', scale=alt.Scale(zero=False))).properties(height=160).configure_view(strokeOpacity=0)
    st.altair_chart(weight_chart, use_container_width=True)
