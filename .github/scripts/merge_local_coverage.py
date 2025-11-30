#!/usr/bin/env python3
"""Merge local coverage.xml files under a directory and print a percentage.

Usage: merge_local_coverage.py [artifacts_dir]

Prints either a percentage like "85%" or the string "unknown".

This script properly merges coverage from multiple coverage.xml files by tracking
which lines are covered in each source file across all reports, avoiding double-counting.
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

        # Navigate through packages/classes to find all lines
        for package in root.iter("package"):
            for cls in package.iter("class"):
                filename = cls.attrib.get("filename")
                if not filename:
                    continue

                for line in cls.iter("line"):
                    line_num = line.attrib.get("number")
                    hits = line.attrib.get("hits", "0")
                    try:
                        if line_num:
                            line_num_int = int(line_num)
                            # Track all valid lines
                            all_file_lines[filename].add(line_num_int)
                            # Track covered lines
                            if int(hits) > 0:
                                all_file_coverage[filename].add(line_num_int)
                    except (ValueError, TypeError):
                        continue

    # Calculate total coverage
    total_lines = sum(len(lines) for lines in all_file_lines.values())
    total_covered = sum(len(all_file_coverage[filename]) for filename in all_file_lines.keys())

    if total_lines == 0:
        print("unknown")
        return 0

    pct = round((total_covered / total_lines) * 100)
    print(f"{pct}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
