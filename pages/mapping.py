import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

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

# --- Widget Tanggal berdasarkan Data Reclaimer ---
available_dates = get_available_dates(df_reclaimer_all)
if not available_dates:
    st.sidebar.error("Tidak ada data tanggal yang valid di sheet Reclaimer.")
    st.stop()

selected_date = st.sidebar.selectbox(
    "Pilih Tanggal (berdasarkan data Reclaimer)",
    options=available_dates,
    format_func=lambda date: pd.to_datetime(date).strftime('%d %B %Y'),
    help="Tampilkan kondisi PADA atau SEBELUM tanggal aktivitas reclaimer yang dipilih."
)
selected_datetime = selected_date

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


# ===================== T A M P I L A N   H A L A M A N   U T A M A =====================
# Filter berdasarkan tanggal yang dipilih untuk semua tabel dan plot
next_day = selected_datetime + pd.Timedelta(days=1)

# --- Tabel History Mapping (Filtered) ---
st.subheader(f"History Data dari Google Sheets (Mapping) s/d {selected_datetime.strftime('%d %B %Y')}")
df_history_mapping_filtered = df_all[df_all['tanggal'] < next_day].copy()
kolom_tampil_history = ["tipe", "tongkang", "Ash_%", "Sulfur_%", "tanggal","tiang_start","tiang_end","Sudut Stacking","ketinggian"]
st.dataframe(
    df_history_mapping_filtered.sort_values("tanggal", ascending=False)[[c for c in kolom_tampil_history if c in df_history_mapping_filtered.columns]],
    use_container_width=True
)
# --- Widget Pilihan Sumber Tanggal ---
st.sidebar.subheader("Pengaturan Tanggal")
source = st.sidebar.radio(
    "Gunakan tanggal dari:",
    ["Reclaimer", "Mapping"],
    index=0,  # default: Reclaimer
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
    overlap_y = not (r1["sudut_end"] <= r2["sudut_start"] or r1["sudut_start"] >= r2["sudut_end"])
    return overlap_x and overlap_y

# Urutkan berdasarkan tanggal (baru -> lama), lalu iterasi untuk mendapatkan data unik yang tidak tumpang tindih
df_sorted = df_history_mapping_filtered.sort_values("tanggal", ascending=False)
selected_rows = []
for _, row in df_sorted.iterrows():
    if not any(is_overlap(row, sel) for sel in selected_rows):
        selected_rows.append(row)

# Hasil final untuk plotting mapping
df_plot = pd.DataFrame(selected_rows)
if not df_plot.empty and "tiang_start" in df_plot.columns:
    df_plot = df_plot.sort_values("tiang_start", ascending=True)

st.subheader("Data Tumpukan Batubara (Coal Pile) yang Ditampilkan di Plot")
st.dataframe(df_plot, use_container_width=True)


# ===================== PLOTTING DENGAN PLOTLY =====================
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

# ===================== PLOT KETINGGIAN BOOM =====================
st.subheader("Visualisasi Ketinggian Boom per Tiang")
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
    df_ketinggian['color'] = df_ketinggian['tipe'].map(color_map).fillna('lightgrey')
    df_ketinggian = df_ketinggian.sort_values('tiang')

    fig2 = go.Figure(go.Bar(
        x=df_ketinggian['tiang'], y=df_ketinggian['ketinggian_boom'], marker_color=df_ketinggian['color'],
        hoverinfo='text',
        hovertext=[f"<b>Tiang:</b> {r['tiang']}<br><b>Ketinggian:</b> {r['ketinggian_boom']:.2f}<br><b>Tipe Coal:</b> {r['tipe'] if pd.notna(r['tipe']) else 'N/A'}" for _, r in df_ketinggian.iterrows()]
    ))
    fig2.update_layout(title_text=f"Ketinggian Boom per Tiang (s/d {selected_datetime.strftime('%d %B %Y')})",
                       xaxis_title="Nomor Tiang", yaxis_title="Ketinggian Boom (meter)",
                       xaxis=dict(range=[0.5, 35.5], dtick=1), yaxis=dict(range=[0, df_ketinggian['ketinggian_boom'].max() + 5 if not df_ketinggian.empty else 10]), height=500)
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("Tidak ada data ketinggian boom yang valid untuk ditampilkan pada tanggal yang dipilih.")
