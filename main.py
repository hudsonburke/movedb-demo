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
    mo.md(f"# AddBiomechanics Explorer\n\n| | |\n|---|---|\n| **Studies** | {_n} |\n| **Subjects** | {_s} |\n| **Trials** | {_t} ({_f:,} frames) |\n\n---")
    return subjects, trials


@app.cell
def _(mo, subjects):
    _studies = sorted(subjects["study"].unique().to_list())
    _models = sorted(subjects["model_type"].unique().to_list())
    _splits = sorted(subjects["dataset_split"].unique().to_list())
    study_filter = mo.ui.multiselect(options=_studies, value=[], label="Studies (empty = all)")
    model_filter = mo.ui.dropdown(options=["any"] + _models, value="any", label="Model type")
    split_filter = mo.ui.dropdown(options=["any"] + _splits, value="any", label="Dataset split")
    study_filter
    return model_filter, split_filter, study_filter


@app.cell
def _(model_filter):
    model_filter
    return


@app.cell
def _(split_filter):
    split_filter
    return


@app.cell
def _(mo, model_filter, pl, split_filter, study_filter, subjects, trials):
    _df = subjects
    if study_filter.value:
        _df = _df.filter(pl.col("study").is_in(study_filter.value))
    if model_filter.value != "any":
        _df = _df.filter(pl.col("model_type") == model_filter.value)
    if split_filter.value != "any":
        _df = _df.filter(pl.col("dataset_split") == split_filter.value)
    filtered_subjects = _df
    filtered_trials = trials.join(filtered_subjects.select("subject_id"), on="subject_id") if filtered_subjects.height > 0 else pl.DataFrame()
    mo.md(f"**{filtered_subjects.height} subjects**, **{filtered_trials.height} trials**")
    return filtered_subjects, filtered_trials


@app.cell
def _(filtered_subjects, mo):
    _opts = sorted(filtered_subjects["subject_id"].unique().to_list()) if filtered_subjects.height > 0 else []
    preview_subject = mo.ui.dropdown(options=_opts or ["(none)"], value=_opts[0] if _opts else "(none)", label="Subject")
    preview_subject
    return (preview_subject,)


@app.cell
def _(filtered_trials, mo, pl, preview_subject):
    if preview_subject.value == "(none)":
        _names = []
    else:
        _names = sorted(filtered_trials.filter(pl.col("subject_id") == preview_subject.value)["trial_name"].unique().to_list())
    preview_trial = mo.ui.dropdown(options=_names or ["(none)"], value=_names[0] if _names else "(none)", label="Trial")
    preview_trial
    return (preview_trial,)


@app.cell
def _(mo):
    preview_signal = mo.ui.dropdown(options=["kinematics", "markers", "grf", "forceplates"], value="kinematics", label="Signal")
    preview_signal
    return (preview_signal,)


@app.cell
def _(conn, mo, preview_signal, preview_subject, preview_trial):
    if preview_subject.value == "(none)" or preview_trial.value == "(none)":
        mo.md("*Select a subject and trial.*")
    else:
        _sid = preview_subject.value.replace("'", "''")
        _tn = preview_trial.value.replace("'", "''")
        _sig = preview_signal.value
        _cols = {"kinematics": "frame, time, dof_name, pos, vel, acc, tau", "markers": "frame, time, marker_name, x, y, z", "grf": "frame, time, body_name, contact, fx, fy, fz", "forceplates": "frame, time, fp_name, variable, axis, value"}
        _r = conn.execute(f"SELECT {_cols[_sig]} FROM {_sig} WHERE subject_id = '{_sid}' AND trial_name = '{_tn}' ORDER BY frame LIMIT 500").pl()
        if _r.height:
            mo.md(f"**{_r.height} rows**")
            mo.ui.table(_r, page_size=20)
        else:
            mo.md("*No data.*")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Stride Normalization
    """)
    return


@app.cell
def _(filtered_trials, mo, pl):
    if filtered_trials.height == 0:
        _opts = []
    else:
        _walk = filtered_trials.filter(pl.col("trial_name").str.to_lowercase().str.contains("walk|levelground|treadmill|gait"))
        _opts = sorted(_walk["subject_id"].unique().to_list())
    stride_subject = mo.ui.dropdown(options=_opts or ["(none)"], value=_opts[0] if _opts else "(none)", label="Subject (walking)")
    stride_subject
    return (stride_subject,)


@app.cell
def _(filtered_trials, mo, pl, stride_subject):
    if stride_subject.value == "(none)":
        _names = []
    else:
        _t = filtered_trials.filter(pl.col("subject_id") == stride_subject.value)
        _names = sorted(_t.filter(pl.col("trial_name").str.to_lowercase().str.contains("walk|levelground|treadmill|gait"))["trial_name"].unique().to_list())
    stride_trial = mo.ui.dropdown(options=_names or ["(none)"], value=_names[0] if _names else "(none)", label="Trial")
    stride_trial
    return (stride_trial,)


@app.cell
def _(mo):
    stride_dof = mo.ui.text(value="knee_angle_l", label="DOF")
    stride_dof
    return (stride_dof,)


@app.cell
def _(conn, mo, np, pl, stride_dof, stride_subject, stride_trial):
    stride_result = pl.DataFrame()
    if stride_subject.value == "(none)" or stride_trial.value == "(none)":
        mo.md("*Select a walking subject and trial above.*")
    else:
        _sid = stride_subject.value.replace("'", "''")
        _tn = stride_trial.value.replace("'", "''")
        _dof = stride_dof.value.replace("'", "''")
        contact_df = conn.execute(f"SELECT frame, body_name, contact FROM grf WHERE subject_id = '{_sid}' AND trial_name = '{_tn}' ORDER BY frame").pl()
        kin_df = conn.execute(f"SELECT frame, pos FROM kinematics WHERE subject_id = '{_sid}' AND trial_name = '{_tn}' AND dof_name = '{_dof}' ORDER BY frame").pl()
        if kin_df.height == 0:
            mo.md(f"*No kinematics for DOF '{_dof}' ({kin_df.height} rows). Available DOFs: check SQL editor.*")
        elif contact_df.height == 0:
            mo.md(f"*No contact data ({contact_df.height} rows).*")
        else:
            _body = contact_df["body_name"].unique().sort()[0]
            _c = contact_df.filter(pl.col("body_name") == _body).sort("frame")
            _arr = _c["contact"].to_numpy()
            _strikes = np.where(np.diff(_arr.astype(int)) == 1)[0]
            _frames = _c["frame"].to_numpy()
            if len(_strikes) < 2:
                _min, _max = float(_arr.min()), float(_arr.max())
                mo.md(f"*Only {len(_strikes)} strike(s) for {_body}. Contact range: [{_min}, {_max}]*")
            else:
                _lookup = dict(zip(kin_df["frame"].to_numpy(), kin_df["pos"].to_numpy()))
                rows = []
                for si in range(len(_strikes) - 1):
                    sf, ef = int(_frames[_strikes[si]]), int(_frames[_strikes[si + 1]])
                    if ef - sf < 10:
                        continue
                    angles = np.array([_lookup.get(f, np.nan) for f in range(sf, ef)])
                    resampled = np.interp(np.linspace(0, 100, 101), np.linspace(0, 100, ef - sf), angles)
                    for pct, ang in enumerate(resampled):
                        rows.append({"stride_index": si, "pct": pct, "angle_deg": round(float(ang * 180 / np.pi), 2)})
                stride_result = pl.DataFrame(rows)
                mo.md(f"**{_body}** — {len(_strikes)} strikes → {len(_strikes)-1} strides → {stride_result.height} rows")
    return (stride_result,)


@app.cell
def _(alt, mo, pl, stride_result):
    if stride_result.height == 0:
        chart = mo.md("*No strides to plot.*")
    else:
        _agg = (
            stride_result.group_by("pct")
            .agg(pl.col("angle_deg").mean().alias("mean"), pl.col("angle_deg").std().alias("std"))
            .with_columns((pl.col("mean") - pl.col("std")).alias("lo"), (pl.col("mean") + pl.col("std")).alias("hi"))
            .sort("pct")
        )
        _base = alt.Chart(_agg).encode(x=alt.X("pct:Q", title="% Gait Cycle", scale=alt.Scale(domain=[0, 100])))
        _lines = _base.mark_line(color="#1f77b4", strokeWidth=2).encode(y=alt.Y("mean:Q", title="Angle (deg)"))
        _band = _base.mark_area(opacity=0.2, color="#1f77b4").encode(y="lo:Q", y2="hi:Q")
        _raw = alt.Chart(stride_result).mark_line(opacity=0.15, color="gray").encode(x="pct:Q", y="angle_deg:Q", detail="stride_index:N")
        chart = mo.ui.altair_chart((_raw + _band + _lines).properties(title="Stride-Normalized Angle", height=300))
    chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Ad-hoc SQL
    """)
    return


@app.cell
def _(mo):
    sql_editor = mo.ui.text_area(
        value="SELECT trial_name, dof_name, ROUND(AVG(pos), 4) AS mean_pos\nFROM kinematics k\nJOIN subjects s ON k.subject_id = s.subject_id\nWHERE s.study = 'Carter2023_Formatted_With_Arm'\n  AND dof_name IN ('knee_angle_l', 'knee_angle_r')\nGROUP BY trial_name, dof_name\nLIMIT 50",
        label="SQL", rows=10,
    )
    sql_editor
    return (sql_editor,)


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="Run query")
    run_btn
    return (run_btn,)


@app.cell
def _(conn, mo, run_btn, sql_editor):
    if run_btn.value:
        try:
            _r = conn.execute(sql_editor.value.strip()).pl()
            if _r.height:
                mo.md(f"**{_r.height} rows**")
                mo.ui.table(_r, page_size=20)
            else:
                mo.md("*0 rows.*")
        except Exception as e:
            mo.md(f"**Error:** `{e}`")
    return


if __name__ == "__main__":
    app.run()
