#!/usr/bin/env python3
"""Merge local coverage.xml files under a directory and print a percentage.

Usage: merge_local_coverage.py [artifacts_dir]

Prints either a percentage like "85%" or "85.3%" or the string "unknown".

This script properly merges coverage from multiple coverage.xml files by:
1. Using the aggregate line-rate statistics from the root <coverage> element for maximum accuracy
2. Falling back to tracking which lines are covered in each source file across all reports
3. Rounding to 1 decimal place for more precise reporting (shows as integer if whole number)
"""

from collections import defaultdict
from pathlib import Path
import sys
from xml.etree import ElementTree as ET


def main(argv):
    artifacts_dir = argv[1] if len(argv) > 1 else "artifacts"
    p = Path(artifacts_dir)

    if not p.exists():
        print("unknown")
        return 0

    # Collect all coverage data across all coverage.xml files
    all_file_coverage = defaultdict(set)
    all_file_lines = defaultdict(set)

    # Track root-level coverage statistics for weighted average
    total_root_lines_valid = 0
    total_root_lines_covered = 0

    coverage_files = list(p.rglob("coverage.xml"))
    if not coverage_files:
        print("unknown")
        return 0

    for coverage_file in coverage_files:
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
        except Exception:
            continue

        # First, try to use the aggregate statistics from the root <coverage> element
        # This is more accurate than recalculating from individual lines
        lines_valid = root.attrib.get("lines-valid")
        lines_covered = root.attrib.get("lines-covered")

        if lines_valid and lines_covered:
            try:
                total_root_lines_valid += int(lines_valid)
                total_root_lines_covered += int(lines_covered)
            except (ValueError, TypeError):
                pass

        # Navigate through packages/classes to find all lines
        for package in root.iter("package"):
            for cls in package.iter("class"):
                filename = cls.attrib.get("filename")
                if not filename:
                    continue

                # Lines can be in direct class element or nested under methods/method/lines
                for line in cls.iter("line"):
                    line_num = line.attrib.get("number")
                    hits = line.attrib.get("hits", "0")
                    try:
                        if line_num:
                            line_num_int = int(line_num)
                            hits_int = int(hits)
                            # Only count executable lines (hits >= 0, excluding -1 for branches)
                            if hits_int >= 0:
                                # Track all valid lines
                                all_file_lines[filename].add(line_num_int)
                                # Track covered lines
                                if hits_int > 0:
                                    all_file_coverage[filename].add(line_num_int)
                    except (ValueError, TypeError):
                        continue

    # Use root-level statistics if available (more accurate)
    if total_root_lines_valid > 0:
        pct = round((total_root_lines_covered / total_root_lines_valid) * 100, 1)
        # Format to 1 decimal place if not a whole number, otherwise show as integer
        if pct == int(pct):
            print(f"{int(pct)}%")
        else:
            print(f"{pct}%")
        return 0

    # Fallback: Calculate total coverage from line-by-line data
    total_lines = sum(len(lines) for lines in all_file_lines.values())
    total_covered = sum(len(all_file_coverage[filename]) for filename in all_file_lines.keys())

    if total_lines == 0:
        print("unknown")
        return 0

    pct = round((total_covered / total_lines) * 100, 1)
    # Format to 1 decimal place if not a whole number, otherwise show as integer
    if pct == int(pct):
        print(f"{int(pct)}%")
    else:
        print(f"{pct}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
