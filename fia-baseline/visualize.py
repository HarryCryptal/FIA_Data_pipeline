import glob
import os
import re
import pandas as pd

EXPORT_DIR = "cleaned"


def clean_header(header):
    """Remove leading emojis/symbols from headers."""
    return re.sub(r"^[^\w]+", "", header or "").strip()


def entity_name(filename):
    """Clean filename to extract entity category name."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"_all$", "", stem)
    return re.sub(r"\s+[0-9a-f]{32}$", "", stem, flags=re.I).strip()


def inspect_all_columns():
    # Resolve cleaned relative directory
    target_dir = (
        EXPORT_DIR
        if os.path.exists(EXPORT_DIR)
        else os.path.join("..", EXPORT_DIR)
    )
    csv_files = glob.glob(os.path.join(target_dir, "*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in '{target_dir}/' folder.")
        return

    for file_path in sorted(csv_files):
        entity = entity_name(file_path)
        df = pd.read_csv(file_path, encoding="utf-8-sig")

        # Clean column headers
        df.columns = [clean_header(col) for col in df.columns]

        print("=" * 100)
        print(
            f"📁 CATEGORY: {entity.upper()} ({len(df)} total rows, {len(df.columns)} columns)"
        )
        print(f"   File: {os.path.basename(file_path)}")
        print("=" * 100)

        print(
            f"\n{'#':<4} | {'Column Name':<32} | {'Filled Rows':<12} | {'Sample Value / Preview':<45}"
        )
        print("-" * 100)

        for idx, col in enumerate(df.columns, start=1):
            # Calculate non-null entries
            non_null_count = df[col].notna().sum()

            # Get first non-empty sample value
            sample_series = df[col].dropna()
            if not sample_series.empty:
                raw_sample = str(sample_series.iloc[0]).replace("\n", " ")
                # Strip Notion URL parentheses for cleaner terminal viewing
                clean_sample = re.sub(
                    r"\s*\((?:https?://|notion://)[^)]*\)", "", raw_sample
                )
                sample = (
                    (clean_sample[:42] + "...")
                    if len(clean_sample) > 45
                    else clean_sample
                )
            else:
                sample = "[ALL EMPTY]"

            fill_percentage = (non_null_count / len(df)) * 100
            fill_str = f"{non_null_count}/{len(df)} ({fill_percentage:.0f}%)"

            print(f"{idx:<4} | {col:<32} | {fill_str:<12} | {sample:<45}")

        print("\n")


if __name__ == "__main__":
    inspect_all_columns()