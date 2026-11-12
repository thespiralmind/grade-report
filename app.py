import pandas as pd
import plotly.express as px
import streamlit as st

SUBJECTS = ["math", "english", "science"]
PRIMARY = "#4F46E5"

LEVELS = [
    ("A · Excellent (16+)", 16, "#10B981"),
    ("B · Good (14-16)", 14, "#4F46E5"),
    ("C · Fair (12-14)", 12, "#F59E0B"),
    ("D · Needs support (<12)", 0, "#EF4444"),
]

SOFT_COLORS = ["#D1FAE5", "#E0E7FF", "#FEF3C7", "#FEE2E2"]


def get_level(avg):
    """Return the performance level name for an average grade."""
    for label, minimum, _ in LEVELS:
        if avg >= minimum:
            return label

def show_legend(soft=False):
    """Show a small color guide: a colored square and the level name."""
    colors = SOFT_COLORS if soft else [level[2] for level in LEVELS]
    items = []
    for (label, _, _), color in zip(LEVELS, colors):
        square = (
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};border-radius:3px;border:1px solid #D1D5DB;'
            f'margin-right:6px;"></span>'
        )
        items.append(f"{square}{label}")
    st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;".join(items), unsafe_allow_html=True)

def grade_color(value):
    """Return a soft background color for a grade cell."""
    if value >= 16:
        return "background-color: #D1FAE5"  # green
    if value >= 14:
        return "background-color: #E0E7FF"  # blue
    if value >= 12:
        return "background-color: #FEF3C7"  # yellow
    return "background-color: #FEE2E2"      # red

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

def style_fig(fig, height=360):
    """Apply a consistent look to every chart."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(size=14, color="#1F2937"),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, title_text="",
        ),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor="#D1D5DB")
    fig.update_yaxes(gridcolor="#E5E7EB", zeroline=False)
    return fig

st.set_page_config(page_title="Grade Dashboard", page_icon="📊", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background-color: #F3F4F6;
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #E5E7EB;
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("📊 Student Grade Dashboard")
st.caption("Upload a CSV of grades to see rankings, charts and insights.")

# ---------- Sidebar ----------
st.sidebar.header("Settings")
uploaded = st.sidebar.file_uploader(
    "Upload a CSV file (columns: name, math, english, science)", type="csv"
)
min_avg = st.sidebar.slider(
    "Minimum average", 0.0, 20.0, 0.0, step=0.5,
    help="Hide students whose average is below this value.",
)
# ---------- Data ----------
df = load_data(uploaded)
if uploaded is None:
    st.info("Showing sample data. Upload your own CSV to analyze it.")

missing = [c for c in ["name"] + SUBJECTS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

df = add_ranking(df)
df = df[df["average"] >= min_avg]

if df.empty:
    st.warning("No students match this filter.")
    st.stop()

# ---------- Summary cards ----------
col1, col2, col3 = st.columns(3)
col1.metric("Students", len(df))
col2.metric("Class average", f"{df['average'].mean():.2f}")
col3.metric("Top student", df.iloc[0]["name"])

# ---------- Tabs ----------
tab_overview, tab_charts, tab_students = st.tabs(["Overview", "Charts", "Students"])

with tab_overview:
    st.subheader("Ranking")
    table = df[["rank", "name"] + SUBJECTS + ["average"]]
    styled = table.style.map(grade_color, subset=SUBJECTS + ["average"])
    styled = styled.format({"average": "{:.2f}"})
    st.dataframe(styled, hide_index=True, use_container_width=True)
    show_legend(soft=True)

    st.download_button(
        label="Download results as CSV",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="grade_results.csv",
        mime="text/csv",
    )

with tab_charts:
    left, right = st.columns(2)

    with left:
       
        st.subheader("Performance levels")
        level_counts = df["average"].apply(get_level).value_counts()
        level_counts = level_counts.reindex([l[0] for l in LEVELS], fill_value=0)
        level_counts = level_counts.reset_index()
        level_counts.columns = ["level", "students"]

        fig_levels = px.pie(
            level_counts, names="level", values="students", hole=0.55,
            color="level", color_discrete_map={l[0]: l[2] for l in LEVELS},
        )
        fig_levels.update_traces(textinfo="value", sort=False)
        fig_levels.add_annotation(
            text=f"<b>{len(df)}</b><br>students", showarrow=False, font=dict(size=18)
        )
        fig_levels.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig_levels), use_container_width=True)
        show_legend()

    with right:
        st.subheader("Class average by subject")
        avg_by_subject = df[SUBJECTS].mean().round(2).reset_index()
        avg_by_subject.columns = ["subject", "average"]
        fig_bar = px.bar(
            avg_by_subject, x="subject", y="average", text="average", range_y=[0, 20],
            color_discrete_sequence=[PRIMARY], template="plotly_white",
        )
        fig_bar.update_traces(textposition="outside", cliponaxis=False)
        fig_bar.update_layout(yaxis_title=None, xaxis_title=None)
        st.plotly_chart(style_fig(fig_bar), use_container_width=True)

with tab_students:
    st.subheader("All students at a glance")
    st.caption("Each row is a student, each column a subject. Red means weak, green means strong.")

    heat = df.set_index("name")[SUBJECTS]
    fig_heat = px.imshow(
        heat, text_auto=True, aspect="auto",
        color_continuous_scale=["#EF4444", "#FDE68A", "#10B981"],
        zmin=10, zmax=20,
    )
    fig_heat.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None)
    fig_heat.update_yaxes(dtick=1)
    st.plotly_chart(
        style_fig(fig_heat, height=max(360, 30 * len(df))),
        use_container_width=True,
    )

    st.subheader("Students needing support (average below 12)")
    weak = df[df["average"] < 12][["name", "average"]]
    if weak.empty:
        st.success("No students below 12.")
    else:
        st.dataframe(weak, hide_index=True, use_container_width=True)