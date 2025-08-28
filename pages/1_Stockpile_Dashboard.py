import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd

st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

# PASTIKAN URL SHEET ANDA BENAR
SPREADSHEET_URL = "https://docs.google.com/sheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

# --- Koneksi ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Baca data ---
try:
    df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=5) # Menggunakan TTL rendah untuk refresh data
except Exception as e:
    st.error(f"Gagal membaca Google Sheet. Pastikan URL sudah benar dan sheet telah di-share. Error: {e}")
    st.stop()
    
st.subheader("Raw data dari Google Sheets")
st.dataframe(df, use_container_width=True)

# --- Bersihkan tipe data utama ---
for col in ["tiang_start", "tiang_end", "lebar(tiang)", "sudut_start", "sudut_end", "Ash_%", "Sulfur_%"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Mengubah kolom yang wajib ada untuk plotting dan hover
need_cols = ["name", "tiang_start", "tiang_end", "sudut_start", "sudut_end", "stockpile_id", "Ash_%", "Sulfur_%"]
missing = [c for c in need_cols if c not in df.columns]
if missing:
    st.error(f"Kolom wajib belum lengkap di sheet: {', '.join(missing)}")
    st.stop()

df_plot = df.dropna(subset=need_cols).copy()

if df_plot.empty:
    st.warning("Tidak ada data valid yang bisa di-plot setelah membuang baris kosong. Periksa kembali isi Google Sheet Anda.")
    st.stop()

# --- Plot rectangles ---
st.subheader("Mapping Coal Berdasarkan Tiang dan Sudut Stacking")
fig = go.Figure()

# Menentukan batas sumbu x dan y secara dinamis
x_min = int(df_plot["tiang_start"].min())
x_max = int(df_plot["tiang_end"].max())
y_min = int(df_plot["sudut_start"].min())
y_max = int(df_plot["sudut_end"].max())

# palet warna
palette = pc.qualitative.Plotly
n_colors = len(palette)

for i, r in df_plot.reset_index(drop=True).iterrows():
    y0 = float(r["sudut_start"])
    y1 = float(r["sudut_end"])
    
    x0, x1 = float(r["tiang_start"]), float(r["tiang_end"])
    color = palette[i % n_colors]

    fig.add_shape(
        type="rect",
        x0=x0, y0=y0, x1=x1, y1=y1,
        line=dict(color=color, width=3),
        fillcolor=color,
        opacity=0.5,
    )
    
    fig.add_annotation(
        x=(x0 + x1) / 2,
        y=(y0 + y1) / 2,
        text=str(r["name"]),
        showarrow=False,
        font=dict(size=15, color="black"),
    )

# Menambahkan scatter plot transparan untuk fungsi hover
# Setiap titik berada di tengah-tengah rectangle
fig.add_trace(
    go.Scatter(
        x=(df_plot["tiang_start"] + df_plot["tiang_end"]) / 2,
        y=(df_plot["sudut_start"] + df_plot["sudut_end"]) / 2,
        mode="markers",
        marker=dict(size=0.1, opacity=0), # Membuat marker tidak terlihat
        hoverinfo="text",
        hovertext=df_plot.apply(
            lambda row: f"<b>Stockpile ID:</b> {row['stockpile_id']}<br><b>Ash:</b> {row['Ash_%']:.2f}%<br><b>Sulfur:</b> {row['Sulfur_%']:.2f}%",
            axis=1
        ),
        showlegend=False
    )
)

# Konfigurasi Sumbu X
fig.update_xaxes(
    title="Nomor Tiang", 
    range=[x_min - 1, x_max + 1], 
    dtick=1
)

# Konfigurasi Sumbu Y
fig.update_yaxes(
    title="Sudut Stacking (derajat)",
    range=[y_min, y_max],
    dtick=10,
    showticklabels=True,
    showline=True,
    linecolor="grey"
)

fig.update_layout(
    height=600,
    margin=dict(l=10, r=10, t=50, b=10),
    title="Visualisasi Posisi Coal Pile",
    hovermode="closest", # Mengaktifkan hover pada titik terdekat
    dragmode=False
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "zoom", "select", "lasso2d", "pan"
        ]
    }
)