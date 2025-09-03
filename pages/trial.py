import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import plotly.colors as pc
import pandas as pd

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Rectangles from Google Sheet", layout="wide")

# ===================== S U M B E R   D A T A =====================
# URL 1 (lama) untuk mapping/rectangles
GFORM_URL = "https://docs.google.com/spreadsheets/d/1mV-POsp6EXiQofywsSr7q8r8nfKw9_SyU8rZ84AUJvI/edit?gid=711561672#gid=711561672"

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
df = read_sheet(GFORM_URL)

st.subheader("Data Dari GForm")
kolom_tampil = ["Timestamp", "Grup", "Tiang Awal", "Tiang Akhir", "Nama Tongkang", "Ada Stacking?", "Tipe Coal", "Sudut Stacking", "Ketinggian Stacking", "Ketinggian pile"]
st.dataframe(
    df[[c for c in kolom_tampil if c in df.columns]],
    use_container_width=True
)
