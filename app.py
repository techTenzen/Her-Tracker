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
        background: linear-gradient(160deg, #eafaf2 0%, #fdf2f6 55%, #fff7f0 100%);
        background-attachment: fixed;
    }
    
    /* Immersive Premium Background Fluid Gradients */
    .stApp::before, .stApp::after {
        content: "";
        position: fixed;
        border-radius: 50%;
        filter: blur(85px);
        opacity: 0.45;
        z-index: 0;
        pointer-events: none;
    }
