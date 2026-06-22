#!/usr/bin/env python3
"""
Delta filter: compare new feed against a previous snapshot and return only
rows where Price or Qty_Avail changed, plus any new items.
"""

import os
import glob
import pandas as pd
from datetime import datetime


SNAPSHOT_DIR = "./BVDG-VET"
SNAPSHOT_PREFIX = "previous-feed-snapshot-"


def find_latest_snapshot():
    """Return path to the most recent snapshot file, or None if none exist."""
    pattern = os.path.join(SNAPSHOT_DIR, f"{SNAPSHOT_PREFIX}*.csv")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def run(new_feed_path, snapshot_path=None):
    """
    Compare new_feed_path against snapshot_path (or the latest auto-detected
    snapshot) and return a filtered feed path containing only changed/new rows.
    Saves a new snapshot dated today after running.

    Args:
        new_feed_path: path to the incoming raw vendor feed CSV
        snapshot_path: explicit path to baseline snapshot; auto-detected if None

    Returns:
        path to filtered feed CSV (subset of new_feed_path)
    """
    resolved_snapshot = snapshot_path or find_latest_snapshot()

    if resolved_snapshot is None:
        raise FileNotFoundError(
            "No snapshot found. Provide --snapshot <path> to set a baseline."
        )

    if not os.path.exists(resolved_snapshot):
        raise FileNotFoundError(f"Snapshot file not found: {resolved_snapshot}")

    print(f"Delta snapshot: {resolved_snapshot}")

    new_df = pd.read_csv(new_feed_path, encoding="latin1")
    old_df = pd.read_csv(resolved_snapshot, encoding="latin1", usecols=["Item", "Price", "Qty_Avail"])

    old_df = old_df.rename(columns={"Price": "_old_Price", "Qty_Avail": "_old_Qty_Avail"})

    merged = new_df.merge(old_df, on="Item", how="left")

    changed_mask = (
        merged["_old_Price"].isna()  # new item
        | (merged["Price"] != merged["_old_Price"])
        | (merged["Qty_Avail"] != merged["_old_Qty_Avail"])
    )

    filtered_df = new_df[changed_mask.values].reset_index(drop=True)

    total = len(new_df)
    kept = len(filtered_df)
    new_items = int(merged["_old_Price"].isna().sum())
    print(f"  Total rows in new feed:  {total}")
    print(f"  New items:               {new_items}")
    print(f"  Price/inventory changes: {kept - new_items}")
    print(f"  Rows after delta filter: {kept} ({100 * kept / total:.1f}% of feed)")

    # Write filtered feed to a temp file
    today = datetime.now().strftime("%Y%m%d")
    filtered_path = os.path.join(SNAPSHOT_DIR, f"delta-feed-{today}.csv")
    filtered_df.to_csv(filtered_path, index=False)
    print(f"  Filtered feed saved:     {filtered_path}")

    # Save new snapshot for future runs
    snapshot_out = os.path.join(SNAPSHOT_DIR, f"{SNAPSHOT_PREFIX}{today}.csv")
    new_df.to_csv(snapshot_out, index=False)
    print(f"  New snapshot saved:      {snapshot_out}")

    # Write stats file for CI summary
    stats_path = os.path.join(SNAPSHOT_DIR, "delta-stats.txt")
    with open(stats_path, "w") as f:
        f.write(f"total={total}\n")
        f.write(f"kept={kept}\n")
        f.write(f"new_items={new_items}\n")
        f.write(f"price_inv_changes={kept - new_items}\n")
        f.write(f"skipped={total - kept}\n")
        f.write(f"pct={100 * kept / total:.1f}\n")

    return filtered_path
