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
    st.subheader("Performance levels")
    st.caption(
        "How many students got A, B, C or D. "
        "The highlighted top bar uses each student's overall average."
    )

    OVERALL = "Overall"

    # Overall first, then one entry per subject
    groups = {OVERALL: df["average"]}
    groups.update({sub: df[sub] for sub in SUBJECTS})

    rows = []
    for group_name, grades in groups.items():
        counts = grades.apply(get_level).value_counts()
        for label in FILL:
            n = int(counts.get(label, 0))
            rows.append({
                "group": group_name, "level": label,
                "students": n, "text": str(n) if n else "",
            })
    by_group = pd.DataFrame(rows)

    fig_levels = px.bar(
        by_group, x="students", y="group", color="level", text="text",
        orientation="h", barmode="stack", template="plotly_white",
        color_discrete_map=FILL,
    )
    fig_levels.for_each_trace(
        lambda t: t.update(marker_line_color=EDGE[t.name], marker_line_width=1)
    )
    fig_levels.update_traces(
        textposition="inside", insidetextanchor="middle", textfont_color=TEXT
    )
    fig_levels.update_layout(
        showlegend=False, xaxis_title="Number of students", yaxis_title=None
    )
    fig_levels.update_xaxes(range=[0, len(df)])

    # Plotly draws the first category at the bottom, so list them bottom-to-top
    bottom_to_top = SUBJECTS[::-1] + [OVERALL]
    fig_levels.update_yaxes(
        categoryorder="array",
        categoryarray=bottom_to_top,
        tickvals=bottom_to_top,
        ticktext=SUBJECTS[::-1] + [f"<b>{OVERALL}</b>"],
    )

    # Gray band behind the Overall bar plus a dotted line below it
    top = len(bottom_to_top) - 1
    fig_levels.add_hrect(
        y0=top - 0.5, y1=top + 0.5, fillcolor="#F3F4F6", line_width=0, layer="below"
    )
    fig_levels.add_hline(y=top - 0.5, line_dash="dot", line_color="#9CA3AF")

    st.plotly_chart(style_fig(fig_levels, height=380), use_container_width=True)

with tab_students:
    st.subheader("Students needing support")
    st.caption(
        "Students with a D (below 12) in at least one subject or overall. "
        "The last column shows where they scored D."
    )

    # How many D grades are there in each subject?
    d_fill, d_edge = LEVELS[3][2], LEVELS[3][3]
    chips = "".join(
        f'<span style="display:inline-block;background:{d_fill};'
        f'border:1px solid {d_edge};color:{d_edge};border-radius:999px;'
        f'padding:4px 14px;margin:0 8px 8px 0;font-size:14px;">'
        f'<b>{int((df[sub] < 12).sum())}</b> with D in {sub}</span>'
        for sub in SUBJECTS
    )
    st.markdown(chips, unsafe_allow_html=True)

    support = df.copy()
    support["D in"] = support[SUBJECTS].apply(
        lambda row: ", ".join(s for s in SUBJECTS if row[s] < 12), axis=1
    )
    support["d_count"] = (support[SUBJECTS] < 12).sum(axis=1)
    support = support[(support["d_count"] > 0) | (support["average"] < 12)]
    support = support.sort_values(["d_count", "average"], ascending=[False, True])

    if support.empty:
        st.success("No student has a D in any subject.")
    else:
        shown = support[["name"] + SUBJECTS + ["average", "D in"]]
        styled_support = shown.style.map(grade_color, subset=SUBJECTS + ["average"])
        styled_support = styled_support.format({"average": "{:.2f}"})
        st.dataframe(styled_support, hide_index=True, use_container_width=True)