from __future__ import annotations

# まるたいスタンプラリー / アプリの処理はこの1ファイルに集約
import csv
import hmac
import logging
import math
import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Callable, Iterable, Literal
from urllib.parse import quote
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import folium
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_folium import st_folium
from supabase import create_client

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
STAMP_PATH = ASSET_DIR / "tai_stamp.png"
BUCKET = "visit-photos"
LOGGER = logging.getLogger("marutai")

CSS = r"""
<style>
:root {
  color-scheme: light !important;
  --marutai-red:#d9362b;
  --marutai-red-soft:#fff0ed;
  --marutai-navy:#173a5e;
  --marutai-navy-2:#244f78;
  --marutai-cream:#fffaf0;
  --marutai-paper:#f7f0df;
  --marutai-white:#ffffff;
  --marutai-border:#e7dcc7;
  --marutai-blue:#dceef5;
  --marutai-muted:#6b7785;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  color-scheme: light !important;
  background-color:var(--marutai-cream) !important;
  color:var(--marutai-navy) !important;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 14% 7%, rgba(166,210,227,.14) 0 32px, transparent 33px),
    linear-gradient(180deg, #fffdf8 0%, var(--marutai-cream) 100%) !important;
}
[data-testid="stHeader"] { background:rgba(255,253,248,.96) !important; height:2.25rem; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { background:transparent !important; }
[data-testid="stSidebar"], [data-testid="stSidebarNav"] { display:none !important; }
.block-container {
  max-width:760px;
  padding-top:.35rem !important;
  padding-bottom:8.5rem !important;
}

/* Typography: never place white body text on cream */
.stApp, .stApp p, .stApp li, .stApp label,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
  color:var(--marutai-navy) !important;
}
h1,h2,h3,h4,h5,h6 {
  color:var(--marutai-navy) !important;
  letter-spacing:.01em;
}
h1 { margin-top:.15rem !important; margin-bottom:.55rem !important; }
h2,h3 { margin-top:.65rem !important; margin-bottom:.45rem !important; }
[data-testid="stCaptionContainer"] { color:#516982 !important; }
small { color:#516982 !important; }
hr { border-color:var(--marutai-border) !important; }

/* Buttons */
.stButton > button, .stLinkButton > a {
  min-height:48px;
  border-radius:15px !important;
  border:1px solid var(--marutai-border) !important;
  font-weight:800 !important;
  font-size:1rem !important;
  color:var(--marutai-navy) !important;
  background:var(--marutai-white) !important;
  box-shadow:0 2px 8px rgba(57,43,20,.05) !important;
}
.stButton > button:hover, .stLinkButton > a:hover {
  border-color:#d9a59f !important;
  background:#fff8f6 !important;
  color:var(--marutai-navy) !important;
}
.stButton > button[kind="primary"] {
  background:var(--marutai-red) !important;
  color:#fff !important;
  border-color:var(--marutai-red) !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span { color:#fff !important; }

/* Streamlit form widgets: force light appearance even when device/browser is dark */
[data-baseweb="input"], [data-baseweb="base-input"],
[data-baseweb="select"] > div, [data-baseweb="select"] input,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stTextInput"] [data-baseweb="input"] {
  background:var(--marutai-white) !important;
  color:var(--marutai-navy) !important;
  border-color:var(--marutai-border) !important;
}
[data-baseweb="input"] input, [data-baseweb="base-input"] input,
[data-baseweb="select"] input, [data-testid="stTextInput"] input {
  color:var(--marutai-navy) !important;
  -webkit-text-fill-color:var(--marutai-navy) !important;
  background:transparent !important;
}
input::placeholder, textarea::placeholder {
  color:#8a929b !important;
  -webkit-text-fill-color:#8a929b !important;
  opacity:1 !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div,
[data-testid="stSelectbox"] span, [data-testid="stMultiSelect"] span {
  color:var(--marutai-navy) !important;
}
[data-baseweb="tag"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-navy) !important;
  border:1px solid #efc3bd !important;
}
[data-baseweb="tag"] span { color:var(--marutai-navy) !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
  background:var(--marutai-white) !important;
  color:var(--marutai-navy) !important;
}
[role="option"] { background:var(--marutai-white) !important; color:var(--marutai-navy) !important; }
[role="option"]:hover, [role="option"][aria-selected="true"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-navy) !important;
}

/* Expander */
[data-testid="stExpander"] {
  background:rgba(255,255,255,.88) !important;
  border:1px solid var(--marutai-border) !important;
  border-radius:16px !important;
  box-shadow:none !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p,
[data-testid="stExpander"] svg { color:var(--marutai-navy) !important; fill:var(--marutai-navy) !important; }

/* Checkbox/radio */
[data-testid="stCheckbox"] label, [data-testid="stCheckbox"] p,
[data-testid="stRadio"] label, [data-testid="stRadio"] p {
  color:var(--marutai-navy) !important;
  opacity:1 !important;
}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child,
[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
  border-color:#8ea3b7 !important;
  background:#fff !important;
}
[data-testid="stCheckbox"] [aria-checked="true"] > div:first-child,
[data-testid="stRadio"] [aria-checked="true"] > div:first-child {
  background:var(--marutai-red) !important;
  border-color:var(--marutai-red) !important;
}

/* Segmented control */
[data-testid="stSegmentedControl"] { background:transparent !important; }
[data-testid="stSegmentedControl"] button {
  color:var(--marutai-navy) !important;
  background:#fff !important;
  border-color:var(--marutai-border) !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
  background:var(--marutai-red-soft) !important;
  color:var(--marutai-red) !important;
  border-color:#e7aaa3 !important;
}

/* Uploader / camera */
[data-testid="stFileUploader"], [data-testid="stCameraInput"] { color:var(--marutai-navy) !important; }
[data-testid="stFileUploaderDropzone"] {
  background:#fff !important;
  border:1px dashed #c8bca8 !important;
  border-radius:16px !important;
}
[data-testid="stFileUploaderDropzone"] * { color:var(--marutai-navy) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] > div { display:none !important; }
[data-testid="stFileUploaderDropzoneInstructions"]::before {
  content:"写真をここに追加";
  display:block;
  color:var(--marutai-navy);
  font-weight:800;
  margin-bottom:2px;
}
[data-testid="stFileUploaderDropzoneInstructions"]::after {
  content:"JPG・PNG・WEBP";
  display:block;
  color:var(--marutai-muted);
  font-size:.78rem;
}
[data-testid="stFileUploaderDropzone"] button { font-size:0 !important; }
[data-testid="stFileUploaderDropzone"] button::after {
  content:"写真を選ぶ";
  font-size:.9rem;
  color:var(--marutai-navy);
  font-weight:800;
}

/* Status boxes */
[data-testid="stAlert"] { border-radius:14px !important; }
[data-testid="stAlert"] p { color:var(--marutai-navy) !important; }

/* Brand */
.brand-fallback { display:flex; align-items:center; justify-content:center; gap:14px; margin:0 auto 10px; }
.brand-stamp {
  width:84px; height:84px; border:6px solid var(--marutai-red); border-radius:50%; color:var(--marutai-red);
  display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:900; transform:rotate(-4deg);
  box-shadow:inset 0 0 0 3px #fff9ec;
}
.brand-title { color:var(--marutai-navy); font-weight:900; font-size:29px; line-height:1.02; letter-spacing:.02em; }
.brand-sub { color:var(--marutai-navy); font-weight:700; font-size:12px; margin-top:6px; }
.hero-question { color:var(--marutai-navy); text-align:center; font-size:1.18rem; font-weight:900; margin:.25rem 0 .75rem; }
.count-card {
  margin-top:.9rem; border:1px solid var(--marutai-border); border-radius:18px; padding:15px 18px; text-align:center;
  background:linear-gradient(135deg,#fff,#f7fbff); box-shadow:0 2px 10px rgba(79,55,22,.05);
}
.count-card span { display:block; color:var(--marutai-navy); font-weight:800; }
.count-card strong { display:block; color:var(--marutai-red); font-size:2.7rem; line-height:1.05; margin-top:4px; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--marutai-border); border-radius:14px; padding:9px; }

/* Facility cards */
.facility-card {
  border:0;
  border-radius:17px;
  padding:14px 15px 11px;
  margin:.4rem 0 .18rem;
  background:rgba(255,255,255,.94);
  box-shadow:none;
}
.facility-card-title { color:var(--marutai-navy); font-weight:900; font-size:1.2rem; line-height:1.25; margin-bottom:7px; }
.facility-card-meta { color:#385672; font-size:.9rem; font-weight:700; margin-bottom:7px; }
.facility-tags { display:flex; flex-wrap:wrap; gap:6px; margin:5px 0 4px; }
.facility-tag {
  display:inline-flex; align-items:center; min-height:28px; padding:3px 9px; border-radius:999px;
  border:1px solid #d6e0e8; background:#f7fbfd; color:var(--marutai-navy); font-size:.82rem; font-weight:700;
}
.facility-tag.yes { border-color:#b8d9e5; background:#eff9fc; }
.facility-tag.no { border-color:#e2ddd4; background:#fbfaf7; color:#687889; }
.facility-status { margin-top:7px; color:var(--marutai-navy); font-weight:900; font-size:.9rem; }
.facility-status.visited { color:var(--marutai-red); }
.facility-card + div[data-testid="stButton"] button { min-height:42px !important; }

/* Detail */
.detail-summary {
  background:#fff; border:1px solid var(--marutai-border); border-radius:16px; padding:12px 14px; margin:.2rem 0 .6rem;
  color:var(--marutai-navy);
}
.detail-summary strong { color:var(--marutai-navy); }

/* Bottom navigation */
.nav-wrap {
  position:fixed; left:0; right:0; bottom:0; z-index:9999;
  background:rgba(255,253,248,.98); border-top:1px solid var(--marutai-border);
  padding:6px max(10px, env(safe-area-inset-right)) calc(8px + env(safe-area-inset-bottom)) max(10px, env(safe-area-inset-left));
  backdrop-filter:blur(9px);
}
.nav-inner { max-width:740px; margin:auto; display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }
.nav-item {
  position:relative; text-align:center; color:var(--marutai-navy) !important; text-decoration:none !important;
  font-weight:800; font-size:.79rem; padding:6px 2px 7px; border-radius:11px;
}
.nav-item.active { color:var(--marutai-red) !important; background:var(--marutai-red-soft); }
.nav-item.active::after {
  content:""; position:absolute; left:24%; right:24%; bottom:2px; height:3px; border-radius:3px; background:var(--marutai-red);
}
.nav-icon { display:block; font-size:1.35rem; line-height:1.05; margin-bottom:3px; }

.st-key-bottom_nav {
  position:fixed; left:0; right:0; bottom:0; z-index:9999;
  background:#fffdf8; border-top:1px solid var(--marutai-border);
  padding:8px 10px calc(10px + env(safe-area-inset-bottom));
}
.st-key-bottom_nav > div { max-width:740px; margin:auto; }
.st-key-bottom_nav [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:4px !important; }
.st-key-bottom_nav [data-testid="stColumn"] { min-width:0 !important; width:25% !important; flex:1 1 0 !important; }
.st-key-bottom_nav button { padding:4px !important; font-size:.75rem !important; min-height:46px; }
/* Map iframe */
[data-testid="stIFrame"] { border-radius:16px; overflow:hidden; }

@media (max-width: 640px) {
  [data-testid="stHeader"] { height:1.75rem; }
  .block-container {
    padding-left:.72rem !important;
    padding-right:.72rem !important;
    padding-top:1.1rem !important;
    padding-bottom:9.2rem !important;
  }
  h1 { font-size:1.72rem !important; line-height:1.16 !important; margin:.1rem 0 .45rem !important; }
  h2 { font-size:1.4rem !important; }
  h3 { font-size:1.12rem !important; }
  .brand-title { font-size:25px; }
  .brand-stamp { width:72px; height:72px; font-size:26px; }
  .hero-question { font-size:1.08rem; margin:.15rem 0 .6rem; }
  .stButton > button, .stLinkButton > a { min-height:46px; font-size:.95rem !important; }
  .facility-card { padding:12px 12px 10px; border-radius:15px; }
  .facility-card-title { font-size:1.1rem; }
  .facility-card-meta, .facility-status { font-size:.86rem; }
  .facility-tag { font-size:.78rem; padding:2px 8px; }
  [data-testid="stExpander"] details > div { padding-left:.6rem !important; padding-right:.6rem !important; }
  [data-testid="stVerticalBlock"] { gap:.55rem !important; }
}
</style>
"""

# ── 1. 設定・Supabase保存 ────────────────────────────────────
def setting(name: str) -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, ""))).strip()
    except FileNotFoundError:
        return os.getenv(name, "").strip()


def require_access() -> None:
    required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "APP_PASSWORD")
    missing = [name for name in required if not setting(name)]
    if missing:
        st.info("初期設定が必要です。README.mdに沿って設定してください。")
        st.code("未設定: " + ", ".join(missing))
        st.stop()
    # 家族共通の記録帳。service roleを使うため、表示前にアクセスを確認する。
    import hashlib
    token = hashlib.sha256(setting("APP_PASSWORD").encode()).hexdigest()
    if st.session_state.get("access_token") == token:
        return
    with st.form("login"):
        entered = st.text_input("合言葉", type="password")
        if st.form_submit_button("開く", width="stretch"):
            if hmac.compare_digest(entered.encode(), setting("APP_PASSWORD").encode()):
                st.session_state["access_token"] = token
                st.rerun()
            else:
                st.error("合言葉が違います。")
    st.stop()


# セッションごとにクライアントを持ち、利用者間で接続状態を共有しない。
def db():
    signature = (setting("SUPABASE_URL"), setting("SUPABASE_SERVICE_ROLE_KEY"))
    if st.session_state.get("db_signature") != signature:
        st.session_state["db_client"] = create_client(*signature)
        st.session_state["db_signature"] = signature
    return st.session_state["db_client"]


def fetch_all(table: str, columns: str = "*", *, active_only=False, order="id") -> list[dict[str, Any]]:
    rows, offset = [], 0
    # APIの既定件数で切れないよう、全ページを取得する。
    while True:
        query = db().table(table).select(columns).order(order)
        if active_only:
            query = query.eq("active", True)
        batch = query.range(offset, offset + 499).execute().data or []
        if not batch:
            return rows
        rows.extend(batch)
        offset += len(batch)


def list_facilities(active_only: bool = True) -> list[dict[str, Any]]:
    cache_key = "facilities_active" if active_only else "facilities_all"
    cache = st.session_state.setdefault("run_data", {})
    if cache_key not in cache:
        rows = fetch_all("facilities", active_only=active_only)
        cache[cache_key] = sorted(rows, key=lambda f: (f.get("ward", ""), f.get("name", "")))
    return cache[cache_key]


def get_facility(facility_id: str) -> dict[str, Any] | None:
    return next((f for f in list_facilities(False) if str(f["id"]) == str(facility_id)), None)


def list_visits() -> list[dict[str, Any]]:
    cache = st.session_state.setdefault("run_data", {})
    if "visits" not in cache:
        rows = fetch_all("visits", "*, facilities(*)")
        cache["visits"] = sorted(rows, key=lambda v: (v["visited_date"], v.get("created_at", "")), reverse=True)
    return cache["visits"]


def visits_for_facility(facility_id: str) -> list[dict[str, Any]]:
    return [v for v in list_visits() if str(v["facility_id"]) == str(facility_id)]


def visited_facility_ids() -> set[str]:
    return {str(v["facility_id"]) for v in list_visits()}


def photo_path(path: str | None):
    if not path:
        return None
    # Storageは非公開。短時間だけ有効な閲覧URLを発行する。
    result = db().storage.from_(BUCKET).create_signed_url(path, 3600)
    return result.get("signedURL") or result.get("signedUrl")


def create_visit(facility_id: str, visited_date: str, original_bytes: bytes, stamped_bytes: bytes) -> dict[str, Any]:
    visit_id = str(uuid4())
    original_path = f"original/{facility_id}/{visit_id}.jpg"
    stamped_path = f"stamped/{facility_id}/{visit_id}.jpg"
    row = dict(id=visit_id, facility_id=facility_id, visited_date=visited_date,
               original_photo_url=original_path, stamped_photo_url=stamped_path)
    bucket = db().storage.from_(BUCKET)
    uploaded = []
    try:
        for path, data in ((original_path, original_bytes), (stamped_path, stamped_bytes)):
            bucket.upload(path, data, file_options={"content-type": "image/jpeg", "upsert": "false"})
            uploaded.append(path)
        db().table("visits").insert(row).execute()
    except Exception:
        # 通信断でDBの応答だけ失われた場合は、保存済み写真を消さない。
        try:
            saved = db().table("visits").select("id").eq("id", visit_id).execute().data
        except Exception:
            LOGGER.exception("保存状態を確認できません: %s", visit_id)
            raise
        if not saved:
            if uploaded:
                try:
                    bucket.remove(uploaded)
                except Exception:
                    LOGGER.exception("未使用写真を削除できません: %s", visit_id)
            raise
    st.session_state["run_data"] = {}
    return row


def parse_facility_csv(raw: bytes) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    required = {"name", "category", "ward", "address", "latitude", "longitude"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("CSVの必須列: " + ", ".join(sorted(required)))
    rows, ids = [], set()
    def boolean(value, *, nullable=True):
        value = str(value or "").strip().lower()
        if not value and nullable:
            return None
        if value in {"true", "1", "yes", "y"}:
            return True
        if value in {"false", "0", "no", "n"}:
            return False
        raise ValueError("真偽値はtrue／false／空欄で入力してください。")
    for line, source in enumerate(reader, start=2):
        if not any(str(v or "").strip() for v in source.values()):
            continue
        row = {key: str(source.get(key) or "").strip() for key in required}
        if not row["name"] or row["category"] not in CATEGORY_LABELS:
            raise ValueError(f"{line}行目: 施設名・施設種別を確認してください。")
        raw_id = str(source.get("id") or "").strip()
        try:
            row["id"] = str(UUID(raw_id)) if raw_id else str(uuid5(NAMESPACE_URL, "marutai:" + row["name"] + ":" + row["address"]))
            for key, limit in (("latitude", 90), ("longitude", 180)):
                value = float(row[key]) if row[key] else None
                if value is not None and (not math.isfinite(value) or not -limit <= value <= limit):
                    raise ValueError("緯度・経度の範囲が不正です。")
                row[key] = value
            for key in ("has_open_air_bath", "has_natural_hot_spring"):
                row[key] = boolean(source.get(key))
            row["active"] = boolean(source.get("active") or "true", nullable=False)
        except ValueError as exc:
            raise ValueError(f"{line}行目: {exc}") from exc
        row["website_url"] = str(source.get("website_url") or "").strip()
        if row["website_url"] and not row["website_url"].startswith(("https://", "http://")):
            raise ValueError(f"{line}行目: 公式サイトはhttp(s)のURLにしてください。")
        if row["id"] in ids:
            raise ValueError(f"{line}行目: IDが重複しています。")
        ids.add(row["id"])
        rows.append(row)
    if not rows:
        raise ValueError("登録する施設がありません。")
    return rows


def render_data_settings() -> None:
    with st.expander("施設データの設定"):
        st.caption("CSVで施設を追加・更新します。同じIDの施設は更新し、CSVにない施設は残します。")
        uploaded = st.file_uploader("施設CSV", type=["csv"])
        if uploaded is not None and st.button("CSVを登録する"):
            try:
                rows = parse_facility_csv(uploaded.getvalue())
                for start in range(0, len(rows), 200):
                    db().table("facilities").upsert(rows[start:start+200], on_conflict="id").execute()
                st.success(f"{len(rows)}施設を登録しました。")
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                LOGGER.exception("施設CSV登録失敗")
                st.error("登録できませんでした。一部が登録された場合も、同じCSVで再実行できます。")
            finally:
                st.session_state["run_data"] = {}
        st.caption("同梱CSVは画面確認用のサンプル3件です。正式な施設データではありません。")
        st.download_button("CSVの形式をダウンロード", (ROOT / "data/facilities.csv").read_bytes(),
                           file_name="facilities.csv", mime="text/csv")


def feature_text(label: str, value: bool | None) -> str:
    return f"{label} 未登録" if value is None else f"{label}{'あり' if value else 'なし'}"


def facility_label(f: dict) -> str:
    name, ward = str(f.get("name", "")), str(f.get("ward", ""))
    return name if not ward or ward in name else f"{name}（{ward}）"


# ── 2. 写真・共通表示 ──
Position = Literal["top_left", "top_right", "bottom_left", "bottom_right"]


def _date_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def add_visit_stamp(
    photo_bytes: bytes,
    visited_date: str,
    position: Position = "bottom_right",
) -> bytes:
    """Return JPEG bytes with the red 'たい' stamp and visit date overlaid.

    The original input bytes are never modified. The caller stores the original and
    returned versions separately.
    """
    base = Image.open(BytesIO(photo_bytes)).convert("RGB")
    stamp = Image.open(STAMP_PATH).convert("RGBA")

    width, height = base.size
    short_side = min(width, height)
    stamp_size = max(120, int(short_side * 0.26))
    stamp.thumbnail((stamp_size, stamp_size), Image.Resampling.LANCZOS)

    pad = max(16, int(short_side * 0.035))
    date_font = _date_font(max(18, int(stamp_size * 0.11)))
    date_text = visited_date.replace("-", ".")

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_box = draw.textbbox((0, 0), date_text, font=date_font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    block_w = max(stamp.width, text_w)
    block_h = stamp.height + text_h + max(5, int(stamp_size * 0.025))

    if position == "top_left":
        x, y = pad, pad
    elif position == "top_right":
        x, y = width - block_w - pad, pad
    elif position == "bottom_left":
        x, y = pad, height - block_h - pad
    else:
        x, y = width - block_w - pad, height - block_h - pad

    stamp_x = x + (block_w - stamp.width) // 2
    overlay.alpha_composite(stamp, dest=(stamp_x, y))

    text_x = x + (block_w - text_w) // 2
    text_y = y + stamp.height + max(5, int(stamp_size * 0.025))
    # Small cream keyline keeps the date readable on dark/light photos.
    draw.text(
        (text_x, text_y),
        date_text,
        font=date_font,
        fill=(198, 41, 35, 255),
        stroke_width=max(1, int(stamp_size * 0.01)),
        stroke_fill=(255, 249, 235, 235),
    )

    result = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    out = BytesIO()
    result.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()

def render_logo(width: int = 310) -> None:
    logo = ASSET_DIR / "logo.png"
    if logo.exists():
        st.image(str(logo), width=width)
    else:
        st.markdown(
            "<div class='brand-fallback'><span class='brand-stamp'>たい</span>"
            "<div><div class='brand-title'>まるたい<br>スタンプラリー</div>"
            "<div class='brand-sub'>東京23区のおふろめぐり</div></div></div>",
            unsafe_allow_html=True,
        )

CATEGORY_LABELS = {
    "sento": "銭湯",
    "super_sento": "スーパー銭湯",
    "spa": "日帰り温浴施設",
    "other": "その他の温浴施設",
}


def _yn_tag(label: str, value: bool | None) -> str:
    css = "yes" if value else "no"
    text = feature_text(label, value)
    return f'<span class="facility-tag {css}">{escape(text)}</span>'


def render_facility_card(
    facility: dict[str, Any],
    visited: bool,
    on_detail: Callable[[str], None],
    key_prefix: str = "facility",
) -> None:
    name = escape(str(facility.get("name", "名称未設定")))
    ward = escape(str(facility.get("ward", "")))
    category = escape(CATEGORY_LABELS.get(facility.get("category"), "温浴施設"))
    state_text = "○たい　訪問済み" if visited else "未訪問"
    status_class = "facility-status visited" if visited else "facility-status"

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="facility-card">
              <div class="facility-card-title">{name}</div>
              <div class="facility-card-meta">{ward}　｜　{category}</div>
              <div class="facility-tags">
                {_yn_tag("露天風呂", facility.get("has_open_air_bath"))}
                {_yn_tag("天然温泉", facility.get("has_natural_hot_spring"))}
              </div>
              <div class="{status_class}">{state_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("詳しく見る", key=f"{key_prefix}_{facility.get('id')}", width="stretch"):
            on_detail(str(facility.get("id")))

# ── 3. 地図 ──
TOKYO_CENTER = (35.6764, 139.7483)
TOKYO_23_BOUNDS = [[35.52, 139.55], [35.82, 139.93]]



def _valid_facilities(facilities: Iterable[dict[str, Any]]) -> list[tuple[dict[str, Any], float, float]]:
    valid: list[tuple[dict[str, Any], float, float]] = []
    for facility in facilities:
        lat = facility.get("latitude")
        lon = facility.get("longitude")
        if lat in (None, "") or lon in (None, ""):
            continue
        try:
            lat, lon = float(lat), float(lon)
            if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                valid.append((facility, lat, lon))
        except (TypeError, ValueError):
            continue
    return valid


def build_facility_map(
    facilities: Iterable[dict[str, Any]],
    visited_ids: set[str],
    zoom_start: int = 11,
    fit_23_wards: bool | None = None,
) -> folium.Map:
    facilities = list(facilities)
    valid = _valid_facilities(facilities)

    if fit_23_wards is None:
        fit_23_wards = zoom_start <= 12

    if fit_23_wards:
        center = TOKYO_CENTER
    elif len(valid) == 1:
        center = (valid[0][1], valid[0][2])
    elif valid:
        center = (
            sum(lat for _, lat, _ in valid) / len(valid),
            sum(lon for _, _, lon in valid) / len(valid),
        )
    else:
        center = TOKYO_CENTER

    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        min_zoom=9,
    )

    if fit_23_wards:
        m.fit_bounds(TOKYO_23_BOUNDS, padding=(8, 8))

    for facility, lat, lon in valid:
        fid = str(facility.get("id"))
        visited = fid in visited_ids

        if visited:
            marker_html = """
            <div style='width:42px;height:42px;border-radius:50%;background:#d9362b;color:white;
            border:4px solid #fff7e8;box-shadow:0 2px 8px #0003;display:flex;align-items:center;
            justify-content:center;font-weight:900;font-size:15px;font-family:sans-serif;'>たい</div>
            """
        else:
            marker_html = """
            <div style='width:36px;height:36px;border-radius:19px 19px 19px 4px;background:#173a5e;
            color:white;transform:rotate(-45deg);border:3px solid #fff7e8;box-shadow:0 2px 7px #0003;
            display:flex;align-items:center;justify-content:center;'>
              <span style='transform:rotate(45deg);font-size:19px;'>♨</span>
            </div>
            """

        name = escape(str(facility.get("name", "")))
        ward = escape(str(facility.get("ward", "")))
        category = escape(CATEGORY_LABELS.get(facility.get("category"), "温浴施設"))
        visit_text = "訪問済み" if visited else "未訪問"
        open_air = feature_text("露天風呂", facility.get("has_open_air_bath"))
        natural = feature_text("天然温泉", facility.get("has_natural_hot_spring"))

        detail_url = f"?view=facilities&facility_id={quote(fid, safe='')}"

        popup_html = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Yu Gothic',sans-serif;color:#173a5e;min-width:190px;line-height:1.55;">
          <div style="font-size:16px;font-weight:800;margin-bottom:3px;">{name}</div>
          <div style="font-size:13px;">{ward}<br>施設種別：{category}</div>
          <div style="font-size:13px;font-weight:700;color:{'#d9362b' if visited else '#173a5e'};">{visit_text}</div>
          <div style="font-size:12px;margin-top:5px;">♨ {escape(open_air)}<br>♨ {escape(natural)}</div>
          <a href="{detail_url}" target="_top" style="display:block;margin-top:8px;padding:7px 10px;border-radius:9px;background:#d9362b;color:#fff;text-align:center;text-decoration:none;font-weight:800;font-size:13px;">詳しく見る</a>
        </div>
        """
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=name,
            icon=folium.DivIcon(html=marker_html, icon_size=(42, 42), icon_anchor=(21, 36)),
        ).add_to(m)

    return m

# ── 4. 画面 ──
def render_home(go):
    render_logo()
    st.markdown("<div class='hero-question'>今日はどこのお風呂へ行く？</div>", unsafe_allow_html=True)

    if st.button("🗺️  地図から探す", key="home_map", type="primary", width="stretch"):
        go("map")
    if st.button("♨  露天風呂を探す", key="home_open_air", width="stretch"):
        go("map", open_air="1")
    if st.button("📖  スタンプ帳", key="home_stampbook", width="stretch"):
        go("stampbook")
    if st.button("📷  行ってきた！", key="home_visit", width="stretch"):
        go("visit")

    visits = list_visits()
    unique_facilities = {str(v.get("facility_id")) for v in visits}
    total = len(unique_facilities)
    st.markdown(
        f"<div class='count-card'><span>これまでに</span><strong>{total}湯！</strong></div>",
        unsafe_allow_html=True,
    )

    if visits:
        unique_by_facility = {}
        for v in visits:
            unique_by_facility.setdefault(str(v.get("facility_id")), v.get("facilities") or {})
        ward_counter = Counter(f.get("ward", "") for f in unique_by_facility.values())
        ward_counter.pop("", None)
        if ward_counter:
            st.markdown("#### 区ごとの記録")
            cols = st.columns(min(3, len(ward_counter)))
            for i, (ward, count) in enumerate(ward_counter.most_common(6)):
                cols[i % len(cols)].metric(ward, f"{count}湯")

        achieved = [n for n in (3, 5, 10, 20) if total >= n]
        if achieved:
            st.success(f"{max(achieved)}湯達成！")

WARDS = [
    "千代田区","中央区","港区","新宿区","文京区","台東区","墨田区","江東区","品川区","目黒区","大田区",
    "世田谷区","渋谷区","中野区","杉並区","豊島区","北区","荒川区","板橋区","練馬区","足立区","葛飾区","江戸川区",
]


def render_map(go):
    st.markdown("# 🗺️ 地図から探す")
    facilities = list_facilities()
    visited = visited_facility_ids()

    if not facilities:
        st.warning("施設データがまだありません。data/facilities.csv に施設を登録してください。")
        st_folium(build_facility_map([], visited), width=None, height=430, returned_objects=[])
        return

    default_open_air = st.query_params.get("open_air") == "1"
    with st.expander("絞り込み", expanded=True):
        category = st.multiselect(
            "施設種別",
            options=list(CATEGORY_LABELS.keys()),
            format_func=lambda x: CATEGORY_LABELS[x],
            placeholder="施設の種類を選ぶ",
        )
        open_air = st.checkbox("露天風呂あり", value=default_open_air)
        natural = st.checkbox("天然温泉あり")
        ward = st.selectbox("区を選ぶ", ["すべて"] + WARDS)
        visit_state = st.selectbox("訪問状態", ["すべて", "未訪問", "訪問済み"], index=0)

    filtered = []
    for f in facilities:
        fid = str(f.get("id"))
        if category and f.get("category") not in category:
            continue
        if open_air and not f.get("has_open_air_bath"):
            continue
        if natural and not f.get("has_natural_hot_spring"):
            continue
        if ward != "すべて" and f.get("ward") != ward:
            continue
        if visit_state == "訪問済み" and fid not in visited:
            continue
        if visit_state == "未訪問" and fid in visited:
            continue
        filtered.append(f)

    st.caption(f"{len(filtered)}施設を表示")
    st_folium(
        build_facility_map(filtered, visited, zoom_start=11, fit_23_wards=True),
        width=None,
        height=455,
        returned_objects=[],
    )

    st.markdown("### 施設一覧")
    for f in filtered:
        render_facility_card(
            f,
            str(f.get("id")) in visited,
            lambda fid: go("facilities", facility_id=fid),
            "map",
        )
    if not filtered:
        st.info("条件に合う施設はありません。")

def _detail(go, facility_id: str):
    f = get_facility(facility_id)
    if not f:
        st.error("施設情報が見つかりません。")
        if st.button("施設一覧へ戻る"):
            go("facilities")
        return

    visits = visits_for_facility(facility_id)
    name = escape(str(f.get("name", "")))
    ward = escape(str(f.get("ward", "")))
    category = escape(CATEGORY_LABELS.get(f.get("category"), "温浴施設"))
    address = escape(str(f.get("address", "")))
    status = "○たい　訪問済み" if visits else "未訪問"
    open_air = feature_text("露天風呂", f.get("has_open_air_bath"))
    natural = feature_text("天然温泉", f.get("has_natural_hot_spring"))

    st.markdown(f"# {name}")
    st.markdown(
        f"""
        <div class="detail-summary">
          <strong>{ward}</strong>　｜　{category}<br>
          {address}<br>
          <strong>{status}</strong><br>
          {escape(open_air)}　｜　{escape(natural)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if f.get("latitude") not in (None, "") and f.get("longitude") not in (None, ""):
        st_folium(
            build_facility_map([f], {facility_id} if visits else set(), zoom_start=15, fit_23_wards=False),
            width=None,
            height=300,
            returned_objects=[],
        )
    else:
        st.info("緯度・経度が未登録のため地図は表示できません。")

    if str(f.get("website_url") or "").startswith(("https://", "http://")):
        st.link_button("公式サイト", str(f.get("website_url")), width="stretch")

    if st.button("📷 この施設で『行ってきた！』", type="primary", width="stretch"):
        go("visit", facility_id=facility_id)

    st.markdown("### 訪問記録")
    if not visits:
        st.caption("まだ訪問記録はありません。")
    else:
        st.write(f"これまで **{len(visits)}回** 行ったよ")
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")))
        for idx, visit in enumerate(visits, start=1):
            st.markdown(f"**{idx}回目**　{visit.get('visited_date','')}")
            url = photo_path(visit.get("stamped_photo_url"))
            if url:
                st.image(url, width="stretch")


def render_facilities(go):
    facility_id = st.query_params.get("facility_id")
    if facility_id:
        _detail(go, facility_id)
        return

    st.markdown("# お風呂を探す")
    render_data_settings()
    st.caption("施設名や区名から、行きたいお風呂を探せます。")
    facilities = list_facilities()
    visited = visited_facility_ids()
    query = st.text_input(
        "施設名・住所から検索",
        placeholder="例：品川、新生湯",
        label_visibility="collapsed",
    )
    if query:
        q = query.strip().lower()
        facilities = [
            f for f in facilities
            if q in str(f.get("name", "")).lower()
            or q in str(f.get("address", "")).lower()
            or q in str(f.get("ward", "")).lower()
        ]

    st.caption(f"{len(facilities)}施設")
    for f in facilities:
        render_facility_card(
            f,
            str(f.get("id")) in visited,
            lambda fid: go("facilities", facility_id=fid),
            "list",
        )
    if not facilities:
        st.info("条件に合う施設はありません。")

def _normalize_photo(raw: bytes) -> bytes:
    image = Image.open(BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    out = BytesIO()
    image.save(out, "JPEG", quality=94, optimize=True)
    return out.getvalue()


def render_visit(go):
    st.markdown("# 📷 行ってきた！")
    facilities = list_facilities()
    if not facilities:
        st.warning("先に施設データを登録してください。")
        return

    preselected = st.query_params.get("facility_id", "")
    labels = {str(f.get("id")): facility_label(f) for f in facilities}
    ids = list(labels)
    initial = ids.index(preselected) if preselected in ids else 0

    st.markdown("### 1　訪問した施設を選ぶ")
    facility_id = st.selectbox(
        "施設",
        ids,
        index=initial,
        format_func=lambda x: labels[x],
        label_visibility="collapsed",
    )

    st.markdown("### 2　写真を撮影／選択")
    mode = st.radio("写真の追加方法", ["カメラで撮る", "写真を選ぶ"], horizontal=False)
    if mode == "カメラで撮る":
        st.caption("カメラの使用を許可してください。写真を選ぶ方法も使えます。")
    uploaded = (
        st.camera_input("銭湯・施設前で1枚", label_visibility="collapsed")
        if mode == "カメラで撮る"
        else st.file_uploader(
            "写真を選ぶ",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
    )

    st.markdown("### 3　訪問日")
    visited_date = st.date_input("訪問日", value=datetime.now(ZoneInfo("Asia/Tokyo")).date(), label_visibility="collapsed")

    st.markdown("### 4　スタンプを押す")
    if st.button("○たい　スタンプを押す！", type="primary", width="stretch"):
        if uploaded is None:
            st.warning("銭湯前の写真を1枚追加してね")
            return
        try:
            import hashlib
            fingerprint = hashlib.sha256(uploaded.getvalue() + facility_id.encode() + visited_date.isoformat().encode()).hexdigest()
            if fingerprint == st.session_state.get("last_saved_fingerprint"):
                st.info("この写真・施設・訪問日は保存済みです。")
                return
            original = _normalize_photo(uploaded.getvalue())
            stamped = add_visit_stamp(original, visited_date.isoformat(), position="bottom_right")
            create_visit(facility_id, visited_date.isoformat(), original, stamped)
            st.session_state["last_saved_fingerprint"] = fingerprint
            st.session_state["last_stamped_photo"] = stamped
            st.session_state["last_visit_facility"] = labels[facility_id]
            st.success("たい！またひとつ増えたよ！")
        except Exception as exc:
            st.error("訪問記録を保存できませんでした。写真を確認して、もう一度お試しください。")
            LOGGER.exception("訪問登録失敗")

    if st.session_state.get("last_stamped_photo"):
        st.image(
            st.session_state["last_stamped_photo"],
            caption=st.session_state.get("last_visit_facility", ""),
            width="stretch",
        )
        if st.button("スタンプ帳を見る", width="stretch"):
            go("stampbook")

def render_stampbook(go):
    st.markdown("# 📖 スタンプ帳")
    visits = list_visits()
    if not visits:
        st.info("まだスタンプがありません。『行ってきた！』から最初の1湯を記録できます。")
        return

    sort_mode = st.segmented_control(
        "並べ替え",
        ["新しい順", "古い順", "区ごと", "施設名順"],
        default="新しい順",
        selection_mode="single",
    )

    def name(v):
        return (v.get("facilities") or {}).get("name", "")

    def ward(v):
        return (v.get("facilities") or {}).get("ward", "")

    if sort_mode == "古い順":
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")))
    elif sort_mode == "区ごと":
        visits = sorted(visits, key=lambda v: (ward(v), str(v.get("visited_date", ""))))
    elif sort_mode == "施設名順":
        visits = sorted(visits, key=lambda v: (name(v), str(v.get("visited_date", ""))))
    else:
        visits = sorted(visits, key=lambda v: str(v.get("visited_date", "")), reverse=True)

    # スマホ最優先のため1列表示。360px幅でも写真・文字・ボタンを潰さない。
    for visit in visits:
        f = visit.get("facilities") or {}
        with st.container(border=True):
            url = photo_path(visit.get("stamped_photo_url"))
            if url:
                st.image(url, width="stretch")
            st.markdown(f"### {f.get('name','施設名未取得')}")
            st.caption(f"○たい　{f.get('ward','')}　{visit.get('visited_date','')}")
            if st.button("詳しく見る", key=f"stamp_{visit.get('id')}", width="stretch"):
                go("facilities", facility_id=str(visit.get("facility_id")))

# ── 5. 画面遷移・起動 ──
def go(page: str, **params: str) -> None:
    st.session_state.pop("last_stamped_photo", None)
    st.session_state.pop("last_visit_facility", None)
    st.query_params.clear()
    st.query_params["view"] = page
    for key, value in params.items():
        if value not in (None, ""):
            st.query_params[key] = str(value)
    st.rerun()


def bottom_nav(active: str) -> None:
    # Streamlitボタンで移動し、認証・入力状態を保つ。
    with st.container(key="bottom_nav"):
        cols = st.columns(4)
        for col, (page, label) in zip(cols, [("home", "⌂ ホーム"), ("map", "🗺 地図"),
                                           ("stampbook", "▣ スタンプ帳"), ("facilities", "••• その他")]):
            with col:
                if st.button(label, key="nav_" + page, type="primary" if page == active else "secondary",
                             width="stretch"):
                    go(page)


def main() -> None:
    st.set_page_config(page_title="まるたいスタンプラリー", page_icon="♨️", layout="centered", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    require_access()
    st.session_state["run_data"] = {}
    # 旧URLのpageにも互換対応。
    page = st.query_params.get("view", st.query_params.get("page", "home"))
    routes = {"home": render_home, "map": render_map, "facilities": render_facilities,
              "visit": render_visit, "stampbook": render_stampbook}
    try:
        routes.get(page, render_home)(go)
    except Exception:
        LOGGER.exception("画面の読み込みに失敗: %s", page)
        st.error("データを読み込めませんでした。接続と初期設定を確認し、再読み込みしてください。")
        if st.button("再読み込み"):
            st.rerun()
    bottom_nav(page if page in routes else "home")


if __name__ == "__main__":
    main()
