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


import plotly.express as px

st.subheader("Grade distribution")
subject = st.selectbox("Choose a subject", SUBJECTS)
fig_hist = px.histogram(df, x=subject, nbins=10, range_x=[0, 20])
fig_hist.update_layout(xaxis_title="Grade", yaxis_title="Number of students")
st.plotly_chart(fig_hist, use_container_width=True)

st.subheader("Class average by subject")
avg_by_subject = df[SUBJECTS].mean().round(2).reset_index()
avg_by_subject.columns = ["subject", "average"]
fig_bar = px.bar(avg_by_subject, x="subject", y="average", text="average", range_y=[0, 20])
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Students needing support (average below 12)")
weak = df[df["average"] < 12][["name", "average"]]
if weak.empty:
    st.success("No students below 12.")
else:
    st.dataframe(weak, hide_index=True)