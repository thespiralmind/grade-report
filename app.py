import pandas as pd
import streamlit as st

SUBJECTS = ["math", "english", "science"]

st.set_page_config(page_title="Grade Dashboard", page_icon="📊", layout="wide")
st.title("📊 Student Grade Dashboard")

uploaded = st.file_uploader(
    "Upload a CSV file (columns: name, math, english, science)", type="csv"
)

if uploaded is None:
    df = pd.read_csv("grades.csv")
    st.info("Showing sample data. Upload your own CSV to analyze it.")
else:
    df = pd.read_csv(uploaded)

missing = [c for c in ["name"] + SUBJECTS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

df["average"] = df[SUBJECTS].mean(axis=1).round(2)
df["rank"] = df["average"].rank(ascending=False, method="min").astype(int)
df = df.sort_values("rank")

col1, col2, col3 = st.columns(3)
col1.metric("Students", len(df))
col2.metric("Class average", f"{df['average'].mean():.2f}")
col3.metric("Top student", df.iloc[0]["name"])

st.subheader("Ranking")
st.dataframe(df[["rank", "name"] + SUBJECTS + ["average"]], hide_index=True)