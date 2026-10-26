"""레포 안의 정적 콘텐츠(content/profile.yaml)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "content" / "profile.yaml"


@st.cache_data(show_spinner=False)
def load_profile() -> dict:
    with PROFILE_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("links", [])
    data.setdefault("interests", [])
    data.setdefault("education", [])
    data.setdefault("career", [])
    return data


def photo_path() -> Path | None:
    p = load_profile().get("photo")
    if not p:
        return None
    path = ROOT / p
    return path if path.exists() else None
