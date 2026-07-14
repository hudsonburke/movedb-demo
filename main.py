import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import polars as pl
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from scipy.interpolate import CubicSpline
    from pathlib import Path

    return CubicSpline, Path, go, make_subplots, mo, np, pl, px


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
        options=["kinematics", "markers", "grf"],
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
    else:  # grf
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
    }
    _param_col = {
        "kinematics": "k.dof_name",
        "markers": "k.marker_name",
        "grf": "k.body_name",
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

    # If signal params are specified, ensure trials have ALL of them
    _having_clause = ""
    if signal_param.value and len(signal_param.value) > 1:
        _having_clause = f"HAVING COUNT(DISTINCT {_param_col[_sig]}) = {len(signal_param.value)}"

    # Query matching trials with metadata
    _sql = f"""SELECT t.trial_name, t.subject_id, t.num_frames, t.duration_s, s.study,
           s.biological_sex, s.mass_kg, s.height_m, s.age_years
    FROM trials t
    JOIN subjects s ON t.subject_id = s.subject_id
    JOIN {_sig} k ON k.trial_name = t.trial_name AND k.subject_id = t.subject_id
    {_where}
    GROUP BY t.trial_name, t.subject_id, t.num_frames, t.duration_s, s.study,
             s.biological_sex, s.mass_kg, s.height_m, s.age_years
    {_having_clause}
    ORDER BY s.study, t.subject_id, t.trial_name
    {_limit_clause}"""

    sql_editor = mo.ui.text_area(value=_sql, label="SQL (editable)", rows=16)
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
            options=["gait cycle normalized", "raw data", "mean ± SD", "3D scatter (x/y/z)"],
            value="gait cycle normalized",
            label="Plot type",
        )
    else:
        plot_kind = mo.ui.dropdown(
            options=["gait cycle normalized", "raw data", "mean ± SD"],
            value="gait cycle normalized",
            label="Plot type",
        )
    plot_kind
    return (plot_kind,)


@app.cell
def _(conn, CubicSpline, go, make_subplots, mo, np, pl, plot_kind, query_result, signal, signal_param):
    if query_result is None or query_result.height == 0:
        _output = mo.md("*Run a query above to see a plot.*")
    elif plot_kind.value == "(no data)":
        _output = mo.md("*Select a plot type.*")
    else:
        _spinner = mo.status.spinner(subtitle="Generating plot...")
        _spinner
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
        else:  # grf
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

        if _df.height == 0:
            _output = mo.md("*No frame data found for matched trials.*")
        else:
            # Downsample if too many points (> 50k) - take every Nth point
            if _df.height > 50000:
                _step = max(1, _df.height // 50000)
                _df = _df.sort("trial_name", "frame").with_row_index("_idx").filter(pl.col("_idx") % _step == 0).drop("_idx")

            _params = sorted(_df[_param_col].unique().to_list())
            _n_params = len(_params)

            if _kind == "3D scatter (x/y/z)":
                # Special case for markers 3D scatter
                _sample = _df.sample(min(5000, _df.height))
                _fig = go.Figure(data=[go.Scatter3d(
                    x=_sample["x"].to_list(),
                    y=_sample["y"].to_list(),
                    z=_sample["z"].to_list(),
                    mode="markers",
                    marker=dict(size=3, opacity=0.4, color=_sample["z"].to_list(), colorscale="Viridis"),
                    text=_sample["marker_name"].to_list(),
                )])
                _fig.update_layout(height=600, title="3D Marker Positions")
                _output = mo.ui.plotly(_fig)
            elif _kind == "raw data":
                # Show all trial lines, subplots by parameter
                _fig = make_subplots(rows=_n_params, cols=1, subplot_titles=_params, shared_xaxes=True, vertical_spacing=0.05)
                _trials = sorted(_df["trial_name"].unique().to_list())
                for _i, _p in enumerate(_params, 1):
                    _sub = _df.filter(pl.col(_param_col) == _p)
                    for _t in _trials:
                        _tdata = _sub.filter(pl.col("trial_name") == _t)
                        _fig.add_trace(go.Scatter(
                            x=_tdata["time"].to_list(),
                            y=_tdata[_y_col].to_list(),
                            name=_t,
                            legendgroup=_t,
                            showlegend=(_i == 1),
                            line=dict(width=1),
                            opacity=0.6,
                        ), row=_i, col=1)
                _fig.update_xaxes(title_text="Time (s)", row=_n_params, col=1)
                _fig.update_layout(height=300 * _n_params, title=f"{_y_title} — Raw Data")
                _output = mo.ui.plotly(_fig)
            elif _kind == "gait cycle normalized":
                # Normalize to gait cycle using GRF contact events
                _trials = _df["trial_name"].unique().to_list()
                _norm_rows = []
                _stride_id = 0
                for _trial in _trials:
                    _trial_data = _df.filter(pl.col("trial_name") == _trial)
                    _sub_id = query_result.filter(pl.col("trial_name") == _trial)["subject_id"][0]
                    _contact_df = conn.execute(f"""
                        SELECT frame, body_name, contact FROM grf
                        WHERE subject_id = '{_sub_id}' AND trial_name = '{_trial}'
                        ORDER BY frame
                    """).pl()
                    if _contact_df.height == 0:
                        continue
                    _body = _contact_df["body_name"].unique().sort()[0]
                    _c = _contact_df.filter(pl.col("body_name") == _body).sort("frame")
                    _arr = _c["contact"].to_numpy()
                    _strikes = np.where(np.diff(_arr.astype(int)) == 1)[0]
                    _frames = _c["frame"].to_numpy()
                    if len(_strikes) < 2:
                        continue
                    for _si in range(len(_strikes) - 1):
                        _sf = int(_frames[_strikes[_si]])
                        _ef = int(_frames[_strikes[_si + 1]])
                        if _ef - _sf < 10:
                            continue
                        _stride_data = _trial_data.filter(
                            (pl.col("frame") >= _sf) & (pl.col("frame") <= _ef)
                        ).sort("frame").unique("frame")
                        if _stride_data.height < 4:
                            continue
                        # Cubic spline interpolation to 101 points (0-100%)
                        _frames_arr = _stride_data["frame"].to_numpy().astype(float)
                        _values = _stride_data[_y_col].to_numpy()
                        _pct_arr = (_frames_arr - _sf) / (_ef - _sf) * 100
                        # Ensure endpoints are included
                        if _pct_arr[0] > 0:
                            _pct_arr = np.insert(_pct_arr, 0, 0.0)
                            _values = np.insert(_values, 0, _values[0])
                        if _pct_arr[-1] < 100:
                            _pct_arr = np.append(_pct_arr, 100.0)
                            _values = np.append(_values, _values[-1])
                        # Remove any duplicate x values
                        _mask = np.diff(_pct_arr, prepend=-1) > 0
                        _pct_arr = _pct_arr[_mask]
                        _values = _values[_mask]
                        if len(_pct_arr) < 4:
                            continue
                        _cs = CubicSpline(_pct_arr, _values)
                        _interp_pcts = np.linspace(0, 100, 101)
                        _interp_vals = _cs(_interp_pcts)
                        _param_val = _stride_data[_param_col][0]
                        for _pct, _val in zip(_interp_pcts, _interp_vals):
                            _norm_rows.append({
                                "gait_pct": float(_pct),
                                _y_col: float(_val),
                                "stride_id": f"{_trial}_s{_si}",
                                _param_col: _param_val,
                            })
                        _stride_id += 1
                if not _norm_rows:
                    _output = mo.md("*No strides found for normalization.*")
                else:
                    _norm_df = pl.DataFrame(_norm_rows)
                    _agg = (
                        _norm_df.group_by("gait_pct", _param_col)
                        .agg(pl.col(_y_col).mean().alias("mean"), pl.col(_y_col).std().alias("std"))
                        .with_columns(
                            (pl.col("mean") - pl.col("std")).alias("lo"),
                            (pl.col("mean") + pl.col("std")).alias("hi"),
                        )
                        .sort("gait_pct")
                    )
                    _fig = make_subplots(rows=_n_params, cols=1, subplot_titles=[f"{p} — Gait Cycle Normalized" for p in _params], shared_xaxes=True, vertical_spacing=0.05)
                    for _i, _p in enumerate(_params, 1):
                        _sub = _norm_df.filter(pl.col(_param_col) == _p)
                        _sub_agg = _agg.filter(pl.col(_param_col) == _p)
                        # Individual stride lines
                        for _sid in _sub["stride_id"].unique().to_list():
                            _sdata = _sub.filter(pl.col("stride_id") == _sid)
                            _fig.add_trace(go.Scatter(
                                x=_sdata["gait_pct"].to_list(),
                                y=_sdata[_y_col].to_list(),
                                line=dict(color="gray", width=0.5),
                                opacity=0.15,
                                showlegend=False,
                            ), row=_i, col=1)
                        # SD band
                        _fig.add_trace(go.Scatter(
                            x=_sub_agg["gait_pct"].to_list() + _sub_agg["gait_pct"].to_list()[::-1],
                            y=_sub_agg["hi"].to_list() + _sub_agg["lo"].to_list()[::-1],
                            fill="toself",
                            fillcolor="rgba(31,119,180,0.1)",
                            line=dict(color="rgba(0,0,0,0)"),
                            showlegend=False,
                        ), row=_i, col=1)
                        # Mean line
                        _fig.add_trace(go.Scatter(
                            x=_sub_agg["gait_pct"].to_list(),
                            y=_sub_agg["mean"].to_list(),
                            line=dict(color="#1f77b4", width=2),
                            name="Mean",
                            showlegend=(_i == 1),
                        ), row=_i, col=1)
                    _fig.update_xaxes(title_text="% Gait Cycle", range=[0, 100], row=_n_params, col=1)
                    _fig.update_layout(height=300 * _n_params, title=f"{_y_title}")
                    _output = mo.ui.plotly(_fig)
            else:  # mean ± SD (raw time)
                _agg = (
                    _df.group_by("time", _param_col)
                    .agg(pl.col(_y_col).mean().alias("mean"), pl.col(_y_col).std().alias("std"))
                    .with_columns(
                        (pl.col("mean") - pl.col("std")).alias("lo"),
                        (pl.col("mean") + pl.col("std")).alias("hi"),
                    )
                    .sort("time")
                )
                _fig = make_subplots(rows=_n_params, cols=1, subplot_titles=[f"{p} — mean ± SD" for p in _params], shared_xaxes=True, vertical_spacing=0.05)
                for _i, _p in enumerate(_params, 1):
                    _sub = _agg.filter(pl.col(_param_col) == _p)
                    # SD band
                    _fig.add_trace(go.Scatter(
                        x=_sub["time"].to_list() + _sub["time"].to_list()[::-1],
                        y=_sub["hi"].to_list() + _sub["lo"].to_list()[::-1],
                        fill="toself",
                        fillcolor="rgba(31,119,180,0.1)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                    ), row=_i, col=1)
                    # Mean line
                    _fig.add_trace(go.Scatter(
                        x=_sub["time"].to_list(),
                        y=_sub["mean"].to_list(),
                        line=dict(color="#1f77b4", width=2),
                        name="Mean",
                        showlegend=(_i == 1),
                    ), row=_i, col=1)
                _fig.update_xaxes(title_text="Time (s)", row=_n_params, col=1)
                _fig.update_layout(height=300 * _n_params, title=f"{_y_title}")
                _output = mo.ui.plotly(_fig)
    _output
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
