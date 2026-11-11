import pandas as pd
import plotly.express as px
import streamlit as st

SUBJECTS = ["math", "english", "science"]

def load_data(uploaded_file):
    """Read the uploaded CSV, or the sample file if nothing was uploaded."""
    if uploaded_file is None:
        return pd.read_csv("grades.csv")
    return pd.read_csv(uploaded_file)


def add_ranking(data):
    """Add 'average' and 'rank' columns and sort by rank."""
    data = data.copy()
    data["average"] = data[SUBJECTS].mean(axis=1).round(2)
    data["rank"] = data["average"].rank(ascending=False, method="min").astype(int)
    return data.sort_values("rank")

st.set_page_config(page_title="Grade Dashboard", page_icon="📊", layout="wide")
st.title("📊 Student Grade Dashboard")

st.sidebar.header("Settings")
uploaded = st.sidebar.file_uploader(
    "Upload a CSV file (columns: name, math, english, science)", type="csv"
)

df = load_data(uploaded)
if uploaded is None:
    st.info("Showing sample data. Upload your own CSV to analyze it.")

missing = [c for c in ["name"] + SUBJECTS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

df = add_ranking(df)

min_avg = st.sidebar.slider("Minimum average", 0.0, 20.0, 0.0, step=0.5)
df = df[df["average"] >= min_avg]

if df.empty:
    st.warning("No students match this filter.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Students", len(df))
col2.metric("Class average", f"{df['average'].mean():.2f}")
col3.metric("Top student", df.iloc[0]["name"])

st.subheader("Ranking")
st.dataframe(df[["rank", "name"] + SUBJECTS + ["average"]], hide_index=True)

csv_data = df[["rank", "name"] + SUBJECTS + ["average"]].to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download results as CSV",
    data=csv_data,
    file_name="grade_results.csv",
    mime="text/csv",
)

st.subheader("Grade distribution")
subject = st.sidebar.selectbox("Choose a subject", SUBJECTS)
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

st.subheader("Compare a student with the class")
student = st.selectbox("Choose a student", df["name"])

student_scores = df[df["name"] == student][SUBJECTS].iloc[0]
class_avg = df[SUBJECTS].mean().round(2)

compare = pd.DataFrame({
    "subject": SUBJECTS * 2,
    "score": list(student_scores) + list(class_avg),
    "who": [student] * len(SUBJECTS) + ["Class average"] * len(SUBJECTS),
})

fig_compare = px.bar(
    compare, x="subject", y="score", color="who",
    barmode="group", range_y=[0, 20],
)
st.plotly_chart(fig_compare, use_container_width=True)