import pandas as pd
import plotly.express as px
import streamlit as st

SUBJECTS = ["math", "english", "science"]
TEXT = "#1F2937"

# (label, minimum grade, soft fill color, darker border color)
LEVELS = [
    ("A · Excellent (16+)", 16, "#D1FAE5", "#047857"),
    ("B · Good (14-16)", 14, "#E0E7FF", "#4338CA"),
    ("C · Fair (12-14)", 12, "#FEF3C7", "#B45309"),
    ("D · Needs support (<12)", 0, "#FEE2E2", "#B91C1C"),
]
FILL = {label: fill for label, _, fill, _ in LEVELS}
EDGE = {label: edge for label, _, _, edge in LEVELS}


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


def get_level(grade):
    """Return the level name (A-D) for a grade."""
    for label, minimum, _, _ in LEVELS:
        if grade >= minimum:
            return label


def grade_color(value):
    """Return the soft background color for a grade cell."""
    for _, minimum, fill, _ in LEVELS:
        if value >= minimum:
            return f"background-color: {fill}"


def show_legend():
    """Show the color guide: a small colored square and the level name."""
    items = []
    for label, _, fill, edge in LEVELS:
        square = (
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{fill};border:1px solid {edge};border-radius:3px;'
            f'margin-right:6px;"></span>'
        )
        items.append(f"{square}{label}")
    st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;".join(items), unsafe_allow_html=True)


def style_fig(fig, height=360):
    """Apply a consistent look to every chart."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(size=14, color=TEXT),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
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

# ---------- Data & filters ----------
with st.expander("📁 Use your own data & filters"):
    upload_col, filter_col = st.columns(2)

    with upload_col:
        uploaded = st.file_uploader(
            "Upload a CSV file (columns: name, math, english, science)", type="csv"
        )
        st.download_button(
            label="Download a sample CSV",
            data=pd.read_csv("grades.csv").to_csv(index=False).encode("utf-8"),
            file_name="sample_grades.csv",
            mime="text/csv",
            help="Use this file as a template for your own data.",
        )

    with filter_col:
        min_avg = st.slider(
            "Minimum average", 0.0, 20.0, 0.0, step=0.5,
            help="Hide students whose average is below this value.",
        )

# ---------- Data ----------
df = load_data(uploaded)
source = "sample data" if uploaded is None else "your uploaded file"

missing = [c for c in ["name"] + SUBJECTS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

df = add_ranking(df)
df = df[df["average"] >= min_avg]

if df.empty:
    st.warning("No students match this filter.")
    st.stop()

# ---------- Summary ----------
filter_note = f" · filter: average ≥ {min_avg}" if min_avg > 0 else ""
st.caption(f"📌 Showing {source} · {len(df)} students{filter_note}")

weak_count = int((df["average"] < 12).sum())
subject_means = df[SUBJECTS].mean()
best = subject_means.idxmax()
hardest = subject_means.idxmin()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Students", len(df))
col2.metric("Class average", f"{df['average'].mean():.2f} / 20")
col3.metric("Top student", df.iloc[0]["name"])
col4.metric("Need support", weak_count, help="Students with an average below 12 (level D)")

st.info(
    f"**Key takeaways:** the strongest subject is **{best}** "
    f"({subject_means[best]:.1f}) and the hardest is **{hardest}** "
    f"({subject_means[hardest]:.1f}). **{weak_count}** student(s) need support."
)

# ---------- Color guide (applies to every tab) ----------
st.caption("How to read the colors (grade level):")
show_legend()

# ---------- Tabs ----------
tab_overview, tab_charts, tab_students = st.tabs(
    ["📋 Ranking", "📊 Charts", "🔍 Who needs help"]
)

with tab_overview:
    st.subheader("Ranking")
    st.caption("Every grade is colored by its level, so strong and weak results stand out.")
    table = df[["rank", "name"] + SUBJECTS + ["average"]]
    styled = table.style.map(grade_color, subset=SUBJECTS + ["average"])
    styled = styled.format({"average": "{:.2f}"})
    st.dataframe(styled, hide_index=True, use_container_width=True)

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
        st.caption("How many students fall into each level, based on their overall average.")
        level_counts = df["average"].apply(get_level).value_counts()
        level_counts = level_counts.reindex(list(FILL), fill_value=0).reset_index()
        level_counts.columns = ["level", "students"]

        fig_levels = px.pie(
            level_counts, names="level", values="students", hole=0.55,
            color="level", color_discrete_map=FILL,
        )
        fig_levels.update_traces(
            textinfo="value", sort=False, textfont_color=TEXT,
            marker_line_color=[EDGE[lvl] for lvl in level_counts["level"]],
            marker_line_width=2,
        )
        fig_levels.update_layout(showlegend=False)
        fig_levels.add_annotation(
            text=f"<b>{len(df)}</b><br>students", showarrow=False,
            font=dict(size=18, color=TEXT),
        )
        st.plotly_chart(style_fig(fig_levels), use_container_width=True)

    with right:
        st.subheader("Performance by subject")
        st.caption("For each subject: how many students got A, B, C or D.")
        rows = []
        for sub in SUBJECTS:
            counts = df[sub].apply(get_level).value_counts()
            for label in FILL:
                n = int(counts.get(label, 0))
                rows.append({
                    "subject": sub, "level": label,
                    "students": n, "text": str(n) if n else "",
                })
        by_subject = pd.DataFrame(rows)

        fig_subjects = px.bar(
            by_subject, x="students", y="subject", color="level", text="text",
            orientation="h", barmode="stack", template="plotly_white",
            color_discrete_map=FILL,
            category_orders={"level": list(FILL)},
        )
        fig_subjects.for_each_trace(
            lambda t: t.update(marker_line_color=EDGE[t.name], marker_line_width=1.5)
        )
        fig_subjects.update_traces(textposition="inside", textfont_color=TEXT)
        fig_subjects.update_layout(
            showlegend=False, xaxis_title="Number of students", yaxis_title=None
        )
        st.plotly_chart(style_fig(fig_subjects), use_container_width=True)

with tab_students:
    st.subheader("All students at a glance")
    st.caption("Each row is a student and each column is a subject. The color shows the level.")

    heat = df.set_index("name")[SUBJECTS]
    # Hard color steps so the heatmap uses exactly the A-D colors (scale 0-20)
    scale = [
        [0.0, FILL[LEVELS[3][0]]], [0.6, FILL[LEVELS[3][0]]],
        [0.6, FILL[LEVELS[2][0]]], [0.7, FILL[LEVELS[2][0]]],
        [0.7, FILL[LEVELS[1][0]]], [0.8, FILL[LEVELS[1][0]]],
        [0.8, FILL[LEVELS[0][0]]], [1.0, FILL[LEVELS[0][0]]],
    ]
    fig_heat = px.imshow(
        heat, text_auto=True, aspect="auto",
        color_continuous_scale=scale, zmin=0, zmax=20,
    )
    fig_heat.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None)
    fig_heat.update_yaxes(dtick=1)
    st.plotly_chart(
        style_fig(fig_heat, height=max(360, 30 * len(df))),
        use_container_width=True,
    )

    st.subheader("Students needing support (level D)")
    st.caption("Students whose overall average is below 12.")
    weak = df[df["average"] < 12][["name", "average"]]
    if weak.empty:
        st.success("No students below 12.")
    else:
        st.dataframe(weak, hide_index=True, use_container_width=True)