import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

# PASTIKAN URL SHEET ANDA BENAR
SPREADSHEET_URL = "https://docs.google.com/sheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

# --- Koneksi ke Google Sheets ---
# Membuat koneksi ke Google Sheet menggunakan GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Membaca Data ---
# Mencoba membaca data dari Google Sheet dengan TTL (Time-To-Live) rendah
try:
    df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=5)
except Exception as e:
    st.error(f"Gagal membaca Google Sheet. Pastikan URL sudah benar dan sheet telah di-share. Error: {e}")
    st.stop()
    
# Menampilkan data mentah dari Google Sheet di halaman
st.subheader("Raw data dari Google Sheets")

# Pilihan kolom yang akan ditampilkan di tabel data mentah
kolom_tampil = ["tipe", "tongkang", "Ash_%", "Sulfur_%", "tanggal","lebar(tiang)","Sudut Stacking"]
st.dataframe(df[kolom_tampil], use_container_width=True)

# --- Pembersihan dan Validasi Data ---
# Mengubah tipe data kolom 'tanggal' menjadi datetime
if "tanggal" in df.columns:
    df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce', dayfirst=True)

# Mengubah tipe data kolom-kolom numerik ke float
for col in ["tiang_start", "tiang_end", "lebar(tiang)", "sudut_start", "sudut_end", "Ash_%", "Sulfur_%"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Daftar kolom yang wajib ada untuk plotting dan hover
need_cols = ["tipe", "tiang_start", "tiang_end", "sudut_start", "sudut_end", "tongkang", "Ash_%", "Sulfur_%", "tanggal"]
missing = [c for c in need_cols if c not in df.columns]
if missing:
    st.error(f"Kolom wajib belum lengkap di sheet: {', '.join(missing)}")
    st.stop()

# Menghapus baris yang memiliki nilai kosong pada kolom-kolom penting
df_plot = df.dropna(subset=need_cols).copy()

if df_plot.empty:
    st.warning("Tidak ada data valid yang bisa di-plot setelah membuang baris kosong. Periksa kembali isi Google Sheet Anda.")
    st.stop()

# --- FILTER DATA UNTUK MENGHILANGKAN OVERLAPPING TIANG ---
# Mengelompokkan data berdasarkan rentang tiang DAN sudut
# dan hanya mengambil baris dengan tanggal terbaru dalam setiap kelompok
df_plot = df_plot.loc[df_plot.groupby(["tiang_start", "tiang_end", "sudut_start", "sudut_end"])["tanggal"].idxmax()]

# --- WIDGET UNTUK KUSTOMISASI SKALA SUMBU ---
st.sidebar.subheader("Pengaturan Skala Sumbu")

# Menentukan batas sumbu x dan y secara dinamis untuk nilai default slider
x_min_default = int(df_plot["tiang_start"].min())
x_max_default = int(df_plot["tiang_end"].max())
y_min_default = int(df_plot["sudut_start"].min())
y_max_default = int(df_plot["sudut_end"].max())

# Membuat slider di sidebar untuk mengatur rentang sumbu X
x_min_custom, x_max_custom = st.sidebar.slider(
    "Rentang Tiang (Sumbu X)",
    min_value=x_min_default - 5,
    max_value=x_max_default + 5,
    value=(x_min_default, x_max_default)
)

# Membuat slider di sidebar untuk mengatur rentang sumbu Y
y_min_custom, y_max_custom = st.sidebar.slider(
    "Rentang Sudut (Sumbu Y)",
    min_value=y_min_default - 20,
    max_value=y_max_default + 20,
    value=(y_min_default, y_max_default)
)

# --- Plotting dengan Plotly ---
st.subheader("Mapping Coal Berdasarkan Tiang dan Sudut Stacking")
fig = go.Figure()

# Palet warna untuk kotak
palette = pc.qualitative.Plotly
n_colors = len(palette)

# Loop untuk membuat setiap rectangle dan anotasi teks
for i, r in df_plot.reset_index(drop=True).iterrows():
    y0 = float(r["sudut_start"])
    y1 = float(r["sudut_end"])
    
    x0, x1 = float(r["tiang_start"]), float(r["tiang_end"])
    color = palette[i % n_colors]

    # Menambahkan bentuk rectangle ke plot
    fig.add_shape(
        type="rect",
        x0=x0, y0=y0, x1=x1, y1=y1,
        line=dict(color=color, width=3),
        fillcolor=color,
        opacity=0.5,
    )
    
    # Menambahkan anotasi teks (nama) di tengah setiap rectangle
    fig.add_annotation(
        x=(x0 + x1) / 2,
        y=(y0 + y1) / 2,
        text=str(r["tipe"]),
        showarrow=False,
        font=dict(size=15, color="black"),
    )

# --- Menambahkan Scatter Plot Transparan untuk Hover ---
# Scatter plot ini tidak terlihat, tetapi memungkinkan fungsionalitas hover pada area rectangle
fig.add_trace(
    go.Scatter(
        # Posisi marker di tengah setiap rectangle
        x=(df_plot["tiang_start"] + df_plot["tiang_end"]) / 2,
        y=(df_plot["sudut_start"] + df_plot["sudut_end"]) / 2,
        mode="markers",
        marker=dict(size=0.1, opacity=0), # Membuat marker tidak terlihat
        hoverinfo="text",
        hovertext=df_plot.apply(
            lambda row: f"<b>Tongkang:</b> {row['tongkang']}<br><b>Ash:</b> {row['Ash_%']:.2f}%<br><b>Sulfur:</b> {row['Sulfur_%']:.2f}%<br><b>Tanggal:</b> {row['tanggal'].strftime('%Y-%m-%d')}",
            axis=1
        ),
        showlegend=False
    )
)

# --- Konfigurasi Sumbu dan Layout Plot ---
# Mengatur sumbu X (Nomor Tiang) dengan rentang kustom dari slider
fig.update_xaxes(
    title="Nomor Tiang", 
    range=[x_min_custom, x_max_custom],
    dtick=1,
    showticklabels=True
)

# Mengatur sumbu Y (Sudut Stacking) dengan rentang kustom dari slider
fig.update_yaxes(
    title="Sudut Stacking (derajat)",
    range=[y_min_custom, y_max_custom],
    dtick=10,
    showticklabels=False,
    showline=True,
    linecolor="grey"
)

# Mengatur tata letak plot secara keseluruhan
fig.update_layout(
    height=600,
    margin=dict(l=10, r=10, t=50, b=10),
    title="Visualisasi Posisi Coal Pile",
    hovermode="closest",
    dragmode=False
)

# Menampilkan plot di Streamlit
st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "zoom", "select", "lasso2d"
        ]
    }
)