import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import polars as pl
    import altair as alt
    import numpy as np
    from pathlib import Path

    return Path, alt, mo, np, pl


@app.cell
def _(Path):
    from movedb.adapters.b3d_catalog import create_b3d_catalog
    conn = create_b3d_catalog(Path("data"), Path("catalog.duckdb"))
    return (conn,)


@app.cell
def _(conn, mo):
    subjects = conn.execute("SELECT * FROM subjects").pl()
    trials = conn.execute("SELECT * FROM trials").pl()
    _n = subjects["study"].n_unique()
    _s = subjects.height
    _t = trials.height
    _f = trials["num_frames"].sum()
    mo.md(f"# AddBiomechanics Explorer\n\n{_n} studies · {_s} subjects · {_t} trials · {_f:,} frames")
    return subjects, trials


@app.cell
def _(mo):
    signal = mo.ui.dropdown(
        options=["kinematics", "markers", "grf", "forceplates"],
        value="kinematics",
        label="1. Signal",
    )
    signal
    return (signal,)


@app.cell
def _(mo, subjects):
    study = mo.ui.multiselect(
        options=sorted(subjects["study"].unique().to_list()),
        value=[],
        label="2. Studies (empty = all)",
    )
    study
    return (study,)


@app.cell
def _(mo, pl, study, subjects):
    _df = subjects
    if study.value:
        _df = _df.filter(pl.col("study").is_in(study.value))
    subject = mo.ui.multiselect(
        options=sorted(_df["subject_id"].unique().to_list()),
        value=[],
        label="3. Subjects (empty = all in study)",
    )
    subject
    return (subject,)


@app.cell
def _(mo, pl, study, subject, subjects, trials):
    _df = trials
    if subject.value:
        _df = _df.filter(pl.col("subject_id").is_in(subject.value))
    elif study.value:
        _sub_ids = subjects.filter(pl.col("study").is_in(study.value))["subject_id"].to_list()
        _df = _df.filter(pl.col("subject_id").is_in(_sub_ids))
    trial = mo.ui.multiselect(
        options=sorted(_df["trial_name"].unique().to_list()),
        value=[],
        label="4. Trials (empty = all for selected subjects)",
    )
    trial
    return (trial,)


@app.cell
def _(conn, mo, signal, study, subject, trial):
    _sig = signal.value

    # Build base filter for the selected signal
    _wheres = []
    if study.value:
        _s_list = ", ".join(f"'{s}'" for s in study.value)
        _wheres.append(f"s.study IN ({_s_list})")
    if subject.value:
        _sub_list = ", ".join(f"'{s}'" for s in subject.value)
        _wheres.append(f"k.subject_id IN ({_sub_list})")
    if trial.value:
        _t_list = ", ".join(f"'{t}'" for t in trial.value)
        _wheres.append(f"k.trial_name IN ({_t_list})")

    _where_clause = ("WHERE " + " AND ".join(_wheres)) if _wheres else ""

    if _sig == "kinematics":
        _opts = conn.execute(f"""
            SELECT DISTINCT k.dof_name FROM kinematics k
            JOIN subjects s ON k.subject_id = s.subject_id
            {_where_clause}
            ORDER BY k.dof_name
        """).pl()["dof_name"].to_list()
        signal_param = mo.ui.multiselect(
            options=_opts,
            value=[v for v in ["knee_angle_l", "knee_angle_r"] if v in _opts],
            label="5. DOFs",
        )
    elif _sig == "markers":
        _opts = conn.execute(f"""
            SELECT DISTINCT k.marker_name FROM markers k
            JOIN subjects s ON k.subject_id = s.subject_id
            {_where_clause}
            ORDER BY k.marker_name
        """).pl()["marker_name"].to_list()
        signal_param = mo.ui.multiselect(
            options=_opts[:20],
            value=[],
            label="5. Markers (first 20 shown)",
        )
    elif _sig == "grf":
        _opts = conn.execute(f"""
            SELECT DISTINCT k.body_name FROM grf k
            JOIN subjects s ON k.subject_id = s.subject_id
            {_where_clause}
            ORDER BY k.body_name
        """).pl()["body_name"].to_list()
        signal_param = mo.ui.multiselect(
            options=_opts,
            value=_opts,
            label="5. Bodies",
        )
    else:
        _opts = conn.execute(f"""
            SELECT DISTINCT k.fp_name FROM forceplates k
            JOIN subjects s ON k.subject_id = s.subject_id
            {_where_clause}
            ORDER BY k.fp_name
        """).pl()["fp_name"].to_list()
        signal_param = mo.ui.multiselect(
            options=_opts,
            value=_opts,
            label="5. Force plates",
        )

    signal_param
    return (signal_param,)


@app.cell
def _(conn, mo):
    # Subject parameter filters
    _sex_options = conn.execute("SELECT DISTINCT biological_sex FROM subjects WHERE biological_sex IS NOT NULL ORDER BY biological_sex").pl()["biological_sex"].to_list()
    sex_filter = mo.ui.multiselect(
        options=_sex_options,
        value=[],
        label="Biological sex (empty = any)",
    )

    _mass_stats = conn.execute("SELECT MIN(mass_kg) AS min_m, MAX(mass_kg) AS max_m FROM subjects WHERE mass_kg IS NOT NULL").fetchone()
    mass_filter = mo.ui.range_slider(
        start=float(_mass_stats[0]) if _mass_stats[0] else 0,
        stop=float(_mass_stats[1]) if _mass_stats[1] else 200,
        step=1.0,
        value=(float(_mass_stats[0]) if _mass_stats[0] else 0, float(_mass_stats[1]) if _mass_stats[1] else 200),
        label="Mass (kg)",
    )

    _height_stats = conn.execute("SELECT MIN(height_m) AS min_h, MAX(height_m) AS max_h FROM subjects WHERE height_m IS NOT NULL").fetchone()
    height_filter = mo.ui.range_slider(
        start=float(_height_stats[0]) if _height_stats[0] else 0.5,
        stop=float(_height_stats[1]) if _height_stats[1] else 2.5,
        step=0.01,
        value=(float(_height_stats[0]) if _height_stats[0] else 0.5, float(_height_stats[1]) if _height_stats[1] else 2.5),
        label="Height (m)",
    )

    _age_stats = conn.execute("SELECT MIN(age_years) AS min_a, MAX(age_years) AS max_a FROM subjects WHERE age_years IS NOT NULL").fetchone()
    age_filter = mo.ui.range_slider(
        start=int(_age_stats[0]) if _age_stats[0] else 0,
        stop=int(_age_stats[1]) if _age_stats[1] else 100,
        step=1,
        value=(int(_age_stats[0]) if _age_stats[0] else 0, int(_age_stats[1]) if _age_stats[1] else 100),
        label="Age (years)",
    )

    mo.md("### Subject Filters")
    mo.hstack([sex_filter, mass_filter, height_filter, age_filter], wrap=True)
    return age_filter, height_filter, mass_filter, sex_filter


@app.cell
def _(mo):
    trial_limit = mo.ui.text(
        value="100",
        label="Max trials (empty = no limit)",
    )
    trial_limit
    return (trial_limit,)


@app.cell
def _(
    age_filter,
    height_filter,
    mass_filter,
    mo,
    sex_filter,
    signal,
    signal_param,
    study,
    subject,
    trial,
    trial_limit,
):
    _sig = signal.value

    # Column definitions per signal
    _select_cols = {
        "kinematics": "k.frame, k.time, k.trial_name, k.dof_name, k.pos, k.vel, k.acc, k.tau",
        "markers": "k.frame, k.time, k.trial_name, k.marker_name, k.x, k.y, k.z, k.residual",
        "grf": "k.frame, k.time, k.trial_name, k.body_name, k.contact, k.fx, k.fy, k.fz, k.copx, k.copy, k.copz",
        "forceplates": "k.frame, k.time, k.trial_name, k.fp_name, k.variable, k.axis, k.value",
    }
    _param_col = {
        "kinematics": "k.dof_name",
        "markers": "k.marker_name",
        "grf": "k.body_name",
        "forceplates": "k.fp_name",
    }

    # Build WHERE clauses for trials/data
    _wheres = []
    if study.value:
        _s_list = ", ".join(f"'{s}'" for s in study.value)
        _wheres.append(f"s.study IN ({_s_list})")
    if subject.value:
        _sub_list = ", ".join(f"'{s}'" for s in subject.value)
        _wheres.append(f"k.subject_id IN ({_sub_list})")
    if trial.value:
        _t_list = ", ".join(f"'{t}'" for t in trial.value)
        _wheres.append(f"k.trial_name IN ({_t_list})")
    if signal_param.value:
        _p_list = ", ".join(f"'{p}'" for p in signal_param.value)
        _wheres.append(f"{_param_col[_sig]} IN ({_p_list})")

    # Subject parameter filters
    if sex_filter.value:
        _sex_list = ", ".join(f"'{sx}'" for sx in sex_filter.value)
        _wheres.append(f"s.biological_sex IN ({_sex_list})")
    if mass_filter.value[0] > mass_filter.start or mass_filter.value[1] < mass_filter.stop:
        _wheres.append(f"s.mass_kg BETWEEN {mass_filter.value[0]} AND {mass_filter.value[1]}")
    if height_filter.value[0] > height_filter.start or height_filter.value[1] < height_filter.stop:
        _wheres.append(f"s.height_m BETWEEN {height_filter.value[0]} AND {height_filter.value[1]}")
    if age_filter.value[0] > age_filter.start or age_filter.value[1] < age_filter.stop:
        _wheres.append(f"s.age_years BETWEEN {int(age_filter.value[0])} AND {int(age_filter.value[1])}")

    _where = ("WHERE " + "\n  AND ".join(_wheres)) if _wheres else ""
    _limit_clause = f"LIMIT {trial_limit.value.strip()}" if trial_limit.value.strip() else ""

    # Query matching trials with metadata
    _sql = f"""SELECT DISTINCT t.trial_name, t.subject_id, t.num_frames, t.duration_s, s.study,
           s.biological_sex, s.mass_kg, s.height_m, s.age_years
    FROM trials t
    JOIN subjects s ON t.subject_id = s.subject_id
    JOIN {_sig} k ON k.trial_name = t.trial_name AND k.subject_id = t.subject_id
    {_where}
    ORDER BY s.study, t.subject_id, t.trial_name
    {_limit_clause}"""

    sql_editor = mo.ui.text_area(value=_sql, label="SQL (editable)", rows=14)
    sql_editor
    return (sql_editor,)


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="Run query")
    run_btn
    return (run_btn,)


@app.cell
def _(
    age_filter,
    conn,
    height_filter,
    mass_filter,
    mo,
    run_btn,
    sex_filter,
    sql_editor,
):
    query_result = None
    if run_btn.value:
        try:
            query_result = conn.execute(sql_editor.value.strip()).pl()
            if query_result.height:
                _n_trials = query_result.height
                _n_frames = query_result["num_frames"].sum()
                _n_subjects = query_result["subject_id"].n_unique()

                # Build summary of subject filters applied
                _filter_parts = []
                if sex_filter.value:
                    _filter_parts.append(f"sex={', '.join(sex_filter.value)}")
                if mass_filter.value[0] > mass_filter.start or mass_filter.value[1] < mass_filter.stop:
                    _filter_parts.append(f"mass={mass_filter.value[0]:.0f}-{mass_filter.value[1]:.0f}kg")
                if height_filter.value[0] > height_filter.start or height_filter.value[1] < height_filter.stop:
                    _filter_parts.append(f"height={height_filter.value[0]:.2f}-{height_filter.value[1]:.2f}m")
                if age_filter.value[0] > age_filter.start or age_filter.value[1] < age_filter.stop:
                    _filter_parts.append(f"age={int(age_filter.value[0])}-{int(age_filter.value[1])}yr")

                _filter_str = f" ({', '.join(_filter_parts)})" if _filter_parts else ""
                _output = mo.md(f"**{_n_trials} trials** from **{_n_subjects} subjects** ({_n_frames:,} frames){_filter_str}")
            else:
                _output = mo.md("*No trials match the current filters*")
        except Exception as e:
            _output = mo.md(f"**Error:** `{e}`")
    else:
        _output = mo.md("*Click **Run query** to find matching trials*")
    _output
    return (query_result,)


@app.cell
def _(mo, query_result):
    if query_result is not None and query_result.height:
        _output = mo.ui.table(query_result, page_size=20)
    else:
        _output = mo.md("")
    _output
    return


@app.cell
def _(mo):
    mo.md("""
    ## Plot
    """)
    return


@app.cell
def _(mo, query_result, signal):
    if query_result is None or query_result.height == 0:
        plot_kind = mo.ui.dropdown(options=["(no data)"], value="(no data)", label="Plot type")
    elif signal.value == "markers":
        plot_kind = mo.ui.dropdown(
            options=["individual trials", "mean ± SD", "gait cycle normalized", "3D scatter (x/y/z)"],
            value="gait cycle normalized",
            label="Plot type",
        )
    else:
        plot_kind = mo.ui.dropdown(
            options=["individual trials", "mean ± SD", "gait cycle normalized"],
            value="gait cycle normalized",
            label="Plot type",
        )
    plot_kind
    return (plot_kind,)


@app.cell
def _(alt, conn, mo, np, pl, plot_kind, query_result, signal, signal_param):
    if query_result is None or query_result.height == 0:
        _output = mo.md("*Run a query above to see a plot.*")
    elif plot_kind.value == "(no data)":
        _output = mo.md("*Select a plot type.*")
    else:
        with mo.status.spinner(subtitle="Generating plot..."):
            _sig = signal.value
            _kind = plot_kind.value

            # Build trial filter from matched trials
            _trial_list = ", ".join(f"'{t}'" for t in query_result["trial_name"].to_list())
            _trial_filter = f"trial_name IN ({_trial_list})"

            # Fetch frame data for matched trials
            if _sig == "kinematics":
                _dof_filter = ""
                if signal_param.value:
                    _dofs = ", ".join(f"'{d}'" for d in signal_param.value)
                    _dof_filter = f"AND dof_name IN ({_dofs})"
                _df = conn.execute(f"""
                    SELECT frame, time, trial_name, dof_name, pos
                    FROM kinematics
                    WHERE {_trial_filter} {_dof_filter}
                    ORDER BY trial_name, frame
                """).pl()
                _param_col = "dof_name"
                _y_col = "pos"
                _y_title = "Position (rad)"
            elif _sig == "markers":
                _marker_filter = ""
                if signal_param.value:
                    _markers = ", ".join(f"'{m}'" for m in signal_param.value)
                    _marker_filter = f"AND marker_name IN ({_markers})"
                _df = conn.execute(f"""
                    SELECT frame, time, trial_name, marker_name, x, y, z
                    FROM markers
                    WHERE {_trial_filter} {_marker_filter}
                    ORDER BY trial_name, frame
                """).pl()
                _param_col = "marker_name"
                _y_col = "x"
                _y_title = "X (m)"
            elif _sig == "grf":
                _body_filter = ""
                if signal_param.value:
                    _bodies = ", ".join(f"'{b}'" for b in signal_param.value)
                    _body_filter = f"AND body_name IN ({_bodies})"
                _df = conn.execute(f"""
                    SELECT frame, time, trial_name, body_name, fz
                    FROM grf
                    WHERE {_trial_filter} {_body_filter}
                    ORDER BY trial_name, frame
                """).pl()
                _param_col = "body_name"
                _y_col = "fz"
                _y_title = "Vertical GRF (N)"
            else:
                _fp_filter = ""
                if signal_param.value:
                    _fps = ", ".join(f"'{f}'" for f in signal_param.value)
                    _fp_filter = f"AND fp_name IN ({_fps})"
                _df = conn.execute(f"""
                    SELECT frame, time, trial_name, fp_name, value
                    FROM forceplates
                    WHERE {_trial_filter} {_fp_filter}
                    ORDER BY trial_name, frame
                """).pl()
                _param_col = "fp_name"
                _y_col = "value"
                _y_title = "Value"

            if _df.height == 0:
                _output = mo.md("*No frame data found for matched trials.*")
            elif _kind == "3D scatter (x/y/z)":
                # Special case for markers 3D scatter
                _chart = (
                    alt.Chart(_df.sample(min(5000, _df.height)))
                    .mark_circle(size=8, opacity=0.4)
                    .encode(
                        x=alt.X("x:Q", title="X (m)"),
                        y=alt.Y("y:Q", title="Y (m)"),
                        color=alt.Color("z:Q", title="Z (m)", scale=alt.Scale(scheme="viridis")),
                        tooltip=["marker_name", "x", "y", "z"],
                    )
                    .properties(height=400)
                )
                _output = mo.ui.altair_chart(_chart)
            elif _kind == "individual trials":
                # Show all trial lines, faceted by parameter
                _params = sorted(_df[_param_col].unique().to_list())
                _charts = []
                for _p in _params:
                    _sub = _df.filter(pl.col(_param_col) == _p)
                    _c = (
                        alt.Chart(_sub)
                        .mark_line(opacity=0.5)
                        .encode(
                            x=alt.X("time:Q", title="Time (s)"),
                            y=alt.Y(f"{_y_col}:Q", title=_y_title),
                            color="trial_name:N",
                        )
                        .properties(height=200, title=_p)
                    )
                    _charts.append(_c)
                _chart = alt.vconcat(*_charts).resolve_scale(y="independent")
                _output = mo.ui.altair_chart(_chart)
            elif _kind == "gait cycle normalized":
                # Normalize to gait cycle using GRF contact events
                _trials = _df["trial_name"].unique().to_list()
                _norm_rows = []
                _stride_id = 0
                for _trial in _trials:
                    _trial_data = _df.filter(pl.col("trial_name") == _trial)
                    # Get subject_id for this trial
                    _sub_id = query_result.filter(pl.col("trial_name") == _trial)["subject_id"][0]
                    # Get GRF contact data for stride detection
                    _contact_df = conn.execute(f"""
                        SELECT frame, body_name, contact FROM grf
                        WHERE subject_id = '{_sub_id}' AND trial_name = '{_trial}'
                        ORDER BY frame
                    """).pl()
                    if _contact_df.height == 0:
                        continue
                    # Use first body for stride detection
                    _body = _contact_df["body_name"].unique().sort()[0]
                    _c = _contact_df.filter(pl.col("body_name") == _body).sort("frame")
                    _arr = _c["contact"].to_numpy()
                    _strikes = np.where(np.diff(_arr.astype(int)) == 1)[0]
                    _frames = _c["frame"].to_numpy()
                    if len(_strikes) < 2:
                        continue
                    # Normalize each stride
                    for _si in range(len(_strikes) - 1):
                        _sf = int(_frames[_strikes[_si]])
                        _ef = int(_frames[_strikes[_si + 1]])
                        if _ef - _sf < 10:
                            continue
                        # Get data for this stride
                        _stride_data = _trial_data.filter(
                            (pl.col("frame") >= _sf) & (pl.col("frame") < _ef)
                        )
                        if _stride_data.height == 0:
                            continue
                        # Normalize time to 0-100% of gait cycle
                        _stride_data = _stride_data.with_columns(
                            ((pl.col("frame") - _sf) / (_ef - _sf) * 100).alias("gait_pct")
                        )
                        # Add stride identifier
                        _stride_data = _stride_data.with_columns(
                            pl.lit(f"{_trial}_stride{_si}").alias("stride_id")
                        )
                        _norm_rows.append(_stride_data)
                        _stride_id += 1
                if not _norm_rows:
                    _output = mo.md("*No strides found for normalization.*")
                else:
                    _norm_df = pl.concat(_norm_rows)
                    # Plot by parameter
                    _params = sorted(_norm_df[_param_col].unique().to_list())
                    _charts = []
                    for _p in _params:
                        _sub = _norm_df.filter(pl.col(_param_col) == _p)
                        _c = (
                            alt.Chart(_sub)
                            .mark_line(opacity=0.3)
                            .encode(
                                x=alt.X("gait_pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 100])),
                                y=alt.Y(f"{_y_col}:Q", title=_y_title),
                                color="trial_name:N",
                                detail="stride_id:N",
                            )
                            .properties(height=200, title=f"{_p} — Gait Cycle Normalized")
                        )
                        _charts.append(_c)
                    _chart = alt.vconcat(*_charts).resolve_scale(y="independent")
                    _output = mo.ui.altair_chart(_chart)
            else:
                # Mean ± SD across trials, faceted by parameter
                _agg = (
                    _df.group_by("time", _param_col)
                    .agg(
                        pl.col(_y_col).mean().alias("mean"),
                        pl.col(_y_col).std().alias("std"),
                    )
                    .with_columns(
                        (pl.col("mean") - pl.col("std")).alias("lo"),
                        (pl.col("mean") + pl.col("std")).alias("hi"),
                    )
                    .sort("time")
                )
                _params = sorted(_agg[_param_col].unique().to_list())
                _charts = []
                for _p in _params:
                    _sub = _agg.filter(pl.col(_param_col) == _p)
                    _base = alt.Chart(_sub).encode(
                        x=alt.X("time:Q", title="Time (s)"),
                        y=alt.Y("mean:Q", title=_y_title, scale=alt.Scale(zero=False)),
                    )
                    _line = _base.mark_line(color="#1f77b4", strokeWidth=2)
                    _band = _base.mark_area(opacity=0.2, color="#1f77b4").encode(y="lo:Q", y2="hi:Q")
                    _c = (_band + _line).properties(height=200, title=f"{_p} — mean ± SD")
                    _charts.append(_c)
                _chart = alt.vconcat(*_charts).resolve_scale(y="independent")
                _output = mo.ui.altair_chart(_chart)
    _output
    return


@app.cell
def _(mo):
    mo.md("""
    ## Stride Normalization
    """)
    return


@app.cell
def _(conn, mo, query_result, signal, signal_param):
    if query_result is None or query_result.height == 0 or signal.value != "kinematics":
        stride_dof = mo.ui.dropdown(options=["(no data)"], value="(no data)", label="DOF for stride norm")
    else:
        # Use the DOFs already selected in signal_param, or query available DOFs
        if signal_param.value:
            _dofs = signal_param.value
        else:
            _dofs = conn.execute("SELECT DISTINCT dof_name FROM kinematics ORDER BY dof_name").pl()["dof_name"].to_list()

        _default = _dofs[0]
        # Prefer knee_angle_l or knee_angle_r if available
        for pref in ["knee_angle_l", "knee_angle_r"]:
            if pref in _dofs:
                _default = pref
                break
        stride_dof = mo.ui.dropdown(
            options=_dofs,
            value=_default,
            label="DOF for stride norm",
        )
    stride_dof
    return (stride_dof,)


@app.cell
def _(conn, mo, np, pl, query_result, signal, stride_dof):
    stride_result = pl.DataFrame()
    if query_result is None or query_result.height == 0 or signal.value != "kinematics":
        _output = mo.md("*Run a kinematics query above first.*")
    else:
        _dof = stride_dof.value if stride_dof.value != "(no data)" else "knee_angle_l"
        _dof = _dof.replace("'", "''")

        rows = []
        _stride_counter = 0
        _summaries = []

        # Iterate over all matched trials
        for _row in query_result.iter_rows(named=True):
            _tn = _row["trial_name"].replace("'", "''")
            _sid = _row["subject_id"].replace("'", "''")

            contact_df = conn.execute(f"SELECT frame, body_name, contact FROM grf WHERE subject_id = '{_sid}' AND trial_name = '{_tn}' ORDER BY frame").pl()
            kin_df = conn.execute(f"SELECT frame, pos FROM kinematics WHERE subject_id = '{_sid}' AND trial_name = '{_tn}' AND dof_name = '{_dof}' ORDER BY frame").pl()

            if kin_df.height == 0 or contact_df.height == 0:
                continue

            _body = contact_df["body_name"].unique().sort()[0]
            _c = contact_df.filter(pl.col("body_name") == _body).sort("frame")
            _arr = _c["contact"].to_numpy()
            _strikes = np.where(np.diff(_arr.astype(int)) == 1)[0]
            _frames = _c["frame"].to_numpy()

            if len(_strikes) < 2:
                continue

            _lookup = dict(zip(kin_df["frame"].to_numpy(), kin_df["pos"].to_numpy()))

            for si in range(len(_strikes) - 1):
                sf, ef = int(_frames[_strikes[si]]), int(_frames[_strikes[si + 1]])
                if ef - sf < 10:
                    continue
                angles = np.array([_lookup.get(f, np.nan) for f in range(sf, ef)])
                resampled = np.interp(np.linspace(0, 100, 101), np.linspace(0, 100, ef - sf), angles)
                for pct, ang in enumerate(resampled):
                    rows.append({
                        "trial_name": _row["trial_name"],
                        "stride_id": _stride_counter,
                        "pct": pct,
                        "angle_deg": round(float(ang * 180 / np.pi), 2),
                    })
                _stride_counter += 1

            _summaries.append(f"{_row['trial_name']}: {len(_strikes)-1} strides")

        stride_result = pl.DataFrame(rows)
        if _summaries:
            _output = mo.md(f"**{_dof}** — " + ", ".join(_summaries) + f" → {stride_result.height} total rows")
        else:
            _output = mo.md("*No strides found in any matched trial.*")
    _output
    return (stride_result,)


@app.cell
def _(alt, mo, pl, stride_result):
    if stride_result.height == 0:
        _output = mo.md("*Segment strides above to see chart.*")
    else:
        # Per-trial means with individual trial lines
        _trial_agg = (
            stride_result.group_by("trial_name", "pct")
            .agg(pl.col("angle_deg").mean().alias("mean_angle"))
            .sort("trial_name", "pct")
        )

        # Overall mean ± SD across all strides
        _overall = (
            stride_result.group_by("pct")
            .agg(pl.col("angle_deg").mean().alias("mean"), pl.col("angle_deg").std().alias("std"))
            .with_columns(
                (pl.col("mean") - pl.col("std")).alias("lo"),
                (pl.col("mean") + pl.col("std")).alias("hi"),
            )
            .sort("pct")
        )

        # Individual stride lines (faint)
        _raw = (
            alt.Chart(stride_result)
            .mark_line(opacity=0.08, color="gray")
            .encode(x="pct:Q", y="angle_deg:Q", detail="stride_id:N")
        )

        # SD band (overall)
        _base = alt.Chart(_overall).encode(x=alt.X("pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 100])))
        _band = _base.mark_area(opacity=0.15, color="#1f77b4").encode(y="lo:Q", y2="hi:Q")

        # Per-trial mean lines (colored)
        _trial_lines = (
            alt.Chart(_trial_agg)
            .mark_line(opacity=0.7, strokeWidth=1.5)
            .encode(
                x=alt.X("pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 100])),
                y=alt.Y("mean_angle:Q", title="Angle (deg)"),
                color=alt.Color("trial_name:N", title="Trial"),
            )
        )

        # Overall mean line (thick)
        _overall_line = _base.mark_line(color="#1f77b4", strokeWidth=3).encode(y=alt.Y("mean:Q", title="Angle (deg)"))

        _output = mo.ui.altair_chart(
            (_raw + _band + _trial_lines + _overall_line).properties(
                title="Stride-Normalized Angle (per-trial means with overall mean ± 1 SD)",
                height=400,
            )
        )
    _output
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
