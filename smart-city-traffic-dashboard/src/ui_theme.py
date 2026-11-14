"""Shared dark "glassmorphism" styling helpers for pages (needs Streamlit)."""

import streamlit as st

CYAN, BLUE, AMBER, RED, GREEN = "#00e5ff", "#3d8bff", "#ffb020", "#ff4d6d", "#66e08a"
VIOLET, PINK = "#b388ff", "#ff6ec7"
TEXT, MUTED = "#e6f1ff", "#8fa3c2"

TAGS = {"REAL": "real", "ESTIMATED": "est", "SIMULATED": "sim"}


def inject_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; }}
.stApp {{
    color-scheme: dark; color:{TEXT};
    background:
      radial-gradient(1100px 600px at 12% -10%, rgba(0,229,255,0.14), transparent 60%),
      radial-gradient(900px 600px at 100% 0%, rgba(61,139,255,0.16), transparent 55%),
      linear-gradient(180deg,#050b1a 0%,#030712 100%);
}}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:2rem; padding-bottom:3rem; max-width:1400px; }}
.stApp p, .stApp label, .stApp li, .stApp span {{ color:{TEXT}; }}
[data-testid="stWidgetLabel"] p {{ color:{MUTED}; font-weight:600; letter-spacing:.04em;
    text-transform:uppercase; font-size:.72rem; }}
[data-testid="stSidebar"] {{
    background:linear-gradient(180deg,rgba(8,18,40,.96),rgba(3,7,18,.98));
    border-right:1px solid rgba(0,229,255,0.15);
}}
.nav-title {{ color:{MUTED}; font-size:.7rem; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; margin:1rem 0 .4rem 0; }}
.hero-title {{ font-size:2.1rem; font-weight:800; letter-spacing:-.02em; margin:0;
    background:linear-gradient(90deg,#fff 0%,{CYAN} 60%,{BLUE} 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent !important; }}
.hero-sub {{ color:{MUTED}; margin:.3rem 0 .9rem 0; }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:.7rem;
    font-weight:700; letter-spacing:.06em; margin-right:.4rem; margin-bottom:.3rem; }}
.badge.real {{ background:rgba(46,125,50,.18); color:{GREEN}; border:1px solid rgba(102,224,138,.5); }}
.badge.est {{ background:rgba(61,139,255,.14); color:{BLUE}; border:1px solid rgba(61,139,255,.5); }}
.badge.sim {{ background:rgba(255,176,32,.14); color:{AMBER}; border:1px solid rgba(255,176,32,.45); }}
.badge.notlive {{ background:rgba(255,77,109,.12); color:{RED}; border:1px solid rgba(255,77,109,.45); }}
.glass {{
    background:rgba(255,255,255,0.045); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
    border:1px solid rgba(0,229,255,0.18); border-radius:18px; padding:1.05rem 1.2rem;
    box-shadow:0 8px 32px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
}}
.kpi-label {{ color:{MUTED}; font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }}
.kpi-value {{ font-size:1.9rem; font-weight:800; margin:.3rem 0 .1rem 0; line-height:1.1; }}
.kpi-sub {{ color:{MUTED}; font-size:.8rem; }}
.tag {{ display:inline-block; margin-top:.5rem; font-size:.62rem; font-weight:800; letter-spacing:.08em;
    border-radius:6px; padding:1px 7px; }}
.tag.real {{ color:{GREEN}; background:rgba(46,125,50,.18); border:1px solid rgba(102,224,138,.45); }}
.tag.est {{ color:{BLUE}; background:rgba(61,139,255,.14); border:1px solid rgba(61,139,255,.45); }}
.tag.sim {{ color:{AMBER}; background:rgba(255,176,32,.12); border:1px solid rgba(255,176,32,.4); }}
.section-title {{ font-size:1.1rem; font-weight:700; margin:1.4rem 0 .2rem 0; }}
.section-note {{ color:{MUTED}; font-size:.82rem; margin-bottom:.6rem; }}
.notice {{ border-left:4px solid {AMBER}; background:rgba(255,176,32,.08); border-radius:10px;
    padding:.7rem 1rem; font-size:.88rem; margin:.4rem 0 1rem 0; }}
.legend {{ display:flex; flex-wrap:wrap; gap:.4rem 1.4rem; font-size:.82rem; align-items:center; }}
.swatch {{ display:inline-block; width:26px; height:5px; border-radius:3px; margin-right:.45rem; vertical-align:middle; }}
@media (max-width:768px) {{
  .hero-title {{ font-size:1.5rem; }} .kpi-value {{ font-size:1.5rem; }}
  .block-container {{ padding-left:1rem; padding-right:1rem; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str, colour: str, tag: str) -> str:
    """HTML for one glass KPI card. tag is REAL, ESTIMATED or SIMULATED."""
    return (
        f"<div class='glass'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value' style='color:{colour}'>{value}</div>"
        f"<div class='kpi-sub'>{sub}</div>"
        f"<span class='tag {TAGS[tag]}'>{tag}</span></div>"
    )


def style_figure(fig, height: int = 340):
    """Transparent dark look for every Plotly chart."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT),
        margin=dict(l=10, r=10, t=44, b=10), height=height, title=dict(font=dict(size=15)),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig
