import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import polars as pl
    import altair as alt

    return alt, duckdb, mo, pl


@app.cell
def _(mo):
    mo.md("""
    # AddBiomechanics Explorer

    Explore human movement data from the
    [AddBiomechanics](https://addbiomechanics.org/) dataset using SQL.
    Data was ingested from `.b3d` files into Parquet bundles using
    [MoveDB](https://github.com/SOMA-Bionics/movedb-core).

    ---
    """)
    return


@app.cell
def _(mo, pl):
    mo.md("## Dataset Overview")
    subjects = pl.read_parquet("data/subjects.parquet")
    trials = pl.read_parquet("data/trials.parquet")
    _s = subjects.row(0, named=True)
    _n_walk = trials.filter(pl.col("trial_name").str.contains("walk")).height
    mo.md(
        f"""
        | | |
        |---|---|
        | **Subject** | `{_s['subject_id']}` — {_s['biological_sex']}, {_s['age_years']}y, {_s['mass_kg']}kg, {_s['height_m']}m |
        | **Skeleton** | {_s['num_dofs']} DOFs |
        | **Trials** | {trials.height} total ({_n_walk} walking) |
        | **Tables** | `subjects`, `trials`, `kinematics_summary`, `gait_trajectories` |
        """
    )
    return (trials,)


@app.cell
def _(mo):
    mo.md("""
    ## Query Builder
    """)
    return


@app.cell
def _(mo):
    table_selector = mo.ui.dropdown(
        options=["subjects", "trials", "kinematics_summary", "gait_trajectories"],
        value="kinematics_summary",
        label="Table",
    )
    table_selector
    return (table_selector,)


@app.cell
def _(mo, pl, table_selector, trials):
    _table = table_selector.value

    if _table == "subjects":
        sex_filter = mo.ui.dropdown(
            options=["any", "male", "female"], value="any", label="Sex"
        )
        sex_filter
        filters = {"sex": sex_filter}

    elif _table == "trials":
        _types = sorted(
            trials["trial_name"].str.extract(r"^(\w+?)_\d").unique().sort().to_list()
        )
        trial_type = mo.ui.dropdown(
            options=["any"] + _types, value="any", label="Trial type"
        )
        trial_type
        filters = {"trial_type": trial_type}

    elif _table == "kinematics_summary":
        _dofs = sorted(
            pl.read_parquet("data/kinematics_summary.parquet")["dof_name"].unique().to_list()
        )
        dof_filter = mo.ui.multiselect(
            options=_dofs,
            value=["knee_angle_l", "knee_angle_r"],
            label="DOFs",
        )
        trial_type_k = mo.ui.dropdown(
            options=["any", "walk_fast", "walk_slow", "static"],
            value="any",
            label="Trial type",
        )
        dof_filter
        trial_type_k
        filters = {"dofs": dof_filter, "trial_type": trial_type_k}

    elif _table == "gait_trajectories":
        _dofs = sorted(
            pl.read_parquet("data/gait_trajectories.parquet")["dof_name"].unique().to_list()
        )
        dof_filter_g = mo.ui.multiselect(
            options=_dofs,
            value=["knee_angle_l", "knee_angle_r"],
            label="DOFs",
        )
        trial_type_g = mo.ui.dropdown(
            options=["any", "walk_fast", "walk_slow"],
            value="any",
            label="Trial type",
        )
        agg_mode = mo.ui.dropdown(
            options=["raw", "mean per trial", "mean ± std per trial"],
            value="mean per trial",
            label="Aggregation",
        )
        dof_filter_g
        trial_type_g
        agg_mode
        filters = {"dofs": dof_filter_g, "trial_type": trial_type_g, "agg": agg_mode}

    else:
        filters = {}
    return (filters,)


@app.cell
def _(filters, mo, table_selector):
    _table = table_selector.value

    if _table == "subjects":
        _sql = "SELECT * FROM read_parquet('data/subjects.parquet')"
        if filters["sex"].value != "any":
            _sql += f"\nWHERE biological_sex = '{filters['sex'].value}'"

    elif _table == "trials":
        _sql = "SELECT * FROM read_parquet('data/trials.parquet')"
        if filters["trial_type"].value != "any":
            _sql += f"\nWHERE trial_name LIKE '{filters['trial_type'].value}%'"
        _sql += "\nORDER BY trial_index"

    elif _table == "kinematics_summary":
        _sql = "SELECT * FROM read_parquet('data/kinematics_summary.parquet')"
        _conds = []
        if filters["dofs"].value:
            _dof_list = ", ".join(f"'{d}'" for d in filters["dofs"].value)
            _conds.append(f"dof_name IN ({_dof_list})")
        if filters["trial_type"].value != "any":
            _conds.append(f"trial_name LIKE '{filters['trial_type'].value}%'")
        if _conds:
            _sql += "\nWHERE " + "\n  AND ".join(_conds)
        _sql += "\nORDER BY trial_name, dof_name"

    elif _table == "gait_trajectories":
        _agg = filters["agg"].value
        if _agg == "raw":
            _sql = "SELECT * FROM read_parquet('data/gait_trajectories.parquet')"
        elif _agg == "mean per trial":
            _sql = (
                "SELECT trial_name, dof_name, pct,\n"
                "  ROUND(AVG(angle_deg), 2) AS mean_angle_deg\n"
                "FROM read_parquet('data/gait_trajectories.parquet')"
            )
        else:
            _sql = (
                "SELECT trial_name, dof_name, pct,\n"
                "  ROUND(AVG(angle_deg), 2) AS mean_angle_deg,\n"
                "  ROUND(STDDEV(angle_deg), 2) AS std_angle_deg\n"
                "FROM read_parquet('data/gait_trajectories.parquet')"
            )
        _conds = []
        if filters["dofs"].value:
            _dof_list = ", ".join(f"'{d}'" for d in filters["dofs"].value)
            _conds.append(f"dof_name IN ({_dof_list})")
        if filters["trial_type"].value != "any":
            _conds.append(f"trial_name LIKE '{filters['trial_type'].value}%'")
        if _conds:
            _sql += "\nWHERE " + "\n  AND ".join(_conds)
        if _agg != "raw":
            _sql += "\nGROUP BY trial_name, dof_name, pct"
        _sql += "\nORDER BY trial_name, dof_name, pct"

    else:
        _sql = "-- select a table above"

    sql_editor = mo.ui.text_area(value=_sql, label="SQL", rows=10)
    sql_editor
    return (sql_editor,)


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="Run query")
    run_btn
    return (run_btn,)


@app.cell
def _(duckdb, mo, run_btn, sql_editor):
    _sql = sql_editor.value.strip()
    if run_btn.value and _sql:
        try:
            _result = duckdb.sql(_sql).pl()
            if _result.height == 0:
                mo.md("*Query returned 0 rows.*")
            else:
                mo.md(f"**{_result.height} rows** returned.")
                mo.ui.table(_result, page_size=20)
        except Exception as e:
            mo.md(f"**Error:** `{e}`")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Gait Trajectories
    """)
    return


@app.cell
def _(mo, pl):
    trajectories = pl.read_parquet("data/gait_trajectories.parquet")
    _dof_options = sorted(trajectories["dof_name"].unique().to_list())
    traj_dof_selector = mo.ui.multiselect(
        options=_dof_options,
        value=["knee_angle_l", "knee_angle_r", "hip_flexion_l", "hip_flexion_r"],
        label="Select DOFs",
    )
    traj_dof_selector
    return traj_dof_selector, trajectories


@app.cell
def _(mo):
    traj_mode = mo.ui.switch(
        value=False,
        label="Show mean ± std across strides",
    )
    traj_mode
    return (traj_mode,)


@app.cell
def _(alt, mo, pl, traj_dof_selector, traj_mode, trajectories):
    _df = trajectories.filter(pl.col("dof_name").is_in(traj_dof_selector.value))

    if traj_mode.value:
        _agg = (
            _df.group_by("trial_name", "dof_name", "pct")
            .agg(
                pl.col("angle_deg").mean().alias("mean_deg"),
                pl.col("angle_deg").std().alias("std_deg"),
            )
            .with_columns(
                (pl.col("mean_deg") - pl.col("std_deg")).alias("lo"),
                (pl.col("mean_deg") + pl.col("std_deg")).alias("hi"),
            )
            .sort("trial_name", "dof_name", "pct")
        )
        _base = alt.Chart(_agg).encode(
            x=alt.X("pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 99])),
            color="trial_name:N",
        )
        _lines = _base.mark_line().encode(
            y=alt.Y("mean_deg:Q", title="Angle (deg)"),
        )
        _band = _base.mark_area(opacity=0.15).encode(y="lo:Q", y2="hi:Q")
        _chart = (_band + _lines).facet(
            row=alt.Row("dof_name:N", title=None),
        ).properties(title="Mean ± 1 SD across strides")
    else:
        _chart = (
            alt.Chart(_df)
            .mark_line(opacity=0.3)
            .encode(
                x=alt.X("pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 99])),
                y=alt.Y("angle_deg:Q", title="Angle (deg)"),
                color="trial_name:N",
                detail="trial_name:N",
                facet=alt.Facet("dof_name:N", columns=2),
            )
        )

    mo.ui.altair_chart(_chart.resolve_scale(y="independent"))
    return


@app.cell
def _(mo):
    mo.md("""
    ---

    **About:** [MoveDB](https://github.com/SOMA-Bionics/movedb-core) ·
    [DuckDB](https://duckdb.org/) ·
    [Marimo](https://marimo.io/) ·
    [AddBiomechanics](https://addbiomechanics.org/)
    """)
    return


if __name__ == "__main__":
    app.run()
