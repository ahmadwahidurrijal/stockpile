import streamlit as st
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

url = "https://docs.google.com/spreadsheets/d/1RNOBQG4m-zpdA2qAf1E1nUAI9QKJMUYGUYwUgIA-jrM/edit?gid=328753631#gid=328753631"

conn = st.connection("gsheets", type=GSheetsConnection)
data1 = conn.read(spreadsheet=url, usecols=[0,1,2,5])

st.set_page_config(page_title="Kotak Skala", layout="centered")

# Skala
x_min, x_max = 1, 20
y_min, y_max = 1, 4

# Bikin figure kosong
fig = go.Figure()

# Tambahkan kotak (rectangle)
fig.add_shape(
    type="rect",
    x0=x_min, y0=y_min, x1=x_max, y1=y_max,
    line=dict(color="RoyalBlue", width=2),
    fillcolor="LightSkyBlue", opacity=0.4,
    
)

# Atur axis sesuai skala
fig.update_xaxes(range=[0, 21], title="Panjang (1–20)")
fig.update_yaxes(range=[0, 5], title="Lebar")

fig.update_layout(
    title="Kotak Skala 1–20 x 1–4",
    width=800,
    height=400,
    margin=dict(l=20, r=20, t=50, b=20),
)

st.plotly_chart(fig, use_container_width=True)
