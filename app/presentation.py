from __future__ import annotations

import streamlit as st


def apply_branding() -> None:
    """Intentional CSS requested for FleetSight's gradient application shell."""
    st.markdown(
        """
        <style>
        .stApp { background: radial-gradient(circle at 87% 2%, #17355d 0, #09111f 36%, #070d18 100%); }
        .block-container { padding-top: 1.4rem; max-width: 1500px; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #0e1b2e, #09111f); }
        [data-testid="stMetric"] { background: linear-gradient(135deg, rgba(24,41,66,.95), rgba(13,27,47,.95)); border: 1px solid #2b4264; box-shadow: 0 12px 35px rgba(0,0,0,.16); }
        .fleet-hero { padding: 1.45rem 1.6rem; margin: .2rem 0 1.25rem; border: 1px solid rgba(94,234,212,.28); border-radius: 22px; background: linear-gradient(110deg, rgba(16,45,75,.96), rgba(23,66,103,.78) 48%, rgba(19,88,101,.58)); box-shadow: 0 18px 44px rgba(0,0,0,.22); }
        .fleet-hero h1 { margin: 0; font-size: 2rem; letter-spacing: -.04em; }
        .fleet-hero p { margin: .35rem 0 0; color: #bcd1e9; font-size: 1rem; }
        .eyebrow { color: #5eead4; font-weight: 700; font-size: .77rem; letter-spacing: .12em; text-transform: uppercase; }
        .section-note { color: #98aeca; font-size: .9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, eyebrow: str = "Fleet command center") -> None:
    st.markdown(f'<div class="fleet-hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def status_badge(status: str) -> None:
    value = str(status).lower()
    color = "green" if value in {"available", "healthy", "inside", "completed"} else "orange" if value in {"rented", "watch", "warning", "idle"} else "red" if value in {"overdue", "critical", "outside", "maintenance"} else "blue"
    st.badge(str(status).title(), color=color)
