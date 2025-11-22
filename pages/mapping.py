import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import numpy as np
import re

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

# ===================== S U M B E R   D A T A =====================
# URL 1 untuk mapping/rectangles
SPREADSHEET_URL = "https://docs.google.com/sheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

# URL 2 untuk tabel reclaimer
RECLAIMER_URL = "https://docs.google.com/sheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=1231789348#gid=1231789348"
RECLAIMER_SHEET = None

# --- Koneksi ke Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def read_sheet(url: str, worksheet: str | None = None) -> pd.DataFrame:
    """Helper untuk membaca sheet dengan penanganan error."""
    try:
        if worksheet:
            df_ = conn.read(spreadsheet=url, worksheet=worksheet, ttl=5)
        else:
            df_ = conn.read(spreadsheet=url, ttl=5)
    except Exception as e:
        st.error(f"Gagal membaca Google Sheet.\nURL: {url}\nError: {e}")
        st.stop()
    df_.columns = [str(c).strip() for c in df_.columns]
    return df_

# --- FUNGSI: Mendapatkan daftar tanggal yang tersedia ---
def get_available_dates(df: pd.DataFrame) -> list:
    """
    Mengambil tanggal unik dari kolom 'tanggal', membuang nilai kosong, 
    dan mengurutkannya dari terbaru ke terlama.
    """
    if 'tanggal' in df.columns:
        valid_dates = pd.to_datetime(df['tanggal']).dt.normalize().dropna().unique()
        return sorted(valid_dates, reverse=True)
    return []

# ===================== B A C A   &   P R O S E S   D A T A =====================
# --- Data Mapping ---
df_all = read_sheet(SPREADSHEET_URL)
if "tanggal" not in df_all.columns:
    st.error("Kolom 'tanggal' tidak ditemukan di Google Sheet mapping.")
    st.stop()
df_all['tanggal'] = pd.to_datetime(df_all['tanggal'], errors='coerce')
for col in ["tiang_start", "tiang_end", "sudut_start", "sudut_end", "Ash_%", "Sulfur_%"]:
    if col in df_all.columns:
        df_all[col] = pd.to_numeric(df_all[col], errors="coerce")
need_cols = ["tipe", "tiang_start", "tiang_end", "sudut_start", "sudut_end", "tongkang", "Ash_%", "Sulfur_%", "tanggal"]
df_plot_base = df_all.dropna(subset=need_cols).copy()
if df_plot_base.empty:
    st.warning("Tidak ada data mapping valid yang bisa di-plot.")
    st.stop()

# --- Data Reclaimer (dibaca lebih awal untuk widget) ---
df_reclaimer_all = read_sheet(RECLAIMER_URL, RECLAIMER_SHEET)
df_reclaimer_all.columns = [c.strip() for c in df_reclaimer_all.columns]
if "tanggal" in df_reclaimer_all.columns:
    df_reclaimer_all["tanggal"] = pd.to_datetime(df_reclaimer_all["tanggal"], errors='coerce')
for num_col in ["tiang_awal", "tiang_ahir", "ketinggian_boom"]:
    if num_col in df_reclaimer_all.columns:
        df_reclaimer_all[num_col] = pd.to_numeric(df_reclaimer_all[num_col], errors="coerce")


# ===================== W I D G E T   S I D E B A R =====================
st.sidebar.subheader("Pengaturan Tampilan")

# --- Widget Tanggal berdasarkan Data Reclaimer (Default Awal) ---
available_dates_recl = get_available_dates(df_reclaimer_all)
if not available_dates_recl:
    st.sidebar.error("Tidak ada data tanggal yang valid di sheet Reclaimer.")
    # Fallback agar tidak error jika reclaimer kosong tapi mapping ada
    available_dates_recl = [datetime.now()] 

# --- Widget Skala Sumbu ---
st.sidebar.subheader("Pengaturan Skala Sumbu")
x_min_default = int(df_plot_base["tiang_start"].min()) - 5
x_max_default = int(df_plot_base["tiang_end"].max()) + 5
y_min_default = int(df_plot_base["sudut_start"].min())
y_max_default = int(df_plot_base["sudut_end"].max())
x_min_custom, x_max_custom = st.sidebar.slider(
    "Rentang Tiang (Sumbu X)",
    min_value=x_min_default, max_value=x_max_default, value=(x_min_default, x_max_default)
)
y_min_custom, y_max_custom = st.sidebar.slider(
    "Rentang Sudut (Sumbu Y)",
    min_value=y_min_default - 20, max_value=y_max_default + 20, value=(y_min_default, y_max_default)
)


# --- Widget Pilihan Sumber Tanggal & Tanggal Aktif ---
st.sidebar.subheader("Pengaturan Tanggal")
source = st.sidebar.radio(
    "Gunakan tanggal dari:",
    ["Reclaimer", "Mapping"],
    index=0,
    help="Pilih sumber tanggal utama untuk filter data"
)

if source == "Reclaimer":
    available_dates = get_available_dates(df_reclaimer_all)
else:
    available_dates = get_available_dates(df_all)

if not available_dates:
    st.sidebar.error(f"Tidak ada data tanggal yang valid di sheet {source}.")
    st.stop()

selected_date = st.sidebar.selectbox(
    f"Pilih Tanggal (berdasarkan data {source})",
    options=available_dates,
    format_func=lambda date: pd.to_datetime(date).strftime('%d %B %Y'),
    help="Tampilkan kondisi PADA atau SEBELUM tanggal aktivitas yang dipilih."
)
selected_datetime = selected_date

# Filter berdasarkan tanggal yang dipilih
next_day = selected_datetime + pd.Timedelta(days=1)

# --- Tabel History Mapping (Filtered) ---
st.subheader(f"History Data dari Google Sheets (Mapping) s/d {selected_datetime.strftime('%d %B %Y')}")
df_history_mapping_filtered = df_all[df_all['tanggal'] < next_day].copy()
kolom_tampil_history = ["tipe", "tongkang", "Ash_%", "Sulfur_%", "tanggal","tiang_start","tiang_end","Sudut Stacking","ketinggian"]
st.dataframe(
    df_history_mapping_filtered.sort_values("tanggal", ascending=False)[[c for c in kolom_tampil_history if c in df_history_mapping_filtered.columns]],
    use_container_width=True
)

# --- Filter data sampai tanggal terpilih ---
df_reclaimer = df_reclaimer_all[df_reclaimer_all['tanggal'] <= selected_datetime].copy()
df_filtered_date = df_plot_base[df_plot_base['tanggal'] <= selected_datetime].copy()

# --- Tabel History Reclaimer ---
st.subheader(f"History Data Posisi Reclaimer (s/d {selected_datetime.strftime('%d %B %Y')})")
cols_order = [c for c in ["tanggal", "grup", "tiang_awal", "tiang_ahir", "ketinggian_boom"] if c in df_reclaimer.columns]
st.dataframe(
    df_reclaimer.sort_values("tanggal", ascending=False)[cols_order] if cols_order else df_reclaimer.sort_values("tanggal", ascending=False),
    use_container_width=True
)

# ===================== FILTER DATA TERBARU PER OVERLAP =====================
def is_overlap(r1, r2):
    """Cek apakah dua area (rectangle) tumpang tindih."""
    overlap_x = (r1["tiang_start"] < r2["tiang_end"]) and (r2["tiang_start"] < r1["tiang_end"])
    overlap_y = not (r1["sudut_end"] <= r2["sudut_start"] and r1["sudut_start"] >= r2["sudut_end"])
    return overlap_x and overlap_y

# Urutkan berdasarkan tanggal (baru -> lama), lalu iterasi untuk mendapatkan data unik yang tidak tumpang tindih
df_sorted = df_history_mapping_filtered.sort_values("tanggal", ascending=False)
selected_rows = []
for _, row in df_sorted.iterrows():
    if not any(is_overlap(row, sel) for sel in selected_rows):
        selected_rows.append(row)

# Hasil final untuk plotting mapping
# Ambil tanggal terbaru dari df_valid
latest_date = df_sorted["tanggal"].max()

# Ambil batas 1 bulan terakhir
one_month_ago = latest_date - pd.Timedelta(days=30)

# Filter hanya 1 bulan terakhir
df_last_month = df_sorted[df_sorted["tanggal"].between(one_month_ago, latest_date)]

# Jika sebelumnya kamu punya selected_rows:
df_plot = pd.DataFrame(selected_rows)

# Pastikan df_plot hanya berisi 1 bulan terakhir (sinkron dengan data induk)
if not df_plot.empty and "tanggal" in df_plot.columns:
    df_plot["tanggal"] = pd.to_datetime(df_plot["tanggal"], errors="coerce")
    df_plot = df_plot[df_plot["tanggal"].between(one_month_ago, latest_date)]

# Sort sesuai tiang_start
if not df_plot.empty and "tiang_start" in df_plot.columns:
    df_plot = df_plot.sort_values("tiang_start", ascending=True)


st.subheader("Data Batubara (Coal Pile) yang Ditampilkan di Plot")
st.dataframe(df_plot, use_container_width=True)


# ===================== PLOTTING 2D (MAPPING & RECLAIMER) =====================
fig = go.Figure()
color_map = {"Coal Normal": "green", "Coal Mix 2:1": "yellow", "Coal Mix 1:2 (HS:NS)":"yellow", "Coal HS": "red", "Coal NS" : "green"}

# --- Plot Mapping Rectangles ---
for _, r in df_plot.iterrows():
    y0, y1 = float(r["sudut_start"]), float(r["sudut_end"])
    x0, x1 = float(r["tiang_start"]), float(r["tiang_end"])
    tipe = str(r["tipe"]).strip()
    color = color_map.get(tipe, "lightgrey")
    fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=color, width=3), fillcolor=color, opacity=0.5)
    fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=tipe, showarrow=False, font=dict(size=15, color="black"))

# --- Plot Reclaimer ---
df_recl_plot = df_reclaimer.dropna(subset=["tiang_awal", "tiang_ahir", "tanggal"]).copy()
if not df_recl_plot.empty:
    latest_reclaimer = df_recl_plot.loc[df_recl_plot["tanggal"].idxmax()]
    x0r, x1r = float(latest_reclaimer["tiang_awal"]), float(latest_reclaimer["tiang_ahir"])
    fig.add_shape(type="rect", x0=x0r, y0=0, x1=x1r, y1=90, line=dict(color="grey", width=4, dash="dash"), fillcolor="rgba(0,0,0,0)")
    fig.add_annotation(x=(x0r + x1r) / 2, y=45, text="Reclaimer", showarrow=False, font=dict(size=14, color="grey"))
    if "ketinggian_boom" in latest_reclaimer and pd.notna(latest_reclaimer["ketinggian_boom"]):
        fig.add_trace(go.Scatter(
            x=[(x0r + x1r) / 2], y=[float(latest_reclaimer["ketinggian_boom"])],
            mode="markers+text", marker=dict(size=10, color="red", symbol="circle"),
            text=[f"Boom {latest_reclaimer['ketinggian_boom']:.1f}"], textposition="top center", showlegend=False
        ))

# --- Tambah Layer untuk Hover ---
hover_traces = []
for _, r in df_plot.iterrows():
    hover_traces.append(go.Scatter(
        x=[(r["tiang_start"] + r["tiang_end"]) / 2], y=[(r["sudut_start"] + r["sudut_end"]) / 2],
        mode="markers", marker=dict(size=30, opacity=0), hoverinfo="text",
        hovertext=[f"<b>Tipe:</b> {r['tipe']}<br><b>Tongkang:</b> {r['tongkang']}<br><b>Tiang:</b> {int(r['tiang_start'])} → {int(r['tiang_end'])}<br><b>Sudut:</b> {r['sudut_start']:.1f} → {r['sudut_end']:.1f}<br><b>Tanggal:</b> {r['tanggal'].strftime('%Y-%m-%d')}"],
        showlegend=False
    ))
if not df_recl_plot.empty:
    r = latest_reclaimer
    hover_traces.append(go.Scatter(
        x=[(r["tiang_awal"] + r["tiang_ahir"]) / 2], y=[45], mode="markers", marker=dict(size=50, opacity=0),
        hoverinfo="text", hovertext=[f"<b>Reclaimer</b><br>Tanggal: {r['tanggal'].strftime('%Y-%m-%d')}<br>Tiang: {int(r['tiang_awal'])} → {int(r['tiang_ahir'])}"],
        showlegend=False
    ))
for trace in hover_traces:
    fig.add_trace(trace)

# --- Layout Plot Utama ---
fig.update_xaxes(title="Nomor Tiang", range=[x_min_custom, x_max_custom], dtick=1)
fig.update_yaxes(title="Sudut Stacking (derajat)", range=[y_min_custom, y_max_custom], dtick=10)
fig.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=10), title=f"Visualisasi Posisi Coal Pile + Reclaimer per {selected_datetime.strftime('%d %B %Y')}")
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

# ===================== PLOT KETINGGIAN BOOM (3D VERSION) =====================
st.subheader("Visualisasi Ketinggian Boom per Tiang (3D View)")
expanded_data = []
for _, row in df_reclaimer.iterrows():
    if pd.notna(row['tiang_awal']) and pd.notna(row['tiang_ahir']) and pd.notna(row['ketinggian_boom']):
        for tiang in range(int(row['tiang_awal']), int(row['tiang_ahir']) + 1):
            expanded_data.append({'tanggal': row['tanggal'], 'grup': row.get('grup', 'N/A'), 'tiang': tiang, 'ketinggian_boom': row['ketinggian_boom']})

df_ketinggian = pd.DataFrame(expanded_data)

if not df_ketinggian.empty:
    # Ambil data ketinggian terbaru untuk setiap tiang
    df_ketinggian = df_ketinggian.sort_values('tanggal', ascending=False).drop_duplicates(subset=['tiang'], keep='first')
    
    # Petakan tipe batubara ke setiap tiang untuk pewarnaan
    tiang_to_tipe_map = {tiang: row['tipe'] for _, row in df_plot.iterrows() for tiang in range(int(row['tiang_start']), int(row['tiang_end']) + 1)}
    df_ketinggian['tipe'] = df_ketinggian['tiang'].map(tiang_to_tipe_map)
    # Pastikan color_map tersedia (diambil dari blok kode sebelumnya)
    df_ketinggian['color'] = df_ketinggian['tipe'].map(color_map).fillna('lightgrey')
    df_ketinggian = df_ketinggian.sort_values('tiang')

    # --- IMPLEMENTASI 3D PLOT ---
    x_lines = []
    y_lines = []
    z_lines = []
    line_colors = []

    # Kita gunakan Y=0 sebagai baseline karena data aslinya linear (sepanjang tiang)
    # Anda bisa mengganti y_pos dengan mapping 'grup' jika ingin memisahkan grup secara visual
    
    for _, row in df_ketinggian.iterrows():
        y_pos = 0 
        
        # Titik Dasar (Tanah)
        x_lines.append(row['tiang'])
        y_lines.append(y_pos)
        z_lines.append(0)
        line_colors.append(row['color'])
        
        # Titik Puncak (Ketinggian Boom)
        x_lines.append(row['tiang'])
        y_lines.append(y_pos)
        z_lines.append(row['ketinggian_boom'])
        line_colors.append(row['color'])
        
        # Pemisah (None) agar garis tidak bersambung antar tiang
        x_lines.append(None)
        y_lines.append(None)
        z_lines.append(None)
        line_colors.append(row['color'])

    fig3d = go.Figure()

    # --- AREA FILL 3D (Background Curtain) ---
    # Membentuk polygon tertutup: Kiri Bawah -> Puncak-puncak -> Kanan Bawah -> Kiri Bawah
    if len(df_ketinggian) > 1:
        x_fill = [df_ketinggian['tiang'].iloc[0]] + df_ketinggian['tiang'].tolist() + [df_ketinggian['tiang'].iloc[-1]] + [df_ketinggian['tiang'].iloc[0]]
        y_fill = [0] * len(x_fill)
        z_fill = [0] + df_ketinggian['ketinggian_boom'].tolist() + [0] + [0]
        
        fig3d.add_trace(go.Scatter3d(
            x=x_fill, y=y_fill, z=z_fill,
            mode='lines',
            line=dict(width=0), # Hilangkan garis border area
            surfaceaxis=0, # 1 = Normal Sumbu Y (Fill bidang XZ)
            surfacecolor='rgba(0, 200, 255, 0.15)', # Biru muda transparan
            hoverinfo='skip',
            name='Area Coverage'
        ))

    # 1. Gambar Batang Tiang (Garis Vertikal Tebal)
    fig3d.add_trace(go.Scatter3d(
        x=x_lines, y=y_lines, z=z_lines,
        mode='lines',
        line=dict(color=line_colors, width=15), # Width diperbesar agar terlihat solid seperti tiang
        name='Tiang Structure',
        hoverinfo='none'
    ))

    # 2. Gambar Marker di Puncak (untuk Tooltip & Indikator Kepala)
    fig3d.add_trace(go.Scatter3d(
        x=df_ketinggian['tiang'],
        y=[0] * len(df_ketinggian),
        z=df_ketinggian['ketinggian_boom'],
        mode='markers',
        marker=dict(size=6, color=df_ketinggian['color'], symbol='circle'),
        text=[f"<b>Tiang:</b> {r['tiang']}<br><b>Ketinggian:</b> {r['ketinggian_boom']:.2f}m<br><b>Tipe:</b> {r['tipe']}" for _, r in df_ketinggian.iterrows()],
        hoverinfo='text'
    ))

    # Layout 3D
    fig3d.update_layout(
        title=f"Ketinggian Boom 3D (s/d {selected_datetime.strftime('%d %B %Y')})",
        scene=dict(
            xaxis_title='Nomor Tiang',
            yaxis_title='', # Y tidak terlalu relevan di view ini
            zaxis_title='Ketinggian (m)',
            xaxis=dict(range=[0.5, 35.5]), 
            zaxis=dict(range=[0, df_ketinggian['ketinggian_boom'].max() + 5]),
            # Mengunci aspek rasio agar tiang terlihat proporsional
            aspectmode='manual',
            aspectratio=dict(x=2, y=0.5, z=1) 
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=600
    )

    st.plotly_chart(fig3d, use_container_width=True)

else:
    st.warning("Tidak ada data ketinggian boom yang valid untuk ditampilkan pada tanggal yang dipilih.")

# ========Plot baru==========
TIANG_COLS = [
    "Tiang 1-2","Tiang 2-3","Tiang 3-4","Tiang 4-5","Tiang 5-6","Tiang 6-7","Tiang 7-8","Tiang 8-9",
    "Tiang 9-10","Tiang 10-11","Tiang 11-12","Tiang 12-13","Tiang 13-14","Tiang 14-15","Tiang 15-16","Tiang 16-17",
    "Tiang 17-18","Tiang 18-19","Tiang 19-20","Tiang 20-21","Tiang 21-22","Tiang 22-23","Tiang 23-24","Tiang 24-25",
    "Tiang 25-26","Tiang 26-27","Tiang 27-28","Tiang 28-29","Tiang 29-30","Tiang 30-31","Tiang 31-32","Tiang 32-33",
    "Tiang 33-34","Tiang 34-35"
]

# --- Bersihkan & filter 1 bulan terakhir dari df_plot ---
assert "tanggal" in df_plot.columns, "df_plot harus memiliki kolom 'tanggal'"

df_plot = df_plot.copy()
df_plot["tanggal"] = pd.to_datetime(df_plot["tanggal"], errors="coerce", dayfirst=True)
df_valid = df_plot.dropna(subset=["tanggal"])
latest_date = df_valid["tanggal"].max()
one_month_ago = latest_date - pd.Timedelta(days=30)

# Ambil hanya kolom yang diminta (yang memang ada di df_plot)
existing_tiang = [c for c in TIANG_COLS if c in df_valid.columns]
use_cols = ["tanggal"] + existing_tiang

df_last_month = (
    df_valid.loc[df_valid["tanggal"].between(one_month_ago, latest_date), use_cols]
    .copy()
    .sort_values("tanggal")
)

# Coerce numerik untuk kolom Tiang (tangani koma sebagai desimal)
for c in existing_tiang:
    df_last_month[c] = pd.to_numeric(
        df_last_month[c].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

# --- Tampilkan tabel hasil ---
st.subheader("Tiang (1 bulan terakhir dari df_plot)")
st.caption(f"Rentang: {one_month_ago.date()} s.d. {latest_date.date()} | Kolom terpakai: {len(existing_tiang)}")
st.dataframe(df_last_month, use_container_width=True)

# Opsional: unduh CSV hasil filter
st.download_button(
    "Unduh CSV (1 bulan terakhir)",
    df_last_month.to_csv(index=False).encode("utf-8"),
    file_name="tiang_last_month_from_df_plot.csv",
    mime="text/csv"
)

# 1) Jika ada duplikasi per hari, ambil baris terakhir per tanggal (opsional tapi aman)
df_last_month = (
    df_last_month.sort_values("tanggal")
    .groupby("tanggal", as_index=False)
    .tail(1)
    .reset_index(drop=True)
)

# 2) Tentukan kolom TIANG yang dipakai
#    - pakai TIANG_COLS yang ada di df
#    - kalau kosong, auto-deteksi kolom pola "Tiang d1-d2"
existing_tiang = [c for c in TIANG_COLS if c in df_last_month.columns]

if not existing_tiang:
    # Auto-deteksi
    candidate_cols = [
        c for c in df_last_month.columns
        if re.match(r"(?i)^tiang\s*\d+\s*-\s*\d+$", str(c).strip())
    ]
    if not candidate_cols:
        st.error("Tidak ada kolom 'Tiang d1-d2' yang tersedia di df_last_month.")
        st.stop()

    # Urutkan berdasar angka awal segmen
    def seg_start(col):
        m = re.search(r"(\d+)\s*-\s*(\d+)", col)
        return int(m.group(1)) if m else 10**9

    existing_tiang = sorted(candidate_cols, key=seg_start)

# 3) Pastikan numerik
for c in existing_tiang:
    df_last_month[c] = pd.to_numeric(
        df_last_month[c].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

# 4) Siapkan matriks untuk Surface
Z = df_last_month[existing_tiang].to_numpy(dtype=float)   # shape: (n_tanggal, n_tiang)
X = np.arange(1, len(existing_tiang) + 1)                 # 1..N segmen
Y = np.arange(len(df_last_month))                         # index waktu

# 5) Label sumbu Y pakai tanggal (tick text), dibatasi supaya tidak padat
tanggal_str = df_last_month["tanggal"].dt.strftime("%Y-%m-%d").tolist()
if len(Y) <= 12:
    tick_idx = Y.tolist()
else:
    step = max(1, len(Y) // 12)
    tick_idx = list(range(0, len(Y), step))
    if tick_idx[-1] != len(Y) - 1:
        tick_idx.append(len(Y) - 1)  # pastikan titik terakhir tampil

tick_text = [tanggal_str[i] for i in tick_idx]

# 6) Plot 3D Surface
fig = go.Figure(data=[
    go.Surface(
        z=Z,
        x=X,
        y=Y,
        showscale=True,
        colorbar=dict(title="Nilai")
    )
])

fig.update_layout(
    title=f"3D Surface – Profil Tiang (1 bulan terakhir) | {len(df_last_month)} hari × {len(existing_tiang)} segmen",
    scene=dict(
        xaxis_title="Segmen Tiang (1 = Tiang 1-2)",
        yaxis_title="Tanggal",
        zaxis_title="Nilai",
        yaxis=dict(tickmode="array", tickvals=tick_idx, ticktext=tick_text),
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    height=720,
)

#st.plotly_chart(fig, use_container_width=True)

# Opsional: tampilkan info kolom yang dipakai
with st.expander("Kolom tiang yang dipakai"):
    st.write(existing_tiang)

#======new
# Jika TIANG_COLS tidak cocok dengan df, auto-deteksi
existing_tiang = [c for c in TIANG_COLS if c in df_last_month.columns]

if not existing_tiang:
    candidate_cols = [
        c for c in df_last_month.columns
        if re.match(r"(?i)^tiang\s*\d+\s*-\s*\d+$", str(c))
    ]
    if not candidate_cols:
        st.error("Tidak ada kolom Tiang x-y ditemukan di df_last_month.")
        st.stop()

    # Urutkan berdasar nomor awal
    def seg_start(col):
        m = re.search(r"(\d+)\s*-\s*(\d+)", col)
        return int(m.group(1)) if m else 999

    existing_tiang = sorted(candidate_cols, key=seg_start)

# Numerikkan kolom tiang
for c in existing_tiang:
    df_last_month[c] = pd.to_numeric(
        df_last_month[c].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

# ===============================
#  SIAPKAN MATRIKS SURFACE
# ===============================

Z = df_last_month[existing_tiang].to_numpy(dtype=float)

# X = numeric index (0..N-1), tapi nanti ditampilkan sebagai nama tiang
x_numeric = np.arange(len(existing_tiang))

# Y = indeks tanggal
Y = np.arange(len(df_last_month))
tanggal_str = df_last_month["tanggal"].dt.strftime("%Y-%m-%d").tolist()

# Tick tanggal diringkas agar tidak terlalu rapat
if len(Y) <= 12:
    tick_y_idx = Y.tolist()
else:
    step = max(1, len(Y) // 12)
    tick_y_idx = list(range(0, len(Y), step))
    if tick_y_idx[-1] != len(Y) - 1:
        tick_y_idx.append(len(Y) - 1)

tick_y_text = [tanggal_str[i] for i in tick_y_idx]

# ===============================
#  PLOT 3D SURFACE
# ===============================

fig = go.Figure(
    data=[
        go.Surface(
            z=Z,
            x=x_numeric,
            y=Y,
            showscale=True,
            colorbar=dict(title="Nilai"),
        )
    ]
)

fig.update_layout(
    title=f"3D Surface – Profil Tiang (1 bulan terakhir)",
    scene=dict(
        xaxis_title="Segmen Tiang",
        yaxis_title="Tanggal",
        zaxis_title="Nilai",

        # Tampilkan nama kolom tiang di sumbu X
        xaxis=dict(
            tickmode="array",
            tickvals=x_numeric,
            ticktext=existing_tiang
        ),

        # Tampilkan tanggal di sumbu Y
        yaxis=dict(
            tickmode="array",
            tickvals=tick_y_idx,
            ticktext=tick_y_text
        ),
    ),
    margin=dict(l=0, r=0, t=50, b=0),
    height=750,
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("Kolom tiang yang dipakai"):
    st.write(existing_tiang)


#====baru
# List target (opsional). Kalau kosong/tdk lengkap di data, akan auto-deteksi.
TIANG_COLS = [
    "Tiang 1-2","Tiang 2-3","Tiang 3-4","Tiang 4-5","Tiang 5-6","Tiang 6-7","Tiang 7-8","Tiang 8-9",
    "Tiang 9-10","Tiang 10-11","Tiang 11-12","Tiang 12-13","Tiang 13-14","Tiang 14-15","Tiang 15-16","Tiang 16-17",
    "Tiang 17-18","Tiang 18-19","Tiang 19-20","Tiang 20-21","Tiang 21-22","Tiang 22-23","Tiang 23-24","Tiang 24-25",
    "Tiang 25-26","Tiang 26-27","Tiang 27-28","Tiang 28-29","Tiang 29-30","Tiang 30-31","Tiang 31-32","Tiang 32-33",
    "Tiang 33-34","Tiang 34-35"
]

# --- Siapkan kolom tiang yang dipakai ---
def detect_tiang_cols(df):
    # pakai TIANG_COLS yang eksis
    cols = [c for c in TIANG_COLS if c in df.columns]
    if cols:
        return cols
    # fallback: regex auto-deteksi
    cand = [c for c in df.columns if re.match(r"(?i)^tiang\s*\d+\s*-\s*\d+$", str(c).strip())]
    if not cand:
        return []
    # urutkan berdasar angka awal segmen
    def seg_start(col):
        m = re.search(r"(\d+)\s*-\s*(\d+)", col)
        return int(m.group(1)) if m else 10**9
    return sorted(cand, key=seg_start)

assert "tanggal" in df_last_month.columns, "df_last_month harus ada kolom 'tanggal'."
dfm = df_last_month.copy()
dfm["tanggal"] = pd.to_datetime(dfm["tanggal"], errors="coerce")
dfm = dfm.dropna(subset=["tanggal"])

tiang_cols = detect_tiang_cols(dfm)
if not tiang_cols:
    st.error("Tidak ada kolom 'Tiang x-y' ditemukan pada df_last_month.")
    st.stop()

# Coerce numerik (tangani koma)
for c in tiang_cols:
    dfm[c] = pd.to_numeric(dfm[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")

# Urutkan tanggal terbaru -> terlama
dfm = dfm.sort_values("tanggal", ascending=False).reset_index(drop=True)

# Buat profil lengkap:
# bfill mengisi NaN di baris atas dengan nilai dari baris berikutnya (lebih lama)
filled = dfm[tiang_cols].bfill(axis=0)
profile = filled.iloc[0]

# Buang kolom yang tetap NaN sepanjang 1 bulan
mask_non_nan = profile.notna()
tiang_used = list(profile.index[mask_non_nan])
profile = profile[mask_non_nan]

if len(tiang_used) < len(tiang_cols):
    missing = set(tiang_cols) - set(tiang_used)
    st.warning(f"Mengeluarkan {len(missing)} kolom tanpa data sepanjang 1 bulan: {sorted(missing)}")

# (Opsional) tanggal sumber untuk tiap tiang (dari baris pertama yang punya nilai)
source_dates = {}
for c in tiang_used:
    idx = dfm[c].first_valid_index()  # pada dfm yg sudah descending → ini tanggal paling terbaru yg punya nilai
    source_dates[c] = dfm.loc[idx, "tanggal"] if idx is not None else pd.NaT

# --- 2D AREA CHART ---
x_labels = tiang_used                     # tampilkan nama tiang satu per satu
y_values = profile.values.astype(float)   # nilai akhir setelah backfill

fig = go.Figure(
    data=[
        go.Scatter(
            x=x_labels,
            y=y_values,
            mode="lines+markers",
            fill="tozeroy",
            hovertemplate="<b>%{x}</b><br>Nilai: %{y:.3f}<extra></extra>",
            name="Profil lengkap (latest-available)"
        )
    ]
)

fig.update_layout(
    title="2D Area – Profil Tiang (latest-available dalam 1 bulan terakhir)",
    xaxis_title="Segmen Tiang",
    yaxis_title="Nilai",
    margin=dict(l=0, r=0, t=40, b=0),
    height=520,
)

st.plotly_chart(fig, use_container_width=True)

# Pastikan df_plot & df_last_month punya 'tanggal'
df_plot = df_plot.copy()
df_plot["tanggal"] = pd.to_datetime(df_plot["tanggal"], errors="coerce")
dfm = df_last_month.sort_values("tanggal", ascending=False).reset_index(drop=True)  # sumber backfill

# Kumpulkan tanggal sumber per tiang dari df_last_month (sudah descending)
source_dates = {}
for c in x_labels:  # x_labels = daftar kolom tiang yang dipakai
    idx = dfm[c].first_valid_index()
    source_dates[c] = dfm.loc[idx, "tanggal"] if idx is not None else pd.NaT

# Ambil 'tipe' dari df_plot yang tanggalnya sama dengan tanggal sumber
# Fallback: kalau tanggal itu tidak ada di df_plot, ambil tipe dari baris valid terbaru df_plot untuk tiang tsb.
dfp_desc = df_plot.sort_values("tanggal", ascending=False)
tipe_list = []
for c in x_labels:
    sd = source_dates[c]
    tipe_val = None
    if pd.notna(sd):
        match = dfp_desc.loc[dfp_desc["tanggal"] == sd]
        if not match.empty:
            tipe_val = match.iloc[-1]["tipe"] if "tipe" in match.columns else None
    if tipe_val is None and c in dfp_desc.columns:
        idx2 = dfp_desc[c].first_valid_index()
        if idx2 is not None and "tipe" in dfp_desc.columns:
            tipe_val = dfp_desc.loc[idx2, "tipe"]
    tipe_list.append(tipe_val)

with st.expander("Tanggal sumber nilai per tiang"):
    st.dataframe(
        pd.DataFrame({
            "Tiang": x_labels,
            "Tanggal Sumber": [
                source_dates[c].strftime("%Y-%m-%d") if pd.notna(source_dates[c]) else None
                for c in x_labels
            ],
            "Nilai": y_values,   # hasil profil latest-available
            "Tipe": tipe_list,   # diambil dari df_plot pada baris sumber
        }),
        use_container_width=True
    )