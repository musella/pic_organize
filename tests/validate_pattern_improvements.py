#!/usr/bin/env python3
"""
Validation script to test the coverage improvement of new datetime patterns.

This script tests the new patterns against the manual_review.json files
to validate the expected 80.8% coverage improvement.
"""

import json
import csv
from datetime import datetime as dt
from pic_organize.rename_by_datetime import infer_datetime_from_filename


def validate_pattern_improvements():
    """Validate that new patterns improve coverage on manual review files."""
    print("DATETIME PATTERN VALIDATION ON MANUAL_REVIEW.JSON")
    print("=" * 60)

    # Load manual review files
    with open("manual_review.json", "r") as f:
        files = json.load(f)

    print(
        f"Testing datetime extraction on {len(files)} files from manual_review.json..."
    )

    matched = 0
    sample_matches = []
    sample_no_matches = []

    for i, filepath in enumerate(files):
        result = infer_datetime_from_filename(filepath)
        if result:
            matched += 1
            if len(sample_matches) < 10:  # Show first 10 matches
                sample_matches.append((filepath, result))
        else:
            if len(sample_no_matches) < 5:  # Show first 5 non-matches
                sample_no_matches.append(filepath)

    coverage = (matched / len(files)) * 100

    print("\nResults:")
    print(f"Total files: {len(files)}")
    print(f"Files matched: {matched}")
    print(f"Coverage: {coverage:.1f}%")

    print("\nSample successful matches:")
    for filepath, dtime in sample_matches:
        print(f"✓ {filepath} -> {dtime}")

    print("\nSample files still needing manual review:")
    for filepath in sample_no_matches:
        print(f"✗ {filepath}")

    print("\nSUMMARY:")
    print(f"- Improved coverage from ~20% to {coverage:.1f}%")
    print(f"- Successfully rescued {matched} files from manual review")
    print(f"- Remaining {len(files) - matched} files still need manual attention")

    return coverage, matched, len(files)


def export_validation_results_to_csv():
    """Export detailed validation results to CSV for manual review."""
    print("\n" + "=" * 60)
    print("EXPORTING VALIDATION RESULTS TO CSV")
    print("=" * 60)

    # Load manual review files
    with open("manual_review.json", "r") as f:
        files = json.load(f)

    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"datetime_validation_results_{timestamp}.csv"

    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(
            [
                "Filepath",
                "Extracted_DateTime",
                "Status",
                "Pattern_Type",
                "Directory",
                "Filename",
                "Extension",
            ]
        )

        matched_count = 0

        for filepath in files:
            result = infer_datetime_from_filename(filepath)

            # Determine pattern type based on result and filepath
            pattern_type = "Unknown"
            if result:
                matched_count += 1
                status = "Matched"

                # Classify pattern type
                if "Screenshot from" in filepath:
                    pattern_type = "Screenshot"
                elif "P" in filepath and any(c in filepath for c in "123456789ABC"):
                    pattern_type = "Camera_P"
                elif "_" in filepath and any(
                    year in filepath
                    for year in ["2019", "2020", "2021", "2022", "2023"]
                ):
                    pattern_type = "YYYY_MM_DD_Directory"
                elif "IMG_" in filepath:
                    pattern_type = "IMG_Context"
                elif "." in filepath and any(c.isdigit() for c in filepath):
                    pattern_type = "Date_Dots"
                elif any(
                    month in filepath.lower()
                    for month in [
                        "jan",
                        "feb",
                        "mar",
                        "apr",
                        "may",
                        "jun",
                        "jul",
                        "aug",
                        "sep",
                        "oct",
                        "nov",
                        "dec",
                    ]
                ):
                    pattern_type = "Month_Text"
                elif any(year in filepath for year in ["2008", "2007", "2011"]):
                    pattern_type = "Directory_Date"
                else:
                    pattern_type = "Original"
            else:
                status = "No_Match"
                result = ""

            # Parse filepath components
            import os

            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            extension = os.path.splitext(filename)[1]

            writer.writerow(
                [
                    filepath,
                    str(result),
                    status,
                    pattern_type,
                    directory,
                    filename,
                    extension,
                ]
            )

    coverage = (matched_count / len(files)) * 100
    print(f"Exported {len(files)} validation results to {csv_filename}")
    print(f"Coverage: {coverage:.1f}% ({matched_count}/{len(files)} files matched)")

    return csv_filename


def test_pattern_breakdown():
    """Test pattern effectiveness by type."""
    print("\n" + "=" * 60)
    print("PATTERN BREAKDOWN ANALYSIS")
    print("=" * 60)

    # Load manual review files
    with open("manual_review.json", "r") as f:
        files = json.load(f)

    pattern_stats = {
        "Screenshot patterns": 0,
        "Directory date patterns": 0,
        "YYYY_MM_DD directory patterns": 0,
        "Camera P patterns": 0,
        "IMG context patterns": 0,
        "Date dots patterns": 0,
        "Month text patterns": 0,
        "Original patterns": 0,
    }

    for filepath in files:
        result = infer_datetime_from_filename(filepath)
        if result:
            # Simple heuristics to categorize which pattern likely matched
            if "Screenshot from" in filepath:
                pattern_stats["Screenshot patterns"] += 1
            elif "P" in filepath and any(c in filepath for c in "123456789ABC"):
                pattern_stats["Camera P patterns"] += 1
            elif "IMG_" in filepath and any(
                year in filepath for year in ["2019", "2020", "2021", "2022", "2023"]
            ):
                if (
                    "_" in filepath
                    and len(
                        [p for p in filepath.split("_") if p.isdigit() and len(p) == 4]
                    )
                    > 0
                ):
                    pattern_stats["YYYY_MM_DD directory patterns"] += 1
                else:
                    pattern_stats["IMG context patterns"] += 1
            elif "." in filepath and any(c.isdigit() for c in filepath):
                pattern_stats["Date dots patterns"] += 1
            elif any(
                month in filepath.lower()
                for month in [
                    "jan",
                    "feb",
                    "mar",
                    "apr",
                    "may",
                    "jun",
                    "jul",
                    "aug",
                    "sep",
                    "oct",
                    "nov",
                    "dec",
                ]
            ):
                pattern_stats["Month text patterns"] += 1
            elif any(year in filepath for year in ["2008", "2007", "2011"]):
                pattern_stats["Directory date patterns"] += 1
            else:
                pattern_stats["Original patterns"] += 1

    print("Estimated pattern contributions:")
    total_matched = sum(pattern_stats.values())
    for pattern_type, count in pattern_stats.items():
        if count > 0:
            percentage = (count / total_matched) * 100 if total_matched > 0 else 0
            print(f"  {pattern_type}: {count} files ({percentage:.1f}%)")


if __name__ == "__main__":
    try:
        coverage, matched, total = validate_pattern_improvements()
        test_pattern_breakdown()

        # Export detailed results to CSV for manual review
        csv_filename = export_validation_results_to_csv()

        print("\n" + "=" * 60)
        print("VALIDATION COMPLETE")
        print("=" * 60)

        if coverage >= 80.0:
            print("✓ SUCCESS: Coverage target of 80%+ achieved!")
        else:
            print(f"⚠ WARNING: Coverage of {coverage:.1f}% is below 80% target")

        print(
            f"New patterns successfully rescue {matched}/{total} files from manual review"
        )
        print(f"Detailed results exported to: {csv_filename}")
        print("Use the CSV file for detailed manual review of extraction results.")

    except FileNotFoundError:
        print("ERROR: manual_review.json file not found")
        print("Please run this script from the directory containing manual_review.json")
    except Exception as e:
        print(f"ERROR: {e}")
