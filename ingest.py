"""Ingest .b3d files into Parquet bundles for the Marimo demo.

Usage:
    .venv-ingest/bin/python ingest.py [--data-root DIR] [--output-dir DIR]

Requires Python 3.9 (nimblephysics constraint).
"""
import argparse
import sys
from pathlib import Path

import nimblephysics as nimble
import numpy as np
import polars as pl


def extract_subject_row(subject: nimble.biomechanics.SubjectOnDisk, source: str) -> dict:
    """Extract one row for subjects.parquet."""
    skel = subject.readSkel(processingPass=0, ignoreGeometry=True)
    return {
        "subject_id": Path(source).stem,
        "source_file": source,
        "mass_kg": subject.getMassKg(),
        "height_m": subject.getHeightM(),
        "age_years": subject.getAgeYears(),
        "biological_sex": subject.getBiologicalSex(),
        "num_dofs": subject.getNumDofs(),
        "dof_names": [skel.getDofByIndex(i).getName() for i in range(skel.getNumDofs())],
        "body_names": [skel.getBodyNode(i).getName() for i in range(skel.getNumBodyNodes())],
        "num_trials": subject.getNumTrials(),
        "num_processing_passes": subject.getNumProcessingPasses(),
        "quality": str(subject.getQuality()).split(".")[-1],
        "tags": list(subject.getSubjectTags()),
        "href": subject.getHref(),
    }


def extract_trial_rows(subject: nimble.biomechanics.SubjectOnDisk, subject_id: str) -> list[dict]:
    """Extract one row per trial for trials.parquet."""
    rows = []
    for t in range(subject.getNumTrials()):
        frames = subject.getTrialLength(t)
        dt = subject.getTrialTimestep(t)
        rows.append({
            "subject_id": subject_id,
            "trial_name": subject.getTrialName(t),
            "trial_index": t,
            "num_frames": frames,
            "timestep": round(dt, 8),
            "duration_s": round(frames * dt, 4),
        })
    return rows


def extract_kinematics_summary(
    subject: nimble.biomechanics.SubjectOnDisk,
    subject_id: str,
    skel,
    max_frames_per_trial: int = 2000,
) -> list[dict]:
    """Extract per-trial, per-DOF kinematics statistics using readFrames API."""

    dof_names = [skel.getDofByIndex(i).getName() for i in range(subject.getNumDofs())]
    n_dofs = subject.getNumDofs()
    num_passes = subject.getNumProcessingPasses()
    pass_idx = num_passes - 1  # best available pass

    rows = []
    for t in range(subject.getNumTrials()):
        trial_name = subject.getTrialName(t)
        frames_count = subject.getTrialLength(t)
        read_count = min(frames_count, max_frames_per_trial)

        try:
            frames = subject.readFrames(
                trial=t,
                startFrame=0,
                numFramesToRead=read_count,
                includeSensorData=False,
                includeProcessingPasses=True,
            )
        except Exception:
            continue

        # Collect all DOF positions into (frames, dofs) array
        pos_list = []
        for frame in frames:
            try:
                pp = frame.processingPasses[pass_idx]
                pos_list.append(np.array(pp.pos, dtype=float))
            except Exception:
                continue

        if not pos_list:
            continue

        pos = np.stack(pos_list)
        for d, dof in enumerate(dof_names):
            col = pos[:, d]
            rows.append({
                "subject_id": subject_id,
                "trial_name": trial_name,
                "dof_name": dof,
                "mean_angle_deg": round(float(np.mean(col)), 4),
                "std_angle_deg": round(float(np.std(col)), 4),
                "min_angle_deg": round(float(np.min(col)), 4),
                "max_angle_deg": round(float(np.max(col)), 4),
                "range_of_motion_deg": round(float(np.ptp(col)), 4),
            })

    return rows


def _resample_stride(pos_array: np.ndarray, n_points: int = 100) -> np.ndarray:
    """Resample a (frames, dofs) array to exactly n_points via linear interpolation."""
    from scipy.interpolate import interp1d

    n_frames = pos_array.shape[0]
    if n_frames < 2:
        return np.tile(pos_array[0], (n_points, 1))
    x_old = np.linspace(0, 1, n_frames)
    x_new = np.linspace(0, 1, n_points)
    f = interp1d(x_old, pos_array, axis=0, kind="linear")
    return f(x_new)


def extract_gait_trajectories(
    subject: nimble.biomechanics.SubjectOnDisk,
    subject_id: str,
    skel,
    n_points: int = 100,
) -> list[dict]:
    """Extract stride-normalized gait trajectories for walking trials.

    Detects foot strikes from contact data, segments into strides,
    normalizes each stride to n_points (0..n_points-1 percent of gait cycle).
    """

    dof_names = [skel.getDofByIndex(i).getName() for i in range(subject.getNumDofs())]
    num_passes = subject.getNumProcessingPasses()
    pass_idx = num_passes - 1
    dt = subject.getTrialTimestep(0)  # assume uniform timestep

    rows = []

    for t in range(subject.getNumTrials()):
        trial_name = subject.getTrialName(t)
        # Only process walking/running trials
        if not any(kw in trial_name.lower() for kw in ("walk", "run", "jog")):
            continue

        frames_count = subject.getTrialLength(t)
        try:
            frames = subject.readFrames(
                trial=t,
                startFrame=0,
                numFramesToRead=frames_count,
                includeSensorData=False,
                includeProcessingPasses=True,
            )
        except Exception:
            continue

        contacts = np.array([f.processingPasses[pass_idx].contact for f in frames])
        pos = np.stack([f.processingPasses[pass_idx].pos for f in frames])

        # Detect left foot strikes (0 -> 1 transition)
        left_contact = contacts[:, 0].astype(int)
        strikes = np.where(np.diff(left_contact) == 1)[0]
        if len(strikes) < 2:
            continue

        # Segment into strides: strike[i] to strike[i+1]
        for s in range(len(strikes) - 1):
            start, end = strikes[s], strikes[s + 1]
            stride_pos = pos[start:end]
            if stride_pos.shape[0] < 10:
                continue

            resampled = _resample_stride(stride_pos, n_points)

            for d, dof in enumerate(dof_names):
                for pct in range(n_points):
                    rows.append({
                        "subject_id": subject_id,
                        "trial_name": trial_name,
                        "stride_index": s,
                        "pct": pct,
                        "dof_name": dof,
                        "angle_deg": round(float(np.degrees(resampled[pct, d])), 4),
                    })

    return rows


def main():
    parser = argparse.ArgumentParser(description="Ingest .b3d files to Parquet")
    parser.add_argument("--data-root", type=Path, required=True, help="Directory containing .b3d files")
    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Output directory for Parquet files")
    args = parser.parse_args()

    b3d_files = sorted(args.data_root.glob("*.b3d"))
    if not b3d_files:
        print(f"No .b3d files found in {args.data_root}")
        sys.exit(1)

    print(f"Found {len(b3d_files)} .b3d files in {args.data_root}")

    subject_rows = []
    trial_rows = []
    kin_rows = []
    traj_rows = []

    for i, path in enumerate(b3d_files):
        print(f"[{i+1}/{len(b3d_files)}] {path.name}...")
        subject = nimble.biomechanics.SubjectOnDisk(str(path))
        subject_id = path.stem

        subject_rows.append(extract_subject_row(subject, str(path)))
        trial_rows.extend(extract_trial_rows(subject, subject_id))

        skel = subject.readSkel(processingPass=0, ignoreGeometry=True)
        kin_rows.extend(extract_kinematics_summary(subject, subject_id, skel))
        traj_rows.extend(extract_gait_trajectories(subject, subject_id, skel))

    args.output_dir.mkdir(parents=True, exist_ok=True)

    subjects_df = pl.DataFrame(subject_rows)
    subjects_path = args.output_dir / "subjects.parquet"
    subjects_df.write_parquet(subjects_path)
    print(f"\nWrote {subjects_df.height} subjects → {subjects_path}")

    trials_df = pl.DataFrame(trial_rows)
    trials_path = args.output_dir / "trials.parquet"
    trials_df.write_parquet(trials_path)
    print(f"Wrote {trials_df.height} trials → {trials_path}")

    if kin_rows:
        kin_df = pl.DataFrame(kin_rows)
        kin_path = args.output_dir / "kinematics_summary.parquet"
        kin_df.write_parquet(kin_path)
        print(f"Wrote {kin_df.height} kinematics rows → {kin_path}")

    if traj_rows:
        traj_df = pl.DataFrame(traj_rows)
        traj_path = args.output_dir / "gait_trajectories.parquet"
        traj_df.write_parquet(traj_path)
        print(f"Wrote {traj_df.height} gait trajectory rows → {traj_path}")

    print("\nDone.")

if __name__ == "__main__":
    main()
