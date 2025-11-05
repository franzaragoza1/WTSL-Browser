# tennis_dashboard.py
# ----------------------------------------------------
# 🎾 WTSL Stats - Professional Tennis Player Dashboard
# ----------------------------------------------------

import json
import pandas as pd
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import quote_plus, parse_qs, unquote_plus
import os # Añadido para la ruta del JSON en Render

# ------------------ DATA LOADING ------------------
# Arregla la ruta para que Render encuentre el JSON
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Corregimos los datos: "Unknown" ahora es "Left" (Zurdo)
df = pd.DataFrame(data).drop_duplicates(subset=["name"]).reset_index(drop=True)
df["hand"] = df["hand"].fillna("Unknown").replace({
    "L": "Left", "R": "Right",
    "U": "Left", # U (Unknown) -> Left
    "LeftHanded": "Left", "RightHanded": "Right",
    "left": "Left", "right": "Right",
    "unknown": "Left", # unknown -> Left
    "Unknown": "Left", # "Unknown" string -> Left
    "Diestro": "Right",
    "Zurdo": "Left"
})


# ------------------ LABELS ------------------
LABELS = {
    "name": "Player Name",
    "style": "Play Style",
    "height": "Height (cm)",
    "weight": "Weight (kg)",
    "hand": "Dominant Hand",
    "fh_power": "Forehand Power",
    "fh_consistency": "Forehand Consistency",
    "fh_precision": "Forehand Precision",
    "bh_power": "Backhand Power",
    "bh_consistency": "Backhand Consistency",
    "bh_precision": "Backhand Precision",
    "fh_volley": "Forehand Volley",
    "bh_volley": "Backhand Volley",
    "smash": "Smash",
    "net_presence": "Net Presence",
    "srv_power": "Service Power",
    "srv_consistency": "Service Consistency",
    "srv_precision": "Service Precision",
    "focus": "Focus",
    "counter": "Counter Skill",
    "lob": "Lob Skill",
    "dropshot": "Dropshot Skill",
    "topspin": "Topspin Skill",
    "speed": "Speed",
    "stamina": "Stamina",
    "tonicity": "Muscle Tone",
    "tal_slice_serve": "Slice Serve",
    "tal_topspin_serve": "Topspin Serve",
    "tal_twist_serve": "Twist Serve",
    "tal_slice_mastery": "Slice Mastery",
    "tal_slider": "Slider",
    "tal_boom_server": "Boom Boom Server",
    "tal_ball_feeling": "Ball Feeling",
    "tal_spinny_bh": "Spinny Backhand",
    "tal_flat_bh": "Flat Backhand"
}

# ------------------ GROUPS ------------------
GROUPS = {
    "Rally": ["fh_power", "fh_consistency", "fh_precision",
              "bh_power", "bh_consistency", "bh_precision"],
    "Volley": ["fh_volley", "bh_volley", "smash", "net_presence"],
    "Serve": ["srv_power", "srv_consistency", "srv_precision"],
    "Special": ["focus", "counter", "lob", "dropshot", "topspin"],
    "Physique": ["speed", "stamina", "tonicity"],
    "Talents": ["tal_slice_serve", "tal_topspin_serve", "tal_twist_serve",
                "tal_slice_mastery", "tal_slider", "tal_boom_server",
                "tal_ball_feeling", "tal_spinny_bh", "tal_flat_bh"]
}

# ------------------ HELPERS ------------------
def talent_to_stars(val, max_one=False):
    try:
        v = int(val)
    except Exception:
        v = 0
    if max_one:
        v = min(v, 1)
    else:
        if v > 2: v = 2
        
    return "—" if v == 0 else "⭐" * v


# ------------------ APP ------------------
# Usamos BOOTSTRAP solo como base para la estructura
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "WTSL Stats"
server = app.server # Añadido para que Gunicorn (Render) funcione


# ------------------ LAYOUT ------------------
app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dcc.Location(id="url", refresh=False),

    dbc.Row([
        # -------- SIDEBAR (en una Card) --------
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H3("🎾 WTSL Stats", className="text-center mb-3"),
                    html.Hr(),

                    html.Label("Search Player:", className="fw-bold"),
                    dcc.Input(id="search", type="text", placeholder="Enter name...", className="form-control mb-3"),

                    html.Label("Filter by Play Style:", className="fw-bold"),
                    dcc.Dropdown(
                        options=[{"label": s, "value": s} for s in sorted(df["style"].dropna().unique())],
                        id="style-filter",
                        placeholder="Select style",
                        className="mb-3"
                    ),

                    html.Label("Filter by Dominant Hand:", className="fw-bold"),
                    dcc.Dropdown(
                        options=[{"label": s, "value": s} for s in sorted(df["hand"].dropna().unique())],
                        id="hand-filter",
                        placeholder="Select hand",
                        className="mb-3"
                    ),

                    html.Label("Min. Speed:", className="fw-bold"),
                    dcc.Slider(0, 100, 1, value=0, marks=None,
                               tooltip={"always_visible": True}, id="speed-filter", className="mb-4"),

                    html.Label("Player List:", className="fw-bold"),
                    html.Div(id="player-list", style={
                        "maxHeight": "400px", "overflowY": "scroll", "borderRadius": "6px",
                        "padding": "8px"
                    }),
                ]),
            ),
            width=3, className="h-100"
        ),

        # -------- MAIN CONTENT (en una Card) --------
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    # CORRECCIÓN: Usamos dbc.Tabs en lugar de dcc.Tabs
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Overview", tab_id="overview"),
                            dbc.Tab(label="Rally", tab_id="rally"),
                            dbc.Tab(label="Volley", tab_id="volley"),
                            dbc.Tab(label="Serve", tab_id="serve"),
                            dbc.Tab(label="Special", tab_id="special"),
                            dbc.Tab(label="Physique", tab_id="physique"),
                            dbc.Tab(label="Talents", tab_id="talents"),
                            dbc.Tab(label="Compare", tab_id="compare"),
                        ],
                        id="tabs",
                        active_tab="overview", # Propiedad correcta es 'active_tab'
                        className="mb-3",
                    ),
                    html.Div(id="tab-content")
                ])
            ),
            width=9
        )
    ], className="mt-3")
])

# ------------------ CALLBACKS ------------------

# Player list sidebar
@app.callback(
    Output("player-list", "children"),
    Input("search", "value"),
    Input("style-filter", "value"),
    Input("hand-filter", "value"),
    Input("speed-filter", "value")
)
def update_player_list(search, style, hand, min_speed):
    players = df.copy()
    if search:
        players = players[players["name"].str.contains(search, case=False, na=False)]
    if style:
        players = players[players["style"] == style]
    if hand:
        players = players[players["hand"] == hand]
    if min_speed:
        players = players[players["speed"] >= min_speed]
    players = players.sort_values("name")

    if players.empty:
        return html.Div("No players found.", className="text-muted")

    links = []
    for _, row in players.iterrows():
        url = "/?player=" + quote_plus(row["name"])
        links.append(
            html.A(
                row["name"],
                href=url,
                className="player-list-link"
            )
        )
    return links

# CSS personalizado con la nueva paleta y corrección de pestañas
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>WTSL Stats</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --c1-blue-black: #021C1E;
                --c2-cadet-blue: #004445;
                --c3-rain: #2C7873;
                --c4-greenery: #6FB98F;
                --text-primary: #FFFFFF;
                --text-secondary: #aaaaaa;
            }

            body {
                font-family: 'Inter', 'Open Sans', sans-serif;
                background-color: var(--c1-blue-black);
                color: var(--text-primary);
                margin: 0;
            }
            
            /* Estilo de las tarjetas (Sidebar y Main) */
            .card, .card-body {
                background-color: var(--c2-cadet-blue);
                border: 1px solid var(--c3-rain);
                color: var(--text-primary);
            }

            /* Títulos y etiquetas en acento */
            h3, h4, .fw-bold {
                color: var(--c4-greenery);
                font-weight: 600;
            }
            hr {
                border-top: 1px solid var(--c3-rain);
                opacity: 0.5;
            }

            /* Contenedor de lista de jugadores */
            #player-list {
                background-color: rgba(2, 28, 30, 0.5); /* c1-blue-black con 50% alpha */
            }

            /* Enlaces de jugador */
            .player-list-link {
                display: block;
                padding: 8px;
                border-radius: 4px;
                text-decoration: none;
                color: var(--text-primary);
                background-color: var(--c3-rain);
                margin-bottom: 6px;
                border: 1px solid var(--c3-rain);
                transition: background-color 0.2s, color 0.2s;
            }
            .player-list-link:hover {
                background-color: var(--c4-greenery);
                color: var(--c1-blue-black); /* Texto oscuro sobre fondo claro */
                font-weight: 600;
            }

            /* Inputs y Dropdowns */
            .form-control, .Select-control {
                background-color: var(--c1-blue-black);
                color: var(--text-primary);
                border: 1px solid var(--c3-rain);
            }
            .form-control:focus {
                background-color: var(--c1-blue-black);
                color: var(--text-primary);
                border-color: var(--c4-greenery);
                box-shadow: 0 0 0 0.2rem rgba(111, 185, 143, 0.25);
            }
            .Select-value-label, .Select-placeholder {
                color: var(--text-primary) !important;
            }
            .Select-menu-outer, .VirtualizedSelectOption {
                background-color: var(--c2-cadet-blue);
                color: var(--text-primary);
            }
            .VirtualizedSelectFocusedOption {
                background-color: var(--c3-rain);
            }

            /* CORRECCIÓN PESTAÑAS (dbc.Tabs) */
            .nav-tabs {
                border-bottom: 1px solid var(--c3-rain);
            }
            .nav-tabs .nav-link {
                /* Estilo de pestañas inactivas */
                color: var(--text-secondary); /* Texto claro (gris) */
                background-color: var(--c2-cadet-blue); /* Fondo oscuro */
                border: 1px solid var(--c3-rain);
                margin-right: 2px;
            }
            .nav-tabs .nav-link:hover {
                /* Inactiva al pasar el ratón */
                color: var(--text-primary);
                background-color: var(--c3-rain);
                border-color: var(--c4-greenery);
            }
            .nav-tabs .nav-link.active {
                /* Pestaña activa */
                color: var(--c1-blue-black); /* Texto oscuro */
                background-color: var(--c4-greenery); /* Fondo acento */
                border-color: var(--c4-greenery);
                font-weight: 600;
            }

            .text-muted {
                color: var(--c3-rain) !important;
                opacity: 0.9;
            }

            /* Estilo de Tablas */
            .table {
                color: var(--text-primary);
                border-color: var(--c3-rain);
            }
            .table > :not(caption) > * > * {
                background-color: transparent;
                color: var(--text-primary);
                border-bottom-width: 1px;
                border-color: var(--c3-rain);
            }
            .table-striped > tbody > tr:nth-of-type(odd) {
                --bs-table-accent-bg: rgba(2, 28, 30, 0.5); /* c1-blue-black 50% */
                color: var(--text-primary);
            }
            .table-hover > tbody > tr:hover {
                --bs-table-accent-bg: rgba(111, 185, 143, 0.2); /* c4-greenery 20% */
                color: var(--text-primary);
            }

        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Main content area
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"), # CORRECCIÓN: 'value' -> 'active_tab'
    Input("url", "search")
)
def render_tabs(tab, search):
    player_name = None
    if search:
        qs = parse_qs(search.lstrip("?"))
        if "player" in qs and qs["player"]:
            player_name = unquote_plus(qs["player"][0])

    if not player_name:
        return html.Div("Select a player from the list.", className="text-muted p-3")

    matches = df[df["name"] == player_name]
    if matches.empty:
        return html.Div(f"Player '{player_name}' not found.", className="text-danger p-3")
    p = matches.iloc[0]

    graph_template = "plotly_dark"
    accent_color = "#6FB98F" # c4-greenery

    if tab == "overview":
        radar_attrs = ["fh_power", "bh_power", "srv_power", "speed", "stamina", "focus"]
        radar_vals = [p.get(a, 0) for a in radar_attrs]
        radar_df = pd.DataFrame({"Attribute": [LABELS[a] for a in radar_attrs], "Value": radar_vals})
        
        radar = px.line_polar(radar_df, r="Value", theta="Attribute", line_close=True, template=graph_template)
        radar.update_traces(fill="toself", line_color=accent_color)
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False)),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)") 

        return html.Div([
            html.H4(f"{p['name']} — Overview", className="mb-3"),
            html.P(f"Play Style: {p['style']} | Hand: {p['hand']} | Height: {p['height']} cm | Weight: {p['weight']} kg"),
            dcc.Graph(figure=radar)
        ])

    if tab in ["rally", "volley", "serve", "special", "physique"]:
        section = tab.capitalize()
        rows = []
        for key in GROUPS[section]:
            rows.append(html.Tr([html.Td(LABELS[key]), html.Td(p.get(key, "—"))]))
        return html.Div([
            html.H4(f"{p['name']} — {section}"),
            dbc.Table(rows, bordered=True, striped=True, hover=True, className="mt-2")
        ])

    if tab == "talents":
        talents = []
        for key in GROUPS["Talents"]:
            val = talent_to_stars(p.get(key, 0), max_one=False)
            talents.append(html.Tr([html.Td(LABELS[key]), html.Td(val)]))
        return html.Div([
            html.H4(f"{p['name']} — Talents"),
            dbc.Table(talents, bordered=True, striped=True, hover=True, className="mt-2")
        ])

    if tab == "compare":
        return html.Div([
            html.H4("Player Comparison", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Player A:", className="fw-bold"),
                    dcc.Dropdown(
                        id="compare-a", options=[{"label": n, "value": n} for n in df["name"]],
                        value=p["name"], className="mb-3"
                    )
                ]),
                dbc.Col([
                    html.Label("Player B:", className="fw-bold"),
                    dcc.Dropdown(
                        id="compare-b", options=[{"label": n, "value": n} for n in df["name"]],
                        placeholder="Select another player", className="mb-3"
                    )
                ])
            ]),
            html.Div(id="compare-output")
        ])

    return html.Div("Invalid tab.")


@app.callback(
    Output("compare-output", "children"),
    Input("compare-a", "value"),
    Input("compare-b", "value")
)
def compare_players(a, b):
    if not a or not b:
        return html.Div("Select two players to compare.", className="text-muted")
    p1, p2 = df[df["name"] == a].iloc[0], df[df["name"] == b].iloc[0]

    radar_attrs = ["fh_power", "bh_power", "srv_power", "speed", "stamina", "focus"]
    df1 = pd.DataFrame({"Attribute": [LABELS[a] for a in radar_attrs], "Value": [p1.get(a, 0) for a in radar_attrs], "Player": a})
    df2 = pd.DataFrame({"Attribute": [LABELS[a] for a in radar_attrs], "Value": [p2.get(a, 0) for a in radar_attrs], "Player": b})
    comp_df = pd.concat([df1, df2])

    radar = px.line_polar(comp_df, r="Value", theta="Attribute", color="Player", line_close=True, template="plotly_dark")
    radar.update_traces(fill="toself", opacity=0.7)
    radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False)),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        legend_title_text="") 

    table_rows = []
    for attr in radar_attrs:
        table_rows.append(html.Tr([
            html.Td(LABELS[attr]),
            html.Td(p1.get(attr, "—")),
            html.Td(p2.get(attr, "—"))
        ]))

    table = dbc.Table(
        [html.Thead(html.Tr([html.Th("Attribute"), html.Th(a), html.Th(b)]))] + table_rows,
        bordered=True, striped=True, hover=True, className="mt-3"
    )

    return html.Div([dcc.Graph(figure=radar), table])


# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)
