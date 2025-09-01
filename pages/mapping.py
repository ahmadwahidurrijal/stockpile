import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

# ===================== S U M B E R   D A T A =====================
# URL 1 (lama) untuk mapping/rectangles
SPREADSHEET_URL = "https://docs.google.com/sheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

# URL 2 (baru) untuk tabel reclaimer (kolom: tanggal, tiang_awal, tiang_ahir, ketinggian_boom)
RECLAIMER_URL = "https://docs.google.com/spreadsheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=1231789348#gid=1231789348"
# Jika tab/worksheet-nya bernama "reclaimer", isi di sini; kalau tidak yakin, biarkan None agar baca sheet sesuai gid
RECLAIMER_SHEET = None  # atau "reclaimer"

# --- Koneksi ke Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def read_sheet(url: str, worksheet: str | None = None) -> pd.DataFrame:
    """Helper baca sheet dgn fallback."""
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

# ===================== B A C A   D A T A   U T A M A =====================
df = read_sheet(SPREADSHEET_URL)

st.subheader("Raw data dari Google Sheets (Mapping)")
kolom_tampil = ["tipe", "tongkang", "Ash_%", "Sulfur_%", "tanggal","lebar(tiang)","Sudut Stacking"]
st.dataframe(
    df[[c for c in kolom_tampil if c in df.columns]],
    use_container_width=True
)

# --- Pembersihan dan Validasi Data ---
if "tanggal" in df.columns:
    df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce', dayfirst=True)

for col in ["tiang_start", "tiang_end", "lebar(tiang)", "sudut_start", "sudut_end", "Ash_%", "Sulfur_%"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

need_cols = ["tipe", "tiang_start", "tiang_end", "sudut_start", "sudut_end", "tongkang", "Ash_%", "Sulfur_%", "tanggal"]
missing = [c for c in need_cols if c not in df.columns]
if missing:
    st.error(f"Kolom wajib belum lengkap di sheet (mapping): {', '.join(missing)}")
    st.stop()

df_plot = df.dropna(subset=need_cols).copy()
if df_plot.empty:
    st.warning("Tidak ada data valid yang bisa di-plot setelah membuang baris kosong. Periksa kembali isi Google Sheet Anda.")
    st.stop()

# Hanya ambil baris terbaru per (tiang_start, tiang_end, sudut_start, sudut_end)
df_plot = df_plot.loc[
    df_plot.groupby(["tiang_start", "tiang_end", "sudut_start", "sudut_end"])["tanggal"].idxmax()
]

# --- WIDGET PENGATURAN SKALA ---
st.sidebar.subheader("Pengaturan Skala Sumbu")
x_min_default = int(df_plot["tiang_start"].min())
x_max_default = int(df_plot["tiang_end"].max())
y_min_default = int(df_plot["sudut_start"].min())
y_max_default = int(df_plot["sudut_end"].max())

x_min_custom, x_max_custom = st.sidebar.slider(
    "Rentang Tiang (Sumbu X)",
    min_value=x_min_default - 5,
    max_value=x_max_default + 5,
    value=(x_min_default, x_max_default)
)
y_min_custom, y_max_custom = st.sidebar.slider(
    "Rentang Sudut (Sumbu Y)",
    min_value=y_min_default - 20,
    max_value=y_max_default + 20,
    value=(y_min_default, y_max_default)
)

# --- Plotting dengan Plotly ---


# ===================== R E C L A I M E R   ( T A B E L   B A R U ) =====================
st.subheader("Tabel Reclaimer (URL kedua)")
df_reclaimer = read_sheet(RECLAIMER_URL, RECLAIMER_SHEET)

# Normalisasi nama kolom agar aman (mis. ada spasi/kapital)
df_reclaimer.columns = [c.strip() for c in df_reclaimer.columns]

# Casting tipe data sesuai kolom yang kamu sebutkan
if "tanggal" in df_reclaimer.columns:
    df_reclaimer["tanggal"] = pd.to_datetime(df_reclaimer["tanggal"], errors="coerce", dayfirst=True)

for num_col in ["tiang_awal", "tiang_ahir", "ketinggian_boom"]:
    if num_col in df_reclaimer.columns:
        df_reclaimer[num_col] = pd.to_numeric(df_reclaimer[num_col], errors="coerce")

# Urutan kolom sesuai permintaan (tampilkan yang ada saja biar aman)
cols_order = [c for c in ["tanggal", "tiang_awal", "tiang_ahir", "ketinggian_boom"] if c in df_reclaimer.columns]

# cara 2: tinggi dinamis (30px per baris, max 500px)
n_rows = len(df_reclaimer)
row_height = 30
max_height = 500
dynamic_height = min(n_rows * row_height + 30, max_height)

st.dataframe(
    df_reclaimer[cols_order] if cols_order else df_reclaimer,
    use_container_width=True,
    height=dynamic_height
)

st.caption("Sumber: URL reclaimer (gid=1231789348)")


# ===================== E N D =====================

# --- Plotting dengan Plotly ---
# --- Plotting dengan Plotly ---
st.subheader("Mapping Coal Berdasarkan Tiang dan Sudut Stacking")
fig = go.Figure()

# mapping warna berdasarkan tipe
color_map = {
    "Coal Normal": "green",
    "Coal Mix 2:1": "yellow",
    "Coal HS": "red"
}

for i, r in df_plot.reset_index(drop=True).iterrows():
    y0, y1 = float(r["sudut_start"]), float(r["sudut_end"])
    x0, x1 = float(r["tiang_start"]), float(r["tiang_end"])

    # pilih warna sesuai tipe, default abu-abu kalau tidak ketemu
    tipe = str(r["tipe"]).strip()
    color = color_map.get(tipe, "lightgrey")

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
        text=tipe,
        showarrow=False,
        font=dict(size=15, color="black"),
    )

fig.add_trace(
    go.Scatter(
        x=(df_plot["tiang_start"] + df_plot["tiang_end"]) / 2,
        y=(df_plot["sudut_start"] + df_plot["sudut_end"]) / 2,
        mode="markers",
        marker=dict(size=0.1, opacity=0),
        hoverinfo="text",
        hovertext=df_plot.apply(
            lambda row: (
                f"<b>Tongkang:</b> {row['tongkang']}<br>"
                f"<b>Ash:</b> {row['Ash_%']:.2f}%<br>"
                f"<b>Sulfur:</b> {row['Sulfur_%']:.2f}%<br>"
                f"<b>Tanggal:</b> {row['tanggal'].strftime('%Y-%m-%d')}"
            ),
            axis=1
        ),
        showlegend=False
    )
)

# ===================== Integrasi Reclaimer: hanya ambil 1 data terbaru =====================
need_cols_recl = ["tiang_awal", "tiang_ahir", "tanggal"]
df_recl_plot = df_reclaimer.dropna(subset=need_cols_recl).copy()

# pastikan tipe data
df_recl_plot["tanggal"] = pd.to_datetime(df_recl_plot["tanggal"], errors="coerce", dayfirst=True)
for c in ["tiang_awal", "tiang_ahir", "ketinggian_boom"]:
    if c in df_recl_plot.columns:
        df_recl_plot[c] = pd.to_numeric(df_recl_plot[c], errors="coerce")

# ambil hanya baris dengan tanggal terbaru
if not df_recl_plot.empty:
    latest_idx = df_recl_plot["tanggal"].idxmax()
    df_recl_plot = df_recl_plot.loc[[latest_idx]].copy()

# Gambar kotak reclaimer (outline) + titik ketinggian_boom
for _, rr in df_recl_plot.iterrows():
    x0r, x1r = float(rr["tiang_awal"]), float(rr["tiang_ahir"])
    y0r, y1r = 0.0, 90.0

    # Kotak outline Reclaimer
    fig.add_shape(
        type="rect",
        x0=x0r, y0=y0r, x1=x1r, y1=y1r,
        line=dict(color="grey", width=4, dash="dash"),
        fillcolor="rgba(0,0,0,0)",
        opacity=1.0,
        layer="above"
    )

    # Tambah teks "Reclaimer" di tengah kotak
    fig.add_annotation(
        x=(x0r + x1r) / 2,
        y=(y0r + y1r) / 2,
        text="Reclaimer",
        showarrow=False,
        font=dict(size=14, color="grey"),
        align="center"
    )

    # Titik ketinggian boom
    if "ketinggian_boom" in rr and pd.notna(rr["ketinggian_boom"]):
        x_center = (x0r + x1r) / 2
        y_boom = float(rr["ketinggian_boom"])
        tgl = rr["tanggal"].strftime("%Y-%m-%d") if "tanggal" in rr and pd.notna(rr["tanggal"]) else "-"

        fig.add_trace(
            go.Scatter(
                x=[x_center],
                y=[y_boom],
                mode="markers+text",
                marker=dict(size=10, color="red", symbol="circle"),
                text=[f"Boom {y_boom:.1f}"],
                textposition="top center",
                name=f"Boom {tgl}",
                hovertemplate=(
                    f"<b>Reclaimer</b><br>"
                    f"Tanggal: {tgl}<br>"
                    f"Tiang: {int(x0r)} → {int(x1r)}<br>"
                    f"Ketinggian boom: {y_boom:.2f}"
                ),
                showlegend=False
            )
        )

# Titik hover transparan di tengah kotak
if not df_recl_plot.empty:
    x_center = (df_recl_plot["tiang_awal"] + df_recl_plot["tiang_ahir"]) / 2
    y_center = (y_min_custom + y_max_custom) / 2

    hover_text = df_recl_plot.apply(
        lambda r: (
            f"<b>Reclaimer</b><br>"
            f"Tanggal: {r['tanggal'].strftime('%Y-%m-%d') if ('tanggal' in df_recl_plot.columns and pd.notna(r['tanggal'])) else '-'}<br>"
            f"Tiang: {int(r['tiang_awal']) if pd.notna(r['tiang_awal']) else '-'} → "
            f"{int(r['tiang_ahir']) if pd.notna(r['tiang_ahir']) else '-'}<br>"
            f"Ketinggian boom: "
            f"{(('{:.2f}'.format(float(r['ketinggian_boom']))) if ('ketinggian_boom' in df_recl_plot.columns and pd.notna(r['ketinggian_boom'])) else '-')}"
        ),
        axis=1
    )

    fig.add_trace(
        go.Scatter(
            x=x_center,
            y=[y_center] * len(df_recl_plot),
            mode="markers",
            marker=dict(size=0.1, opacity=0),  # tak terlihat
            hoverinfo="text",
            hovertext=hover_text,
            showlegend=False
        )
    )

# =================== akhir integrasi reclaimer ===================

# ==== Pastikan RANGE sumbu mencakup Reclaimer ====
# X harus mencakup tiang_awal..tiang_ahir
if not df_recl_plot.empty:
    x_min_plot = float(min(x_min_custom, df_recl_plot["tiang_awal"].min()))
    x_max_plot = float(max(x_max_custom, df_recl_plot["tiang_ahir"].max()))
else:
    x_min_plot, x_max_plot = x_min_custom, x_max_custom

# Y harus mencakup 0..90 (kotak reclaimer)
if not df_recl_plot.empty:
    y_min_plot = float(min(y_min_custom, 0.0))
    y_max_plot = float(max(y_max_custom, 90.0))
else:
    y_min_plot, y_max_plot = y_min_custom, y_max_custom
# ================================================

fig.update_xaxes(title="Nomor Tiang", range=[x_min_plot, x_max_plot], dtick=1, showticklabels=True)  # <--
fig.update_yaxes(title="Sudut Stacking (derajat)", range=[y_min_plot, y_max_plot],                 # <--
                 dtick=10, showticklabels=False, showline=True, linecolor="grey")

fig.update_layout(
    height=600,
    margin=dict(l=10, r=10, t=50, b=10),
    title="Visualisasi Posisi Coal Pile + Reclaimer (Outline)",
    hovermode="closest",
    dragmode=False,
    legend=dict(title=None)
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={"displaylogo": False, "modeBarButtonsToRemove": ["zoom", "select", "lasso2d"]}
)

# =================== akhir integrasi reclaimer ===================

