"""Ingest .b3d files into Parquet bundles for the Marimo demo.

Thin wrapper around movedb.adapters.b3d_ingest.ingest_b3d_dataset().

Usage:
    uv run python ingest.py \
        --data-root /path/to/Downloads/test \
        --data-root /path/to/Downloads/train \
        --output-dir data \
        --workers 8
"""
from __future__ import annotations

import argparse
from pathlib import Path

from movedb.adapters.b3d_ingest import ingest_b3d_dataset


def main():
    parser = argparse.ArgumentParser(description="Ingest .b3d files to Parquet")
    parser.add_argument(
        "--data-root", type=Path, action="append", required=True,
        help="Root directory with .b3d files (specify multiple times)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    parser.add_argument("--skip-markers", action="store_true", help="Skip marker extraction")
    parser.add_argument("--skip-forceplates", action="store_true", help="Skip force plate extraction")
    args = parser.parse_args()

    skip = []
    if args.skip_markers:
        skip.append("markers")
    if args.skip_forceplates:
        skip.append("forceplates")

    stats = ingest_b3d_dataset(
        data_roots=args.data_root,
        output_dir=args.output_dir,
        skip_signals=skip or None,
        workers=args.workers,
    )

    print(f"\nDone in {stats.elapsed_seconds/60:.1f}m.")
    print(f"  Completed: {stats.subjects_completed}")
    print(f"  Failed:    {stats.subjects_failed}")
    for sig, count in stats.signal_row_counts.items():
        print(f"  {sig}: {count:,} rows")
    if stats.errors:
        print(f"\nErrors ({len(stats.errors)}):")
        for sid, msg in stats.errors[:10]:
            print(f"  {sid}: {msg}")
        if len(stats.errors) > 10:
            print(f"  ... and {len(stats.errors) - 10} more")


if __name__ == "__main__":
    main()
