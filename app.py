import pandas as pd
import plotly.express as px
import streamlit as st

TEXT = "#1F2937"

# (name, share of full marks needed, soft fill color, darker border color)
LEVEL_SPECS = [
    ("A · Excellent", 0.8, "#D1FAE5", "#047857"),
    ("B · Good", 0.7, "#E0E7FF", "#4338CA"),
    ("C · Fair", 0.6, "#FEF3C7", "#B45309"),
    ("D · Needs support", 0.0, "#FEE2E2", "#B91C1C"),
]


def make_levels(max_score):
    """Turn the level specs into (label, minimum grade, fill, edge) for a given scale."""
    levels = []
    previous_low = None
    for name, share, fill, edge in LEVEL_SPECS:
        low = round(share * max_score, 2)
        if previous_low is None:
            label = f"{name} ({low:g}+)"
        elif share == 0:
            label = f"{name} (<{previous_low:g})"
        else:
            label = f"{name} ({low:g}-{previous_low:g})"
        levels.append((label, low, fill, edge))
        previous_low = low
    return levels


def load_data(uploaded_file):
    """Read the uploaded CSV or Excel file, or the sample file if nothing was uploaded."""
    if uploaded_file is None:
        return pd.read_csv("grades.csv")
    if uploaded_file.name.lower().endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def guess_name_column(data):
    """Pick the most likely column holding student names."""
    for col in data.columns:
        if "name" in str(col).lower():
            return col
    text_cols = [c for c in data.columns if not pd.api.types.is_numeric_dtype(data[c])]
    return text_cols[0] if text_cols else data.columns[0]


def guess_subject_columns(data, name_col):
    """Pick columns that mostly contain numbers (skipping 'No.', 'Total', ...)."""
    skip = {"no", "no.", "id", "#", "rank", "total", "average", "avg", "sum"}
    subjects = []
    for col in data.columns:
        if col == name_col or str(col).strip().lower() in skip:
            continue
        values = data[col].dropna()
        values = values[values.astype(str).str.strip() != ""]
        if values.empty:
            continue
        if pd.to_numeric(values, errors="coerce").notna().mean() >= 0.5:
            subjects.append(col)
    return subjects


def guess_max_score(data, subject_cols):
    """Guess the full marks (10, 20 or 100) from the highest grade in the file."""
    if not subject_cols:
        return 20
    values = pd.concat([pd.to_numeric(data[c], errors="coerce") for c in subject_cols])
    top = values.max()
    for limit in (10, 20, 100):
        if top <= limit:
            return limit
    return 100


def find_data_issues(raw_data, name_col, subject_cols, max_score):
    """List every grade cell the app cannot use, with its spreadsheet row number."""
    has_name = raw_data[name_col].notna()
    rows = []
    for col in subject_cols:
        original = raw_data[col]
        numbers = pd.to_numeric(original, errors="coerce")
        blank = original.isna() | (original.astype(str).str.strip() == "")
        problems = [
            (blank, "Empty"),
            (~blank & numbers.isna(), "Not a number"),
            (numbers.notna() & ((numbers < 0) | (numbers > max_score)),
             f"Outside 0-{max_score:g}"),
        ]
        for mask, problem in problems:
            for idx in raw_data.index[mask & has_name]:
                value = "" if blank[idx] else str(original[idx])
                rows.append({
                    "Row": idx + 2,  # +2: Excel counts from 1 and row 1 is the header
                    "Student": str(raw_data.loc[idx, name_col]).strip(),
                    "Subject": str(col),
                    "Value": value,
                    "Problem": problem,
                })
    return pd.DataFrame(rows, columns=["Row", "Student", "Subject", "Value", "Problem"])


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


def style_table(data):
    """Color the grade cells by level and format the numbers nicely."""
    cols = SUBJECTS + ["average"]
    formats = {s: "{:g}" for s in SUBJECTS}
    formats["average"] = "{:.2f}"
    return data.style.map(grade_color, subset=cols).format(formats, na_rep="–")


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


def join_names(names):
    """Bold names joined like: A, B and C."""
    bold = [f"**{n}**" for n in names]
    return bold[0] if len(bold) == 1 else ", ".join(bold[:-1]) + " and " + bold[-1]


def takeaway_text(subject_means, weak_count):
    """Build the key-takeaways sentence, including ties between subjects."""
    means = subject_means.round(1)  # compare what the user actually sees
    support = f"**{weak_count}** student(s) need support."
    if len(means) == 1:
        return (
            f"**Key takeaways:** the class average in {join_names(means.index)} "
            f"is {means.max():.1f}. {support}"
        )
    if means.max() == means.min():
        return (
            f"**Key takeaways:** all subjects have the same class average "
            f"({means.max():.1f}). {support}"
        )
    best = list(means[means == means.max()].index)
    hardest = list(means[means == means.min()].index)
    best_text = (
        f"the strongest subject is {join_names(best)}"
        if len(best) == 1 else f"the strongest subjects are {join_names(best)}"
    )
    hardest_text = (
        f"the hardest is {join_names(hardest)}"
        if len(hardest) == 1 else f"the hardest are {join_names(hardest)}"
    )
    return (
        f"**Key takeaways:** {best_text} ({means.max():.1f}) and {hardest_text} "
        f"({means.min():.1f}). {support}"
    )


def most_d_sentence(d_counts, total):
    """Say which subject(s) have the most students at level D, including ties."""
    most = max(d_counts.values())
    if most == 0:
        return "💡 No student is at level D in any subject."
    top = [f"**{sub}**" for sub, n in d_counts.items() if n == most]
    if len(d_counts) > 1 and len(top) == len(d_counts):
        return f"💡 Every subject has {most} of {total} students at level D."
    names = top[0] if len(top) == 1 else ", ".join(top[:-1]) + " and " + top[-1]
    each = " each" if len(top) > 1 else ""
    return f"💡 The most students at level D are in {names} ({most} of {total}{each})."


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
st.caption("Upload a CSV or Excel file of grades to see rankings, charts and insights.")

# ---------- Data & settings ----------
with st.expander("📁 Use your own data & settings"):
    left_col, right_col = st.columns(2)

    with left_col:
        uploaded = st.file_uploader(
            "Upload a CSV or Excel file with student names and grades",
            type=["csv", "xlsx"],
        )
        st.download_button(
            label="Download a sample CSV",
            data=pd.read_csv("grades.csv").to_csv(index=False).encode("utf-8"),
            file_name="sample_grades.csv",
            mime="text/csv",
            help="Use this file as a template for your own data.",
        )

    raw = load_data(uploaded)

    with right_col:
        default_name = guess_name_column(raw)
        name_col = st.selectbox(
            "Column with student names",
            list(raw.columns),
            index=list(raw.columns).index(default_name),
        )
        other_cols = [c for c in raw.columns if c != name_col]
        subject_cols = st.multiselect(
            "Columns with grades (one per subject)",
            other_cols,
            default=[c for c in guess_subject_columns(raw, name_col) if c in other_cols],
        )

    score_col, filter_col = st.columns(2)

    with score_col:
        max_score = st.number_input(
            "Maximum score (full marks)",
            min_value=1.0,
            value=float(guess_max_score(raw, subject_cols)),
            step=1.0,
            help="For example 20, 10 or 100. Levels A-D are calculated from this.",
        )

    with filter_col:
        min_avg = st.slider(
            "Minimum average", 0.0, float(max_score), 0.0,
            step=0.5 if max_score <= 20 else 1.0,
            help="Hide students whose average is below this value.",
        )

# ---------- Data ----------
source = "sample data" if uploaded is None else "your uploaded file"

if not subject_cols:
    st.error("Please choose at least one column that contains grades.")
    st.stop()

df = raw[[name_col] + subject_cols].copy()
df = df.rename(columns={name_col: "name"})
df = df.dropna(subset=["name"])
df["name"] = df["name"].astype(str).str.strip()
for col in subject_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")  # text like "ABS" becomes empty
    df[col] = df[col].where((df[col] >= 0) & (df[col] <= max_score))  # impossible grades too
df = df.dropna(subset=subject_cols, how="all")
SUBJECTS = subject_cols

# Levels and colors depend on the maximum score
LEVELS = make_levels(max_score)
FILL = {label: fill for label, _, fill, _ in LEVELS}
EDGE = {label: edge for label, _, _, edge in LEVELS}
PASS_MARK = LEVELS[2][1]  # below this grade means level D

# ---------- Data check ----------
issues = find_data_issues(raw, name_col, subject_cols, max_score)
if not issues.empty:
    st.warning(
        f"⚠️ Data check: {len(issues)} grade cell(s) could not be used and were "
        "treated as missing. A student's average only uses the grades that exist."
    )
    with st.expander("See which cells"):
        st.dataframe(issues, hide_index=True, use_container_width=True)

duplicate_names = df.loc[df["name"].duplicated(), "name"].unique()
if len(duplicate_names) > 0:
    st.warning(
        "⚠️ These names appear more than once: " + ", ".join(duplicate_names)
        + ". They are shown as separate students."
    )

df = add_ranking(df)
df = df[df["average"] >= min_avg]

if df.empty:
    st.warning("No students match this filter.")
    st.stop()

# ---------- Summary ----------
filter_note = f" · filter: average ≥ {min_avg:g}" if min_avg > 0 else ""
st.caption(f"📌 Showing {source} · {len(df)} students{filter_note}")

weak_count = int((df["average"] < PASS_MARK).sum())
subject_means = df[SUBJECTS].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Students", len(df))
col2.metric("Class average", f"{df['average'].mean():.1f} / {max_score:g}")
col3.metric("Top student", df.iloc[0]["name"])
col4.metric(
    "Need support", weak_count,
    help=f"Students with an average below {PASS_MARK:g} (level D)",
)

st.info(takeaway_text(subject_means, weak_count))

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
    st.dataframe(style_table(table), hide_index=True, use_container_width=True)

    st.download_button(
        label="Download results as CSV",
        data=table.to_csv(index=False, float_format="%g").encode("utf-8"),
        file_name="grade_results.csv",
        mime="text/csv",
    )

with tab_charts:
    st.subheader("Performance levels")
    st.caption(
        "How many students got A, B, C or D. The highlighted top bar uses each "
        "student's overall average. Subjects are sorted by class average, lowest first."
    )

    OVERALL = "Overall"
    NO_GRADE = "No grade"
    NO_GRADE_FILL, NO_GRADE_EDGE = "#E5E7EB", "#9CA3AF"

    # Overall first, then the subjects with the lowest class average
    weakest_first = list(subject_means.sort_values().index)
    groups = {OVERALL: df["average"]}
    groups.update({sub: df[sub] for sub in weakest_first})

    rows = []
    for group_name, grades in groups.items():
        counts = grades.apply(get_level).value_counts()
        for label in FILL:
            n = int(counts.get(label, 0))
            rows.append({
                "group": group_name, "level": label,
                "students": n, "text": str(n) if n else "",
            })
        missing_n = int(grades.isna().sum())  # students without a usable grade
        rows.append({
            "group": group_name, "level": NO_GRADE,
            "students": missing_n, "text": str(missing_n) if missing_n else "",
        })
    by_group = pd.DataFrame(rows)

    fig_levels = px.bar(
        by_group, x="students", y="group", color="level", text="text",
        orientation="h", barmode="stack", template="plotly_white",
        color_discrete_map={**FILL, NO_GRADE: NO_GRADE_FILL},
    )
    fig_levels.for_each_trace(
        lambda t: t.update(
            marker_line_color=EDGE.get(t.name, NO_GRADE_EDGE), marker_line_width=1
        )
    )
    fig_levels.update_traces(
        textposition="inside", insidetextanchor="middle", textfont_color=TEXT,
        hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x} student(s)<extra></extra>",
    )
    fig_levels.update_layout(
        showlegend=False, xaxis_title="Number of students", yaxis_title=None
    )
    fig_levels.update_xaxes(range=[0, len(df)])

    # Plotly draws the first category at the bottom, so list them bottom-to-top
    bottom_to_top = weakest_first[::-1] + [OVERALL]
    fig_levels.update_yaxes(
        categoryorder="array",
        categoryarray=bottom_to_top,
        tickvals=bottom_to_top,
        ticktext=weakest_first[::-1] + [f"<b>{OVERALL}</b>"],
        automargin=True,
        ticklabelstandoff=8,
    )

    # Gray band behind the Overall bar plus a dotted line below it
    top = len(bottom_to_top) - 1
    fig_levels.add_hrect(
        y0=top - 0.5, y1=top + 0.5, fillcolor="#F3F4F6", line_width=0, layer="below"
    )
    fig_levels.add_hline(y=top - 0.5, line_dash="dot", line_color="#9CA3AF")

    st.plotly_chart(
        style_fig(fig_levels, height=max(300, 60 * len(groups) + 60)),
        use_container_width=True,
    )

    # One plain-language sentence under the chart
    d_counts = {sub: int((df[sub] < PASS_MARK).sum()) for sub in SUBJECTS}
    st.markdown(most_d_sentence(d_counts, len(df)))
    if (by_group.loc[by_group["level"] == NO_GRADE, "students"] > 0).any():
        st.caption("Gray = students without a usable grade (see the data check above).")

with tab_students:
    st.subheader("Students needing support")
    st.caption(
        f"Students with a D (below {PASS_MARK:g}) in at least one subject or overall. "
        "The last column shows where they scored D."
    )

    # How many D grades are there in each subject?
    d_fill, d_edge = LEVELS[3][2], LEVELS[3][3]
    chips = "".join(
        f'<span style="display:inline-block;background:{d_fill};'
        f'border:1px solid {d_edge};color:{d_edge};border-radius:999px;'
        f'padding:4px 14px;margin:0 8px 8px 0;font-size:14px;">'
        f'<b>{int((df[sub] < PASS_MARK).sum())}</b> with D in {sub}</span>'
        for sub in SUBJECTS
    )
    st.markdown(chips, unsafe_allow_html=True)

    support = df.copy()
    support["D in"] = support[SUBJECTS].apply(
        lambda row: ", ".join(s for s in SUBJECTS if row[s] < PASS_MARK), axis=1
    )
    support["d_count"] = (support[SUBJECTS] < PASS_MARK).sum(axis=1)
    support = support[(support["d_count"] > 0) | (support["average"] < PASS_MARK)]
    support = support.sort_values(["d_count", "average"], ascending=[False, True])

    if support.empty:
        st.success("No student has a D in any subject.")
    else:
        shown = support[["name"] + SUBJECTS + ["average", "D in"]]
        st.dataframe(style_table(shown), hide_index=True, use_container_width=True)