#!/usr/bin/env python3
"""
Steam Presence GUI - Configuration Manager and Process Controller
Provides a graphical user interface for configuring steam-presence,
inspecting optional features, and controlling the live background presence.
Features high-contrast adaptive theming so text is always 100% visible.
"""

import os
import sys
import json
import time
import queue
import shutil
import signal
import threading
import subprocess
import webbrowser
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure directory is script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BACKUP_PATH = os.path.join(BASE_DIR, "config.json.bak")
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")

# Default template configuration (matches main.py defaultSettings)
DEFAULT_CONFIG: Dict[str, Any] = {
    "STEAM_API_KEY": "",
    "USER_IDS": "",
    "DISCORD_APPLICATION_ID": "869994714093465680",
    "FETCH_STEAM_RICH_PRESENCE": True,
    "FETCH_STEAM_REVIEWS": False,
    "ADD_STEAM_STORE_BUTTON": True,
    "STEAM_STORE_REGION": "us",
    "WEB_SCRAPE": False,
    "COVER_ART": {
        "STEAM_GRID_DB": {
            "ENABLED": False,
            "STEAM_GRID_API_KEY": ""
        },
        "USE_STEAM_STORE_FALLBACK": True
    },
    "LOCAL_GAMES": {
        "ENABLED": False,
        "LOCAL_DISCORD_APPLICATION_ID": "1062648118375616594",
        "GAMES": []
    },
    "GAME_OVERWRITE": {
        "ENABLED": False,
        "NAME": "",
        "SECONDS_SINCE_START": 0
    },
    "CUSTOM_ICON": {
        "ENABLED": False,
        "URL": "https://raw.githubusercontent.com/JustTemmie/steam-presence/main/readmeimages/defaulticon.png",
        "TEXT": "Steam Presence on Discord"
    },
    "BLACKLIST": [],
    "WHITELIST": []
}

def load_raw_config() -> tuple[Dict[str, Any], bool, str]:
    """
    Checks if config.json exists beforehand.
    If it exists, reads and merges with DEFAULT_CONFIG to guarantee complete structure.
    Returns (config_dict, is_existing_data, message).
    """
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            # Deep merge into defaults
            merged = json.loads(json.dumps(DEFAULT_CONFIG))
            for k, v in user_data.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, dict) and sub_k in merged[k] and isinstance(merged[k][sub_k], dict):
                            merged[k][sub_k].update(sub_v)
                        else:
                            merged[k][sub_k] = sub_v
                else:
                    merged[k] = v
            msg = f"Found existing config.json with saved data (Steam User: {merged.get('USER_IDS', 'N/A')})"
            return merged, True, msg
        except Exception as e:
            msg = f"Error reading existing config.json: {e}. Fallback to default template."
            return json.loads(json.dumps(DEFAULT_CONFIG)), False, msg
    else:
        msg = "No previous config.json found. Creating clean default configuration."
        return json.loads(json.dumps(DEFAULT_CONFIG)), False, msg


# Try importing tkinter and PIL
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("Error: tkinter is required for the GUI application.")
    print("Please install python3-tk or run the installer script.")
    sys.exit(1)

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# High-contrast Theme Palettes
THEMES = {
    "light": {
        "window_bg": "#f1f5f9",        # Clean light slate
        "card_bg": "#ffffff",          # Pure white card
        "card_border": "#cbd5e1",      # Distinct border
        "text_primary": "#0f172a",     # Near black / Slate-900 (ultra-sharp)
        "text_secondary": "#334155",   # Slate-700 description
        "text_muted": "#475569",       # Slate-600 subtext
        "accent": "#4f46e5",           # Vibrant Indigo
        "accent_text": "#0f172a",      # Button text
        "steam_blue": "#0284c7",       # Steam Cyan / Deep Blue
        "entry_bg": "#ffffff",         # White input background
        "entry_fg": "#0f172a",         # Black input text
        "entry_border": "#cbd5e1",
        "btn_bg": "#e2e8f0",
        "btn_fg": "#0f172a",           # Dark text on native button
        "success": "#15803d",          # Deep Green
        "danger": "#b91c1c",           # Deep Red
        "warning": "#b45309",          # Deep Amber
        "terminal_bg": "#0f172a",      # Dark terminal for logs
        "terminal_fg": "#f8fafc",      # Light text in terminal
        "badge_bg": "#e2e8f0",
        "badge_fg": "#15803d",
        "separator": "#e2e8f0"
    },
    "dark": {
        "window_bg": "#111318",
        "card_bg": "#1c1f26",
        "card_border": "#2e3342",
        "text_primary": "#f8fafc",
        "text_secondary": "#cbd5e1",
        "text_muted": "#94a3b8",
        "accent": "#5865F2",
        "accent_text": "#ffffff",
        "steam_blue": "#38bdf8",
        "entry_bg": "#13151b",
        "entry_fg": "#f8fafc",
        "entry_border": "#3b4252",
        "btn_bg": "#2b2f3d",
        "btn_fg": "#0f172a",
        "success": "#22c55e",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "terminal_bg": "#0b0c10",
        "terminal_fg": "#f8fafc",
        "badge_bg": "#1e293b",
        "badge_fg": "#4ade80",
        "separator": "#2e3342"
    }
}


class ScrollableFrame(tk.Frame):
    """A scrollable frame using a canvas and scrollbar with explicit background."""
    def __init__(self, container, bg_color="#f1f5f9", *args, **kwargs):
        super().__init__(container, bg=bg_color, *args, **kwargs)
        self.bg_color = bg_color
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg_color)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind_mouse_scroll(self.canvas)
        self.bind_mouse_scroll(self.scrollable_content)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def update_bg(self, new_bg):
        self.bg_color = new_bg
        self.config(bg=new_bg)
        self.canvas.config(bg=new_bg)
        self.scrollable_content.config(bg=new_bg)


class SteamPresenceGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Steam Presence - Control Center & Settings")
        self.root.geometry("990x780")
        self.root.minsize(860, 650)

        # Process management variables
        self.process: Optional[subprocess.Popen] = None
        self.log_queue: queue.Queue = queue.Queue()
        self.active_pid: Optional[int] = None

        # Check existing config beforehand
        self.config, self.is_existing_config, self.load_status_msg = load_raw_config()

        # Theme setting - Default to Light Mode so text on white background is 100% visible
        self.current_theme_name = "light"
        self.colors = THEMES[self.current_theme_name]

        self.root.configure(bg=self.colors["window_bg"])

        # Track UI widgets that need theme updates
        self.registered_cards: List[tk.Frame] = []
        self.registered_labels: List[tuple[tk.Label, str]] = []  # (label, role)
        self.registered_entries: List[tk.Entry] = []
        self.registered_checks: List[tk.Checkbutton] = []
        self.registered_listboxes: List[tk.Listbox] = []

        self._init_ttk_styles()
        self._init_variables()
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Populate fields from existing config
        self._populate_fields_from_config()

        # Start background queue checker
        self.root.after(100, self._process_log_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _init_ttk_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Configure Notebook styling
        style.configure("TNotebook", background=self.colors["window_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background="#e2e8f0", foreground="#0f172a", padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#ffffff")],
                  foreground=[("selected", "#0284c7")])

    def _init_variables(self):
        # Core Settings
        self.var_steam_api_key = tk.StringVar()
        self.var_user_ids = tk.StringVar()
        self.var_discord_app_id = tk.StringVar(value="869994714093465680")
        self.var_steam_region = tk.StringVar(value="us")
        self.var_show_api_key = tk.BooleanVar(value=False)

        # Optional Features
        self.var_rich_presence = tk.BooleanVar(value=True)
        self.var_reviews = tk.BooleanVar(value=False)
        self.var_store_button = tk.BooleanVar(value=True)
        self.var_web_scrape = tk.BooleanVar(value=False)

        # Game Overwrite
        self.var_overwrite_enabled = tk.BooleanVar(value=False)
        self.var_overwrite_name = tk.StringVar()
        self.var_overwrite_seconds = tk.StringVar(value="0")

        # Custom Icon
        self.var_custom_icon_enabled = tk.BooleanVar(value=False)
        self.var_custom_icon_url = tk.StringVar(value="https://raw.githubusercontent.com/JustTemmie/steam-presence/main/readmeimages/defaulticon.png")
        self.var_custom_icon_text = tk.StringVar(value="Steam Presence on Discord")

        # Cover Art
        self.var_sgdb_enabled = tk.BooleanVar(value=False)
        self.var_sgdb_api_key = tk.StringVar()
        self.var_store_fallback = tk.BooleanVar(value=True)

        # Local Games
        self.var_local_games_enabled = tk.BooleanVar(value=False)
        self.var_local_discord_app_id = tk.StringVar(value="1062648118375616594")
        self.local_games_list: List[str] = []

        # Filters
        self.blacklist_list: List[str] = []
        self.whitelist_list: List[str] = []

        # Service Status Info
        self.var_status_indicator = tk.StringVar(value="🔴 Stopped")
        self.var_status_account = tk.StringVar(value="Not checked")
        self.var_status_game = tk.StringVar(value="Idle")

    def _build_header(self):
        self.header_frame = tk.Frame(self.root, bg=self.colors["window_bg"])
        self.header_frame.pack(fill="x", padx=18, pady=(14, 8))

        # Title and branding
        title_box = tk.Frame(self.header_frame, bg=self.colors["window_bg"])
        title_box.pack(side="left")

        self.title_lbl = tk.Label(
            title_box,
            text="🎮 Steam Presence Manager",
            bg=self.colors["window_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 16, "bold")
        )
        self.title_lbl.pack(anchor="w")

        self.sub_lbl = tk.Label(
            title_box,
            text="Discord Rich Presence bridge for your Steam library & local games",
            bg=self.colors["window_bg"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 9)
        )
        self.sub_lbl.pack(anchor="w")

        # Right side controls: Theme Toggle & Config Badge
        right_box = tk.Frame(self.header_frame, bg=self.colors["window_bg"])
        right_box.pack(side="right")

        # Theme switcher button
        self.btn_theme_toggle = tk.Button(
            right_box,
            text="🌙 Dark Mode",
            fg=self.colors["btn_fg"],
            font=("Segoe UI", 9, "bold"),
            relief="groove",
            command=self._toggle_theme
        )
        self.btn_theme_toggle.pack(side="right", padx=(8, 0))

        # Config Status Badge
        badge_text = "✓ Existing config.json Loaded" if self.is_existing_config else "ℹ New config.json initialized"
        self.lbl_config_badge = tk.Label(
            right_box,
            text=badge_text,
            bg=self.colors["badge_bg"],
            fg=self.colors["badge_fg"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief="solid",
            bd=1
        )
        self.lbl_config_badge.pack(side="right")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=6)

        # Tab 1: Core Settings (Required)
        self.tab_core = ScrollableFrame(self.notebook, bg_color=self.colors["window_bg"])
        self.notebook.add(self.tab_core, text="🔑 Core Settings")
        self._build_tab_core(self.tab_core.scrollable_content)

        # Tab 2: Optional Features (Mentioned with descriptions)
        self.tab_optional = ScrollableFrame(self.notebook, bg_color=self.colors["window_bg"])
        self.notebook.add(self.tab_optional, text="⭐ Optional Features")
        self._build_tab_optional(self.tab_optional.scrollable_content)

        # Tab 3: Cover Art & Local Games
        self.tab_art_local = ScrollableFrame(self.notebook, bg_color=self.colors["window_bg"])
        self.notebook.add(self.tab_art_local, text="🎨 Cover Art & Games")
        self._build_tab_art_local(self.tab_art_local.scrollable_content)

        # Tab 4: Control Center & Live Logs
        self.tab_control = tk.Frame(self.notebook, bg=self.colors["window_bg"])
        self.notebook.add(self.tab_control, text="🚀 Control & Live Logs")
        self._build_tab_control(self.tab_control)

    # ----------------------------------------------------
    # TAB 1: CORE / REQUIRED SETTINGS
    # ----------------------------------------------------
    def _build_tab_core(self, parent):
        card = self._create_card(parent, "Primary Steam & Discord Setup", "These fields are essential for Steam Presence to link your account and communicate with Discord.")

        # Steam Web API Key
        self._create_field_label(card, "Steam Web API Key *")

        key_frame = tk.Frame(card, bg=self.colors["card_bg"])
        key_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.entry_steam_key = self._create_entry(key_frame, self.var_steam_api_key, show="*")
        self.entry_steam_key.pack(side="left", fill="x", expand=True, ipady=4)

        self.btn_toggle_key = tk.Button(
            key_frame,
            text="👁 Show",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9),
            command=self._toggle_show_api_key
        )
        self.btn_toggle_key.pack(side="left", padx=6)

        btn_get_key = tk.Button(
            key_frame,
            text="🌐 Get API Key",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9, "bold"),
            command=lambda: webbrowser.open("https://steamcommunity.com/dev/apikey")
        )
        btn_get_key.pack(side="left", padx=2)

        self._create_field_desc(card, "Used to fetch your currently played game from Steam HQ. Obtain your free key from Steam Developer Portal.")

        # Steam User ID
        self._create_field_label(card, "Steam User ID(s) * (SteamID64)")

        id_frame = tk.Frame(card, bg=self.colors["card_bg"])
        id_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.entry_user_id = self._create_entry(id_frame, self.var_user_ids)
        self.entry_user_id.pack(side="left", fill="x", expand=True, ipady=4)

        btn_find_id = tk.Button(
            id_frame,
            text="🔍 SteamDB Calculator",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9, "bold"),
            command=lambda: webbrowser.open("https://steamdb.info/calculator/")
        )
        btn_find_id.pack(side="left", padx=6)

        btn_test_account = tk.Button(
            id_frame,
            text="⚡ Verify Account",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9, "bold"),
            command=self._test_steam_connection_live
        )
        btn_test_account.pack(side="left", padx=2)

        self._create_field_desc(card, "Your 17-digit SteamID64 (e.g. 76561198076041281). For multiple accounts, separate with commas: id1,id2")

        # Discord Application ID
        self._create_field_label(card, "Discord Application ID (Client ID)")

        discord_frame = tk.Frame(card, bg=self.colors["card_bg"])
        discord_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.entry_discord_app = self._create_entry(discord_frame, self.var_discord_app_id)
        self.entry_discord_app.pack(side="left", fill="x", expand=True, ipady=4)

        btn_default_discord = tk.Button(
            discord_frame,
            text="↺ Reset Default",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9),
            command=lambda: self.var_discord_app_id.set("869994714093465680")
        )
        btn_default_discord.pack(side="left", padx=6)

        self._create_field_desc(card, "Default '869994714093465680' displays as 'a game on steam'. Change only if you created a custom app on Discord Developer Portal.")

        # Steam Store Region
        self._create_field_label(card, "Steam Store Region (Currency / Pricing)")

        region_frame = tk.Frame(card, bg=self.colors["card_bg"])
        region_frame.pack(fill="x", padx=12, pady=(0, 4))

        regions = ["us", "gb", "eu", "de", "in", "ca", "au", "fr", "es", "jp", "br", "ru"]
        self.combo_region = ttk.Combobox(
            region_frame,
            textvariable=self.var_steam_region,
            values=regions,
            width=14,
            state="readonly"
        )
        self.combo_region.pack(side="left")

        self._create_field_desc(card, "Determines the currency and region code for the store button price formatting (e.g. us = USD, gb = GBP, in = INR).")

    # ----------------------------------------------------
    # TAB 2: OPTIONAL FEATURES (DETAILED & SEPARATE)
    # ----------------------------------------------------
    def _build_tab_optional(self, parent):
        self._create_card(
            parent,
            "Optional Features & Customizations",
            "Enhance your Discord presence with rich metadata, store buttons, review ratings, custom titles, and icons. All features below are optional."
        )

        # Feature 1: Enhanced Rich Presence
        self._create_feature_toggle(
            parent,
            title="1. Fetch Steam Enhanced Rich Presence (FETCH_STEAM_RICH_PRESENCE)",
            var=self.var_rich_presence,
            desc="Pulls detailed real-time game status from Steam for games that support it (e.g. 'Browsing Menus' in Bloons TD6, 'Battling in Elysium' in Hades, or current map/mode in Counter-Strike 2). Recommended: Enabled."
        )

        # Feature 2: Steam Store Button
        self._create_feature_toggle(
            parent,
            title="2. Discord Profile 'View on Steam' Button (ADD_STEAM_STORE_BUTTON)",
            var=self.var_store_button,
            desc="Adds a clickable button to your Discord Rich Presence card that allows friends to jump directly to the game's Steam Store page and see its current price."
        )

        # Feature 3: Steam Reviews
        self._create_feature_toggle(
            parent,
            title="3. Fetch Steam Community Reviews (FETCH_STEAM_REVIEWS)",
            var=self.var_reviews,
            desc="Queries the Steam Store to show the community review score (e.g. 'Very Positive (88%)') directly in your Discord presence status line."
        )

        # Feature 4: Web Scraping for Non-Steam Games
        scrape_card = self._create_feature_toggle(
            parent,
            title="4. Web Scraping for Non-Steam Games (WEB_SCRAPE)",
            var=self.var_web_scrape,
            desc="Steam's official API does not report non-Steam games added to your library. Enabling web-scraping queries your Steam Community profile every 20 seconds. Requires placing a valid 'cookies.txt' file in the steampresence folder."
        )
        cookie_status = "✓ cookies.txt detected in directory" if os.path.exists(COOKIES_PATH) else "⚠ cookies.txt not found (place it in folder if enabling)"
        cookie_color = self.colors["success"] if os.path.exists(COOKIES_PATH) else self.colors["warning"]
        self.lbl_cookie = tk.Label(scrape_card, text=cookie_status, bg=self.colors["card_bg"], fg=cookie_color, font=("Segoe UI", 9, "bold"))
        self.lbl_cookie.pack(anchor="w", padx=32, pady=(0, 8))

        # Feature 5: Game Overwrite Mode
        overwrite_card = self._create_card(
            parent,
            "5. Game Overwrite Mode (GAME_OVERWRITE)",
            "Force Steam Presence to always broadcast a custom game name on Discord, even when you aren't playing anything (e.g. 'Hollow Knight: Silksong' or 'Working on Project')."
        )
        chk_overwrite = self._create_checkbox(overwrite_card, "Enable Game Name Overwrite", self.var_overwrite_enabled)
        chk_overwrite.pack(anchor="w", padx=12, pady=(4, 6))

        ow_row1 = tk.Frame(overwrite_card, bg=self.colors["card_bg"])
        ow_row1.pack(fill="x", padx=12, pady=4)
        lbl_ow1 = tk.Label(ow_row1, text="Custom Display Game Name:", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_ow1.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_ow1, "primary"))
        self._create_entry(ow_row1, self.var_overwrite_name).pack(side="left", fill="x", expand=True, ipady=3)

        ow_row2 = tk.Frame(overwrite_card, bg=self.colors["card_bg"])
        ow_row2.pack(fill="x", padx=12, pady=(4, 10))
        lbl_ow2 = tk.Label(ow_row2, text="Elapsed Time Offset (seconds):", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_ow2.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_ow2, "primary"))
        self._create_entry(ow_row2, self.var_overwrite_seconds, width=12).pack(side="left", ipady=3)
        lbl_ow_hint = tk.Label(ow_row2, text="(Set to 0 for current session time, or e.g. 7200 for 2 hours ago)", bg=self.colors["card_bg"], fg=self.colors["text_secondary"], font=("Segoe UI", 9))
        lbl_ow_hint.pack(side="left", padx=8)
        self.registered_labels.append((lbl_ow_hint, "secondary"))

        # Feature 6: Custom Presence Icon
        icon_card = self._create_card(
            parent,
            "6. Custom Presence Icon & Tooltip (CUSTOM_ICON)",
            "Overrides the small icon in the bottom-right corner of the Discord card with your own custom logo URL and hover tooltip text."
        )
        chk_icon = self._create_checkbox(icon_card, "Enable Custom Corner Icon", self.var_custom_icon_enabled)
        chk_icon.pack(anchor="w", padx=12, pady=(4, 6))

        ic_row1 = tk.Frame(icon_card, bg=self.colors["card_bg"])
        ic_row1.pack(fill="x", padx=12, pady=4)
        lbl_ic1 = tk.Label(ic_row1, text="Direct Icon Image URL (PNG/WebP):", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_ic1.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_ic1, "primary"))
        self._create_entry(ic_row1, self.var_custom_icon_url).pack(side="left", fill="x", expand=True, ipady=3)

        ic_row2 = tk.Frame(icon_card, bg=self.colors["card_bg"])
        ic_row2.pack(fill="x", padx=12, pady=(4, 10))
        lbl_ic2 = tk.Label(ic_row2, text="Hover Tooltip Text:", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_ic2.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_ic2, "primary"))
        self._create_entry(ic_row2, self.var_custom_icon_text).pack(side="left", fill="x", expand=True, ipady=3)

    # ----------------------------------------------------
    # TAB 3: COVER ART & LOCAL GAMES
    # ----------------------------------------------------
    def _build_tab_art_local(self, parent):
        # SteamGridDB
        sgdb_card = self._create_card(
            parent,
            "SteamGridDB Integration (COVER_ART)",
            "Download high-definition game art, transparent icons, and logos straight from SteamGridDB."
        )

        chk_sgdb = self._create_checkbox(sgdb_card, "Enable SteamGridDB Cover Art", self.var_sgdb_enabled)
        chk_sgdb.pack(anchor="w", padx=12, pady=(4, 4))

        sgdb_row = tk.Frame(sgdb_card, bg=self.colors["card_bg"])
        sgdb_row.pack(fill="x", padx=12, pady=4)
        lbl_sgdb = tk.Label(sgdb_row, text="SteamGridDB API Key:", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_sgdb.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_sgdb, "primary"))
        self._create_entry(sgdb_row, self.var_sgdb_api_key).pack(side="left", fill="x", expand=True, ipady=3)

        btn_sgdb_link = tk.Button(
            sgdb_row,
            text="🌐 Get SGDB Key",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9, "bold"),
            command=lambda: webbrowser.open("https://www.steamgriddb.com/profile/preferences/api")
        )
        btn_sgdb_link.pack(side="left", padx=6)

        chk_fallback = self._create_checkbox(sgdb_card, "Use Steam Store Cover Art Fallback (recommended)", self.var_store_fallback)
        chk_fallback.pack(anchor="w", padx=12, pady=(4, 10))

        # Local Games Monitoring
        local_card = self._create_card(
            parent,
            "Local Application & Process Tracking (LOCAL_GAMES)",
            "Track games or software running locally on your computer (e.g. standalone emulators, Minecraft, Discord) without Steam."
        )

        chk_local = self._create_checkbox(local_card, "Enable Local Game Tracking", self.var_local_games_enabled)
        chk_local.pack(anchor="w", padx=12, pady=(4, 4))

        loc_app_row = tk.Frame(local_card, bg=self.colors["card_bg"])
        loc_app_row.pack(fill="x", padx=12, pady=4)
        lbl_loc = tk.Label(loc_app_row, text="Local Discord App ID:", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_loc.pack(side="left", padx=(0, 8))
        self.registered_labels.append((lbl_loc, "primary"))
        self._create_entry(loc_app_row, self.var_local_discord_app_id).pack(side="left", fill="x", expand=True, ipady=3)

        # Process list management
        list_container = tk.Frame(local_card, bg=self.colors["card_bg"])
        list_container.pack(fill="x", padx=12, pady=6)

        self.listbox_local_games = self._create_listbox(list_container, height=5)
        self.listbox_local_games.pack(side="left", fill="x", expand=True)

        scrl = ttk.Scrollbar(list_container, orient="vertical", command=self.listbox_local_games.yview)
        scrl.pack(side="left", fill="y")
        self.listbox_local_games.config(yscrollcommand=scrl.set)

        list_actions = tk.Frame(local_card, bg=self.colors["card_bg"])
        list_actions.pack(fill="x", padx=12, pady=(4, 10))

        self.entry_add_process = self._create_entry(list_actions, None)
        self.entry_add_process.pack(side="left", fill="x", expand=True, ipady=3)

        btn_add_proc = tk.Button(
            list_actions,
            text="+ Add Process",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9, "bold"),
            command=self._add_local_game
        )
        btn_add_proc.pack(side="left", padx=4)

        btn_del_proc = tk.Button(
            list_actions,
            text="− Remove Selected",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9),
            command=self._remove_local_game
        )
        btn_del_proc.pack(side="left", padx=4)

        if HAS_PSUTIL:
            btn_scan_proc = tk.Button(
                list_actions,
                text="⚡ Running Processes...",
                fg=self.colors["btn_fg"],
                relief="groove",
                font=("Segoe UI", 9, "bold"),
                command=self._show_running_processes_dialog
            )
            btn_scan_proc.pack(side="left", padx=4)

        # Blacklist & Whitelist
        filter_card = self._create_card(
            parent,
            "Presence Blacklist & Whitelist",
            "Control which game titles appear on Discord. Games in Blacklist are hidden. If Whitelist has items, only those games are shown."
        )

        filter_cols = tk.Frame(filter_card, bg=self.colors["card_bg"])
        filter_cols.pack(fill="x", padx=12, pady=6)

        # Blacklist Column
        col_bl = tk.Frame(filter_cols, bg=self.colors["card_bg"])
        col_bl.pack(side="left", fill="both", expand=True, padx=(0, 6))

        lbl_bl = tk.Label(col_bl, text="⛔ Blacklist (Never show):", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_bl.pack(anchor="w")
        self.registered_labels.append((lbl_bl, "primary"))

        self.listbox_blacklist = self._create_listbox(col_bl, height=4)
        self.listbox_blacklist.pack(fill="x", pady=4)
        bl_row = tk.Frame(col_bl, bg=self.colors["card_bg"])
        bl_row.pack(fill="x")
        self.entry_bl = self._create_entry(bl_row, None)
        self.entry_bl.pack(side="left", fill="x", expand=True, ipady=2)
        tk.Button(bl_row, text="+", fg=self.colors["btn_fg"], relief="groove", font=("Segoe UI", 9, "bold"), command=self._add_blacklist).pack(side="left", padx=2)
        tk.Button(bl_row, text="−", fg=self.colors["btn_fg"], relief="groove", font=("Segoe UI", 9, "bold"), command=self._remove_blacklist).pack(side="left")

        # Whitelist Column
        col_wl = tk.Frame(filter_cols, bg=self.colors["card_bg"])
        col_wl.pack(side="left", fill="both", expand=True, padx=(6, 0))

        lbl_wl = tk.Label(col_wl, text="✅ Whitelist (Only show these):", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 10, "bold"))
        lbl_wl.pack(anchor="w")
        self.registered_labels.append((lbl_wl, "primary"))

        self.listbox_whitelist = self._create_listbox(col_wl, height=4)
        self.listbox_whitelist.pack(fill="x", pady=4)
        wl_row = tk.Frame(col_wl, bg=self.colors["card_bg"])
        wl_row.pack(fill="x")
        self.entry_wl = self._create_entry(wl_row, None)
        self.entry_wl.pack(side="left", fill="x", expand=True, ipady=2)
        tk.Button(wl_row, text="+", fg=self.colors["btn_fg"], relief="groove", font=("Segoe UI", 9, "bold"), command=self._add_whitelist).pack(side="left", padx=2)
        tk.Button(wl_row, text="−", fg=self.colors["btn_fg"], relief="groove", font=("Segoe UI", 9, "bold"), command=self._remove_whitelist).pack(side="left")

    # ----------------------------------------------------
    # TAB 4: CONTROL CENTER & LIVE LOGS
    # ----------------------------------------------------
    def _build_tab_control(self, parent):
        # Top Dashboard bar
        self.dash = tk.Frame(parent, bg=self.colors["card_bg"], bd=1, relief="solid", highlightbackground=self.colors["card_border"], highlightthickness=1)
        self.dash.pack(fill="x", padx=14, pady=10)
        self.registered_cards.append(self.dash)

        # Status indicators
        stat_box1 = tk.Frame(self.dash, bg=self.colors["card_bg"])
        stat_box1.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        lbl_s1 = tk.Label(stat_box1, text="Process Status", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 9))
        lbl_s1.pack(padx=8, pady=(4, 0), anchor="w")
        self.registered_labels.append((lbl_s1, "muted"))
        self.lbl_proc_status = tk.Label(stat_box1, textvariable=self.var_status_indicator, bg=self.colors["card_bg"], fg=self.colors["danger"], font=("Segoe UI", 12, "bold"))
        self.lbl_proc_status.pack(padx=8, pady=(0, 4), anchor="w")

        stat_box2 = tk.Frame(self.dash, bg=self.colors["card_bg"])
        stat_box2.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        lbl_s2 = tk.Label(stat_box2, text="Steam User", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 9))
        lbl_s2.pack(padx=8, pady=(4, 0), anchor="w")
        self.registered_labels.append((lbl_s2, "muted"))
        self.lbl_steam_user = tk.Label(stat_box2, textvariable=self.var_status_account, bg=self.colors["card_bg"], fg=self.colors["steam_blue"], font=("Segoe UI", 11, "bold"))
        self.lbl_steam_user.pack(padx=8, pady=(0, 4), anchor="w")

        stat_box3 = tk.Frame(self.dash, bg=self.colors["card_bg"])
        stat_box3.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        lbl_s3 = tk.Label(stat_box3, text="Current Detected Game", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 9))
        lbl_s3.pack(padx=8, pady=(4, 0), anchor="w")
        self.registered_labels.append((lbl_s3, "muted"))
        self.lbl_curr_game = tk.Label(stat_box3, textvariable=self.var_status_game, bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Segoe UI", 11, "bold"))
        self.lbl_curr_game.pack(padx=8, pady=(0, 4), anchor="w")
        self.registered_labels.append((self.lbl_curr_game, "primary"))

        # Action Buttons Row
        self.btn_bar = tk.Frame(parent, bg=self.colors["window_bg"])
        self.btn_bar.pack(fill="x", padx=14, pady=(0, 8))

        self.btn_start = tk.Button(
            self.btn_bar,
            text="▶ Start Presence",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
            command=self.start_process
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = tk.Button(
            self.btn_bar,
            text="⏹ Stop Presence",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
            state="disabled",
            command=self.stop_process
        )
        self.btn_stop.pack(side="left", padx=4)

        self.btn_restart = tk.Button(
            self.btn_bar,
            text="🔄 Restart",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
            command=self.restart_process
        )
        self.btn_restart.pack(side="left", padx=4)

        self.btn_save_top = tk.Button(
            self.btn_bar,
            text="💾 Save config.json",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
            command=self.save_configuration
        )
        self.btn_save_top.pack(side="right", padx=4)

        btn_clear_log = tk.Button(
            self.btn_bar,
            text="🧹 Clear Logs",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 9),
            padx=8,
            pady=6,
            command=self._clear_logs
        )
        btn_clear_log.pack(side="right", padx=4)

        # Live Log Terminal Console
        log_frame = tk.Frame(parent, bg=self.colors["window_bg"])
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.log_text = tk.Text(
            log_frame,
            bg=self.colors["terminal_bg"],
            fg=self.colors["terminal_fg"],
            insertbackground="white",
            relief="solid",
            bd=1,
            highlightbackground=self.colors["card_border"],
            highlightthickness=1,
            font=("Consolas", 10),
            wrap="word"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="left", fill="y")
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Configure Terminal Color Tags
        self.log_text.tag_configure("info", foreground="#38bdf8")
        self.log_text.tag_configure("error", foreground="#ef4444", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("success", foreground="#4ade80", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("timestamp", foreground="#94a3b8")
        self.log_text.tag_configure("game", foreground="#818cf8", font=("Consolas", 10, "bold"))

        # Welcome message in terminal
        self._append_log("Steam Presence Control Center Initialized.", "info")
        if self.is_existing_config:
            self._append_log(f"Preloaded configuration from existing config.json: {self.load_status_msg}", "success")
        else:
            self._append_log("New configuration initialized. Please fill in your Steam API Key and User ID.", "info")

    def _build_footer(self):
        self.footer = tk.Frame(self.root, bg=self.colors["window_bg"])
        self.footer.pack(fill="x", padx=18, pady=(4, 12))

        self.lbl_toast = tk.Label(
            self.footer,
            text=self.load_status_msg,
            bg=self.colors["window_bg"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 9)
        )
        self.lbl_toast.pack(side="left")

        btn_save = tk.Button(
            self.footer,
            text="💾 Save Configuration",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=6,
            command=self.save_configuration
        )
        btn_save.pack(side="right", padx=4)

        btn_quit = tk.Button(
            self.footer,
            text="Close GUI",
            fg=self.colors["btn_fg"],
            relief="groove",
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
            command=self._on_closing
        )
        btn_quit.pack(side="right", padx=4)

    # ----------------------------------------------------
    # WIDGET FACTORIES (ENSURES VISIBLE HIGH-CONTRAST COLORS)
    # ----------------------------------------------------
    def _create_card(self, parent, title: str, subtitle: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.colors["card_bg"],
            relief="solid",
            bd=1,
            highlightbackground=self.colors["card_border"],
            highlightthickness=1
        )
        card.pack(fill="x", padx=12, pady=8)
        self.registered_cards.append(card)

        t_lbl = tk.Label(
            card,
            text=title,
            bg=self.colors["card_bg"],
            fg=self.colors["steam_blue"],
            font=("Segoe UI", 12, "bold")
        )
        t_lbl.pack(anchor="w", padx=12, pady=(10, 2))
        self.registered_labels.append((t_lbl, "accent"))

        if subtitle:
            s_lbl = tk.Label(
                card,
                text=subtitle,
                bg=self.colors["card_bg"],
                fg=self.colors["text_secondary"],
                font=("Segoe UI", 9)
            )
            s_lbl.pack(anchor="w", padx=12, pady=(0, 6))
            self.registered_labels.append((s_lbl, "secondary"))

        sep = tk.Frame(card, height=1, bg=self.colors["separator"])
        sep.pack(fill="x", padx=12, pady=(2, 8))
        return card

    def _create_feature_toggle(self, parent, title: str, var: tk.BooleanVar, desc: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.colors["card_bg"],
            relief="solid",
            bd=1,
            highlightbackground=self.colors["card_border"],
            highlightthickness=1
        )
        card.pack(fill="x", padx=12, pady=6)
        self.registered_cards.append(card)

        chk = self._create_checkbox(card, title, var)
        chk.pack(anchor="w", padx=12, pady=(8, 2))

        d_lbl = tk.Label(
            card,
            text=desc,
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9),
            wraplength=880,
            justify="left"
        )
        d_lbl.pack(anchor="w", padx=32, pady=(0, 8))
        self.registered_labels.append((d_lbl, "secondary"))
        return card

    def _create_field_label(self, parent, text: str) -> tk.Label:
        lbl = tk.Label(
            parent,
            text=text,
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10, "bold")
        )
        lbl.pack(anchor="w", padx=12, pady=(10, 2))
        self.registered_labels.append((lbl, "primary"))
        return lbl

    def _create_field_desc(self, parent, text: str) -> tk.Label:
        desc = tk.Label(
            parent,
            text=text,
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9)
        )
        desc.pack(anchor="w", padx=12, pady=(0, 10))
        self.registered_labels.append((desc, "secondary"))
        return desc

    def _create_entry(self, parent, var: Optional[tk.StringVar], show: str = "", width: Optional[int] = None) -> tk.Entry:
        kwargs = {
            "bg": self.colors["entry_bg"],
            "fg": self.colors["entry_fg"],
            "insertbackground": self.colors["entry_fg"],
            "highlightbackground": self.colors["entry_border"],
            "highlightcolor": self.colors["steam_blue"],
            "highlightthickness": 1,
            "relief": "solid",
            "bd": 1,
            "font": ("Consolas", 10)
        }
        if var is not None:
            kwargs["textvariable"] = var
        if show:
            kwargs["show"] = show
        if width is not None:
            kwargs["width"] = width

        e = tk.Entry(parent, **kwargs)
        self.registered_entries.append(e)
        return e

    def _create_checkbox(self, parent, text: str, var: tk.BooleanVar) -> tk.Checkbutton:
        chk = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            selectcolor=self.colors["card_bg"],
            activebackground=self.colors["card_bg"],
            activeforeground=self.colors["text_primary"],
            font=("Segoe UI", 10, "bold")
        )
        self.registered_checks.append(chk)
        return chk

    def _create_listbox(self, parent, height: int = 5) -> tk.Listbox:
        lb = tk.Listbox(
            parent,
            bg=self.colors["entry_bg"],
            fg=self.colors["entry_fg"],
            selectbackground=self.colors["steam_blue"],
            selectforeground="#ffffff",
            height=height,
            relief="solid",
            bd=1,
            highlightbackground=self.colors["card_border"],
            highlightthickness=1,
            font=("Consolas", 9)
        )
        self.registered_listboxes.append(lb)
        return lb

    # ----------------------------------------------------
    # THEME TOGGLING (ENSURES TEXT IS ALWAYS HIGH-CONTRAST)
    # ----------------------------------------------------
    def _toggle_theme(self):
        new_theme = "dark" if self.current_theme_name == "light" else "light"
        self.current_theme_name = new_theme
        self.colors = THEMES[new_theme]
        self._apply_theme()

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["window_bg"])
        self.header_frame.configure(bg=c["window_bg"])
        self.title_lbl.configure(bg=c["window_bg"], fg=c["text_primary"])
        self.sub_lbl.configure(bg=c["window_bg"], fg=c["text_muted"])
        self.lbl_config_badge.configure(bg=c["badge_bg"], fg=c["badge_fg"])
        self.footer.configure(bg=c["window_bg"])
        self.lbl_toast.configure(bg=c["window_bg"], fg=c["text_muted"])

        btn_txt = "☀️ Light Mode" if self.current_theme_name == "dark" else "🌙 Dark Mode"
        self.btn_theme_toggle.configure(text=btn_txt, fg=c["btn_fg"])

        # Update scrollable frames
        self.tab_core.update_bg(c["window_bg"])
        self.tab_optional.update_bg(c["window_bg"])
        self.tab_art_local.update_bg(c["window_bg"])
        self.tab_control.configure(bg=c["window_bg"])
        self.btn_bar.configure(bg=c["window_bg"])

        # Update registered cards
        for card in self.registered_cards:
            card.configure(bg=c["card_bg"], highlightbackground=c["card_border"])
            for child in card.winfo_children():
                if isinstance(child, tk.Frame) and child != card:
                    child.configure(bg=c["card_bg"])

        # Update registered labels
        for lbl, role in self.registered_labels:
            if role == "primary":
                lbl.configure(bg=c["card_bg"], fg=c["text_primary"])
            elif role == "secondary":
                lbl.configure(bg=c["card_bg"], fg=c["text_secondary"])
            elif role == "muted":
                lbl.configure(bg=c["card_bg"], fg=c["text_muted"])
            elif role == "accent":
                lbl.configure(bg=c["card_bg"], fg=c["steam_blue"])

        # Update registered entries
        for entry in self.registered_entries:
            entry.configure(
                bg=c["entry_bg"],
                fg=c["entry_fg"],
                insertbackground=c["entry_fg"],
                highlightbackground=c["entry_border"],
                highlightcolor=c["steam_blue"]
            )

        # Update registered checkbuttons
        for chk in self.registered_checks:
            chk.configure(
                bg=c["card_bg"],
                fg=c["text_primary"],
                selectcolor=c["card_bg"],
                activebackground=c["card_bg"],
                activeforeground=c["text_primary"]
            )

        # Update registered listboxes
        for lb in self.registered_listboxes:
            lb.configure(
                bg=c["entry_bg"],
                fg=c["entry_fg"],
                selectbackground=c["steam_blue"],
                highlightbackground=c["card_border"]
            )

        # Update terminal console
        self.log_text.configure(
            bg=c["terminal_bg"],
            fg=c["terminal_fg"],
            highlightbackground=c["card_border"]
        )

        self._init_ttk_styles()

    # ----------------------------------------------------
    # CONFIG POPULATION & SAVING
    # ----------------------------------------------------
    def _populate_fields_from_config(self):
        """Populates all GUI fields with loaded config data."""
        c = self.config
        self.var_steam_api_key.set(str(c.get("STEAM_API_KEY", "")))
        self.var_user_ids.set(str(c.get("USER_IDS", "")))
        self.var_discord_app_id.set(str(c.get("DISCORD_APPLICATION_ID", "869994714093465680")))
        self.var_steam_region.set(str(c.get("STEAM_STORE_REGION", "us")))

        self.var_rich_presence.set(bool(c.get("FETCH_STEAM_RICH_PRESENCE", True)))
        self.var_reviews.set(bool(c.get("FETCH_STEAM_REVIEWS", False)))
        self.var_store_button.set(bool(c.get("ADD_STEAM_STORE_BUTTON", True)))
        self.var_web_scrape.set(bool(c.get("WEB_SCRAPE", False)))

        # Cover Art
        cover_art = c.get("COVER_ART", {})
        sgdb = cover_art.get("STEAM_GRID_DB", {})
        self.var_sgdb_enabled.set(bool(sgdb.get("ENABLED", False)))
        self.var_sgdb_api_key.set(str(sgdb.get("STEAM_GRID_API_KEY", "")))
        self.var_store_fallback.set(bool(cover_art.get("USE_STEAM_STORE_FALLBACK", True)))

        # Local Games
        local_g = c.get("LOCAL_GAMES", {})
        self.var_local_games_enabled.set(bool(local_g.get("ENABLED", False)))
        self.var_local_discord_app_id.set(str(local_g.get("LOCAL_DISCORD_APPLICATION_ID", "1062648118375616594")))
        self.local_games_list = list(local_g.get("GAMES", []))
        self.listbox_local_games.delete(0, tk.END)
        for g in self.local_games_list:
            self.listbox_local_games.insert(tk.END, g)

        # Game Overwrite
        go = c.get("GAME_OVERWRITE", {})
        self.var_overwrite_enabled.set(bool(go.get("ENABLED", False)))
        self.var_overwrite_name.set(str(go.get("NAME", "")))
        self.var_overwrite_seconds.set(str(go.get("SECONDS_SINCE_START", 0)))

        # Custom Icon
        ci = c.get("CUSTOM_ICON", {})
        self.var_custom_icon_enabled.set(bool(ci.get("ENABLED", False)))
        self.var_custom_icon_url.set(str(ci.get("URL", "https://raw.githubusercontent.com/JustTemmie/steam-presence/main/readmeimages/defaulticon.png")))
        self.var_custom_icon_text.set(str(ci.get("TEXT", "Steam Presence on Discord")))

        # Blacklist & Whitelist
        self.blacklist_list = list(c.get("BLACKLIST", []))
        self.listbox_blacklist.delete(0, tk.END)
        for b in self.blacklist_list:
            self.listbox_blacklist.insert(tk.END, b)

        self.whitelist_list = list(c.get("WHITELIST", []))
        self.listbox_whitelist.delete(0, tk.END)
        for w in self.whitelist_list:
            self.listbox_whitelist.insert(tk.END, w)

        if self.is_existing_config:
            self.var_status_account.set(f"SteamID: {self.var_user_ids.get()[:8]}...")

    def collect_config_dict(self) -> Dict[str, Any]:
        """Collects all UI field values into a complete config dictionary."""
        try:
            seconds_val = int(self.var_overwrite_seconds.get().strip() or "0")
        except ValueError:
            seconds_val = 0

        config_out: Dict[str, Any] = {
            "STEAM_API_KEY": self.var_steam_api_key.get().strip(),
            "USER_IDS": self.var_user_ids.get().strip(),
            "DISCORD_APPLICATION_ID": self.var_discord_app_id.get().strip() or "869994714093465680",
            "FETCH_STEAM_RICH_PRESENCE": self.var_rich_presence.get(),
            "FETCH_STEAM_REVIEWS": self.var_reviews.get(),
            "ADD_STEAM_STORE_BUTTON": self.var_store_button.get(),
            "STEAM_STORE_REGION": self.var_steam_region.get().strip() or "us",
            "WEB_SCRAPE": self.var_web_scrape.get(),
            "COVER_ART": {
                "STEAM_GRID_DB": {
                    "ENABLED": self.var_sgdb_enabled.get(),
                    "STEAM_GRID_API_KEY": self.var_sgdb_api_key.get().strip()
                },
                "USE_STEAM_STORE_FALLBACK": self.var_store_fallback.get()
            },
            "LOCAL_GAMES": {
                "ENABLED": self.var_local_games_enabled.get(),
                "LOCAL_DISCORD_APPLICATION_ID": self.var_local_discord_app_id.get().strip() or "1062648118375616594",
                "GAMES": list(self.local_games_list)
            },
            "GAME_OVERWRITE": {
                "ENABLED": self.var_overwrite_enabled.get(),
                "NAME": self.var_overwrite_name.get().strip(),
                "SECONDS_SINCE_START": seconds_val
            },
            "CUSTOM_ICON": {
                "ENABLED": self.var_custom_icon_enabled.get(),
                "URL": self.var_custom_icon_url.get().strip(),
                "TEXT": self.var_custom_icon_text.get().strip()
            },
            "BLACKLIST": list(self.blacklist_list),
            "WHITELIST": list(self.whitelist_list)
        }
        return config_out

    def save_configuration(self):
        """Saves current GUI inputs to config.json with safety backup."""
        data = self.collect_config_dict()

        # Validation
        if not data["STEAM_API_KEY"]:
            messagebox.showwarning("Incomplete Configuration", "Steam Web API Key is blank. You will need to fill this before running Steam Presence.")
        if not data["USER_IDS"]:
            messagebox.showwarning("Incomplete Configuration", "Steam User ID is blank. Please enter your 17-digit SteamID64.")

        try:
            if os.path.exists(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, BACKUP_PATH)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            self._set_toast("✓ Configuration saved to config.json (backup: config.json.bak)")
            self._append_log("Configuration saved successfully to config.json.", "success")
            messagebox.showinfo("Success", "Configuration successfully saved to config.json!\n\nA backup of the previous config was saved to config.json.bak.")
            self.lbl_config_badge.config(text="✓ Saved to config.json", fg=self.colors["badge_fg"])

            if self.process is not None and self.process.poll() is None:
                if messagebox.askyesno("Restart Presence?", "Steam Presence is currently running. Do you want to restart it to apply the new settings immediately?"):
                    self.restart_process()

        except Exception as e:
            messagebox.showerror("Error Saving", f"Failed to save config.json: {e}")
            self._append_log(f"Error saving config.json: {e}", "error")

    # ----------------------------------------------------
    # LIST MANAGERS
    # ----------------------------------------------------
    def _add_local_game(self):
        val = self.entry_add_process.get().strip()
        if val and val not in self.local_games_list:
            self.local_games_list.append(val)
            self.listbox_local_games.insert(tk.END, val)
            self.entry_add_process.delete(0, tk.END)

    def _remove_local_game(self):
        sel = self.listbox_local_games.curselection()
        if sel:
            idx = sel[0]
            val = self.listbox_local_games.get(idx)
            if val in self.local_games_list:
                self.local_games_list.remove(val)
            self.listbox_local_games.delete(idx)

    def _add_blacklist(self):
        val = self.entry_bl.get().strip()
        if val and val not in self.blacklist_list:
            self.blacklist_list.append(val)
            self.listbox_blacklist.insert(tk.END, val)
            self.entry_bl.delete(0, tk.END)

    def _remove_blacklist(self):
        sel = self.listbox_blacklist.curselection()
        if sel:
            idx = sel[0]
            val = self.listbox_blacklist.get(idx)
            if val in self.blacklist_list:
                self.blacklist_list.remove(val)
            self.listbox_blacklist.delete(idx)

    def _add_whitelist(self):
        val = self.entry_wl.get().strip()
        if val and val not in self.whitelist_list:
            self.whitelist_list.append(val)
            self.listbox_whitelist.insert(tk.END, val)
            self.entry_wl.delete(0, tk.END)

    def _remove_whitelist(self):
        sel = self.listbox_whitelist.curselection()
        if sel:
            idx = sel[0]
            val = self.listbox_whitelist.get(idx)
            if val in self.whitelist_list:
                self.whitelist_list.remove(val)
            self.listbox_whitelist.delete(idx)

    def _toggle_show_api_key(self):
        if self.entry_steam_key.cget("show") == "":
            self.entry_steam_key.config(show="*")
            self.btn_toggle_key.config(text="👁 Show")
        else:
            self.entry_steam_key.config(show="")
            self.btn_toggle_key.config(text="🔒 Hide")

    def _show_running_processes_dialog(self):
        """Displays dialog of active OS processes using psutil for convenient selection."""
        if not HAS_PSUTIL:
            messagebox.showinfo("psutil Required", "psutil module is not installed.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Select Running Process")
        dialog.geometry("450x500")
        dialog.configure(bg=self.colors["window_bg"])
        dialog.transient(self.root)

        tk.Label(
            dialog,
            text="Select an active process to monitor:",
            bg=self.colors["window_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10, "bold")
        ).pack(padx=12, pady=(10, 4), anchor="w")

        search_frame = tk.Frame(dialog, bg=self.colors["window_bg"])
        search_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(search_frame, text="Filter:", bg=self.colors["window_bg"], fg=self.colors["text_secondary"]).pack(side="left", padx=(0, 4))
        var_filter = tk.StringVar()
        entry_filter = self._create_entry(search_frame, var_filter)
        entry_filter.pack(side="left", fill="x", expand=True)

        lb_frame = tk.Frame(dialog, bg=self.colors["window_bg"])
        lb_frame.pack(fill="both", expand=True, padx=12, pady=6)

        proc_listbox = self._create_listbox(lb_frame, height=12)
        proc_listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=proc_listbox.yview)
        sb.pack(side="right", fill="y")
        proc_listbox.config(yscrollcommand=sb.set)

        procs = sorted(list(set(p.name() for p in psutil.process_iter() if p.name())))

        def update_list(*_):
            pattern = var_filter.get().lower()
            proc_listbox.delete(0, tk.END)
            for p in procs:
                if pattern in p.lower():
                    proc_listbox.insert(tk.END, p)

        var_filter.trace_add("write", update_list)
        update_list()

        def add_selected():
            sel = proc_listbox.curselection()
            if sel:
                proc_name = proc_listbox.get(sel[0])
                if proc_name not in self.local_games_list:
                    self.local_games_list.append(proc_name)
                    self.listbox_local_games.insert(tk.END, proc_name)
                dialog.destroy()

        btn_row = tk.Frame(dialog, bg=self.colors["window_bg"])
        btn_row.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_row, text="Add Selected Process", fg=self.colors["btn_fg"], relief="groove", font=("Segoe UI", 10, "bold"), command=add_selected).pack(side="right", padx=4)
        tk.Button(btn_row, text="Cancel", fg=self.colors["btn_fg"], relief="groove", command=dialog.destroy).pack(side="right")

    # ----------------------------------------------------
    # CONNECTION TESTING
    # ----------------------------------------------------
    def _test_steam_connection_live(self):
        """Asynchronously tests Steam API Key and User ID."""
        key = self.var_steam_api_key.get().strip()
        user_ids = self.var_user_ids.get().strip()

        if not key or not user_ids:
            messagebox.showwarning("Missing Credentials", "Please enter both Steam Web API Key and Steam User ID before testing.")
            return

        first_id = user_ids.split(",")[0].strip()
        self._append_log(f"Testing Steam Web API connection for SteamID: {first_id}...", "info")

        def run_test():
            if not HAS_REQUESTS:
                self.log_queue.put(("requests module not installed.", "error"))
                return
            try:
                url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={key}&format=json&steamids={first_id}"
                r = requests.get(url, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    players = data.get("response", {}).get("players", [])
                    if players:
                        p = players[0]
                        p_name = p.get("personaname", "Unknown")
                        game = p.get("gameextrainfo", "None (Offline or Idle)")
                        msg = f"✓ Success! Steam Persona: '{p_name}' | Playing: '{game}'"
                        self.log_queue.put((msg, "success"))
                        self.root.after(0, lambda: self.var_status_account.set(f"{p_name} ({first_id})"))
                        self.root.after(0, lambda: self.var_status_game.set(game))
                        self.root.after(0, lambda: messagebox.showinfo("Connection Verified", f"Steam API connection successful!\n\nAccount: {p_name}\nCurrent Game: {game}"))
                    else:
                        self.log_queue.put((f"Steam returned no player info for SteamID {first_id}. Verify ID format.", "error"))
                        self.root.after(0, lambda: messagebox.showerror("Account Not Found", f"No player details found for {first_id}."))
                elif r.status_code == 403:
                    self.log_queue.put(("Steam API returned 403 Forbidden. Check your Steam Web API Key.", "error"))
                    self.root.after(0, lambda: messagebox.showerror("Invalid API Key", "Steam returned 403 Forbidden. Please verify your API Key."))
                else:
                    self.log_queue.put((f"Steam API returned HTTP {r.status_code}.", "error"))
            except Exception as e:
                self.log_queue.put((f"Steam connection test error: {e}", "error"))

        threading.Thread(target=run_test, daemon=True).start()

    # ----------------------------------------------------
    # PROCESS MANAGEMENT (START, STOP, RESTART, LOGS)
    # ----------------------------------------------------
    def start_process(self):
        """Launches main.py using the project's venv python or sys.executable."""
        if self.process is not None and self.process.poll() is None:
            messagebox.showinfo("Already Running", "Steam Presence is already running.")
            return

        data = self.collect_config_dict()
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self._append_log(f"Warning: could not auto-save config before start: {e}", "error")

        venv_py = os.path.join(BASE_DIR, "venv", "bin", "python")
        if not os.path.exists(venv_py):
            venv_py = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
        if not os.path.exists(venv_py):
            venv_py = sys.executable

        main_script = os.path.join(BASE_DIR, "main.py")
        if not os.path.exists(main_script):
            messagebox.showerror("Error", f"main.py not found in {BASE_DIR}")
            return

        self._append_log(f"Starting Steam Presence process ({venv_py} main.py)...", "info")

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self.process = subprocess.Popen(
                [venv_py, main_script],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            self.active_pid = self.process.pid
            self.var_status_indicator.set(f"🟢 Running (PID {self.active_pid})")
            self.lbl_proc_status.config(fg=self.colors["success"])
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.notebook.select(self.tab_control)

            threading.Thread(target=self._stream_process_output, args=(self.process,), daemon=True).start()

        except Exception as e:
            messagebox.showerror("Execution Failed", f"Could not launch process: {e}")
            self._append_log(f"Execution error: {e}", "error")

    def _stream_process_output(self, proc: subprocess.Popen):
        """Reads stdout from the running process and pipes to queue."""
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    self.log_queue.put((line.rstrip(), "raw"))
            proc.stdout.close()
            return_code = proc.wait()
            self.log_queue.put((f"Process terminated with exit code {return_code}", "info"))
        except Exception as e:
            self.log_queue.put((f"Output reader error: {e}", "error"))
        finally:
            self.log_queue.put(("__PROCESS_STOPPED__", "control"))

    def stop_process(self):
        """Stops the running main.py process."""
        if self.process is None or self.process.poll() is not None:
            self.var_status_indicator.set("🔴 Stopped")
            self.lbl_proc_status.config(fg=self.colors["danger"])
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            return

        self._append_log(f"Stopping Steam Presence (PID: {self.active_pid})...", "info")
        try:
            self.process.terminate()
            threading.Thread(target=self._wait_and_kill, args=(self.process,), daemon=True).start()
        except Exception as e:
            self._append_log(f"Error terminating process: {e}", "error")

    def _wait_and_kill(self, proc: subprocess.Popen):
        try:
            proc.wait(timeout=2.5)
        except subprocess.TimeoutExpired:
            self.log_queue.put(("Process did not exit cleanly; forcing kill...", "error"))
            try:
                proc.kill()
            except Exception:
                pass

    def restart_process(self):
        """Restarts the running process."""
        self._append_log("Restarting Steam Presence...", "info")
        if self.process is not None and self.process.poll() is None:
            self.stop_process()
            self.root.after(1200, self.start_process)
        else:
            self.start_process()

    def _process_log_queue(self):
        """Pulls log items from the queue and inserts them into the text widget."""
        while not self.log_queue.empty():
            try:
                text, kind = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "control" and text == "__PROCESS_STOPPED__":
                self.process = None
                self.active_pid = None
                self.var_status_indicator.set("🔴 Stopped")
                self.lbl_proc_status.config(fg=self.colors["danger"])
                self.btn_start.config(state="normal")
                self.btn_stop.config(state="disabled")
                continue

            self._append_log(text, kind)

        self.root.after(100, self._process_log_queue)

    def _append_log(self, text: str, kind: str = "raw"):
        """Formats and appends a line to the console log viewer."""
        now = datetime.now().strftime("%H:%M:%S")

        self.log_text.insert(tk.END, f"[{now}] ", "timestamp")

        if "found game" in text or "game changed, updating to" in text:
            tag = "game"
            try:
                if "'" in text:
                    g_name = text.split("'")[1]
                    self.var_status_game.set(g_name)
                elif "found game" in text:
                    g_name = text.split("found game")[1].split("played by")[0].strip()
                    self.var_status_game.set(g_name)
            except Exception:
                pass
        elif "ERROR:" in text or kind == "error":
            tag = "error"
        elif "success" in text.lower() or kind == "success":
            tag = "success"
        elif kind == "info":
            tag = "info"
        else:
            tag = "info" if kind == "info" else ""

        self.log_text.insert(tk.END, f"{text}\n", tag if tag else None)
        self.log_text.see(tk.END)

    def _clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def _set_toast(self, text: str):
        self.lbl_toast.config(text=text)
        self.root.after(5000, lambda: self.lbl_toast.config(text=""))

    def _on_closing(self):
        """Handles GUI window exit."""
        if self.process is not None and self.process.poll() is None:
            if messagebox.askyesno("Exit Steam Presence", "Steam Presence is still running in the background.\nDo you want to stop it before closing?"):
                self.stop_process()
        self.root.destroy()


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "--check-config"):
        print("Running Steam Presence GUI headless validation...")
        config, is_existing, msg = load_raw_config()
        print(f"Loaded config: existing={is_existing}, msg={msg}")
        print("Validation successful.")
        sys.exit(0)

    root = tk.Tk()
    app = SteamPresenceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
