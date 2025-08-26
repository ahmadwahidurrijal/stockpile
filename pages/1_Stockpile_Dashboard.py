# example/st_app.py
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd

st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

# --- Koneksi ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Baca data ---
df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
st.subheader("Raw data dari Google Sheets")
st.dataframe(df, use_container_width=True)

# --- Bersihkan tipe data utama ---
for col in ["tiang_start", "tiang_end", "lebar(tiang)"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

need_cols = ["name", "tiang_start", "tiang_end", "lebar(tiang)"]
missing = [c for c in need_cols if c not in df.columns]
if missing:
    st.error(f"Kolom wajib belum lengkap di sheet: {', '.join(missing)}")
    st.stop()

st.subheader("Subset kolom (name & lebar)")
subset = df[["name", "lebar(tiang)"]].copy()
st.dataframe(subset, use_container_width=True)

# --- Plot rectangles ---
st.subheader("Mapping Coal Berdasarkan tiang dan tipe coal")
fig = go.Figure()

x_min = int(df["tiang_start"].min()) if df["tiang_start"].notna().any() else 0
x_max = int(df["tiang_end"].max()) if df["tiang_end"].notna().any() else 10

# palet warna
palette = pc.qualitative.Set3 + pc.qualitative.Pastel1
n_colors = len(palette)

y_gap = 0
for i, r in df.dropna(subset=["tiang_start", "tiang_end"]).reset_index(drop=True).iterrows():
    y0, y1 = i * y_gap + 0.2, i * y_gap + 0.8
    x0, x1 = float(r["tiang_start"]), float(r["tiang_end"])
    color = palette[i % n_colors]

    fig.add_shape(
        type="rect",
        x0=x0, y0=y0, x1=x1, y1=y1,
        line=dict(color=color, width=4),
        fillcolor=color,
        opacity=0.4,
    )
    fig.add_annotation(
        x=(x0 + x1) / 2,
        y=(y0 + y1) / 2,
        text=str(r["name"]),
        showarrow=False,
        font=dict(size=11),
    )

fig.update_xaxes(title="Tiang", range=[x_min - 1, x_max + 1], dtick=1)
fig.update_yaxes(
    range=[0.25,0.95],       # hanya tampil dari 0 s.d. 1
    showticklabels=False,
    showline=True,
    linecolor="grey"
)

fig.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=40, b=10),
    title="Rentang Tiang per Pile (tipe jenis coal per warna)",
    dragmode=False    # nonaktifkan drag default (zoom/pan/select)
    
)
st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displaylogo": False,  # hilangkan logo Plotly
        "modeBarButtonsToRemove": [
            "zoom", "select", "lasso2d"
        ]
    }
)

