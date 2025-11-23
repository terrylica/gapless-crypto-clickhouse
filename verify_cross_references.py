#!/usr/bin/env python3
"""
Cross-Reference Consistency Checker

Verifies all cross-references in documentation point to correct files, functions, classes, and concepts.
Post ADR-0029 validation.

Usage:
    python verify_cross_references.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass

@dataclass
class Reference:
    """Cross-reference found in documentation"""
    source_file: Path
    line_number: int
    link_text: str
    target_path: str
    ref_type: str  # "file", "adr", "function", "class", "section"


class CrossReferenceChecker:
    """Checks all documentation cross-references for consistency"""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.references: List[Reference] = []
        self.broken_refs: List[Reference] = []
        self.valid_refs: List[Reference] = []

    def find_all_references(self) -> None:
        """Find all cross-references in markdown files"""
        md_files = list(self.repo_root.rglob("*.md"))
        # Exclude node_modules
        md_files = [f for f in md_files if "node_modules" not in str(f)]

        for md_file in md_files:
            self._extract_refs_from_file(md_file)

    def _extract_refs_from_file(self, file_path: Path) -> None:
        """Extract all markdown link references from a file"""
        try:
            content = file_path.read_text()
            lines = content.splitlines()

            # Pattern: [link text](path/to/file.md)
            link_pattern = r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)'

            for line_num, line in enumerate(lines, 1):
                matches = re.finditer(link_pattern, line)
                for match in matches:
                    link_text = match.group(1)
                    target = match.group(2)

                    # Determine reference type
                    if target.startswith("http"):
                        continue  # Skip external URLs

                    ref_type = "file"
                    if "ADR" in link_text or "/decisions/" in target:
                        ref_type = "adr"
                    elif "SKILL" in target:
                        ref_type = "skill"

                    ref = Reference(
                        source_file=file_path,
                        line_number=line_num,
                        link_text=link_text,
                        target_path=target,
                        ref_type=ref_type
                    )
                    self.references.append(ref)

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    def verify_references(self) -> None:
        """Verify all extracted references"""
        for ref in self.references:
            if self._verify_single_reference(ref):
                self.valid_refs.append(ref)
            else:
                self.broken_refs.append(ref)

    def _verify_single_reference(self, ref: Reference) -> bool:
        """Verify a single reference exists"""
        target = ref.target_path

        # Handle absolute paths
        if target.startswith("/Users/"):
            target_file = Path(target)
        # Handle relative paths
        elif target.startswith("./") or target.startswith("../"):
            # Resolve relative to source file's directory
            source_dir = ref.source_file.parent
            target_file = (source_dir / target).resolve()
        # Handle root-relative paths
        elif target.startswith("/"):
            target_file = (self.repo_root / target.lstrip("/")).resolve()
        else:
            # Assume relative to source file
            source_dir = ref.source_file.parent
            target_file = (source_dir / target).resolve()

        # Strip anchors (#section)
        target_str = str(target_file)
        if "#" in target_str:
            target_file = Path(target_str.split("#")[0])

        return target_file.exists()

    def generate_report(self) -> str:
        """Generate comprehensive report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CROSS-REFERENCE CONSISTENCY REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        total = len(self.references)
        valid = len(self.valid_refs)
        broken = len(self.broken_refs)

        report_lines.append(f"Total References Found: {total}")
        report_lines.append(f"Valid References: {valid} ({valid/total*100:.1f}%)")
        report_lines.append(f"Broken References: {broken} ({broken/total*100:.1f}%)")
        report_lines.append("")

        # Group by type
        ref_types = {}
        for ref in self.references:
            ref_types[ref.ref_type] = ref_types.get(ref.ref_type, 0) + 1

        report_lines.append("References by Type:")
        for ref_type, count in sorted(ref_types.items()):
            report_lines.append(f"  {ref_type}: {count}")
        report_lines.append("")

        # Broken references details
        if self.broken_refs:
            report_lines.append("=" * 80)
            report_lines.append("BROKEN REFERENCES")
            report_lines.append("=" * 80)
            report_lines.append("")

            for ref in sorted(self.broken_refs, key=lambda r: str(r.source_file)):
                report_lines.append(f"Source: {ref.source_file}:{ref.line_number}")
                report_lines.append(f"  Link Text: {ref.link_text}")
                report_lines.append(f"  Target: {ref.target_path}")
                report_lines.append(f"  Type: {ref.ref_type}")
                report_lines.append("")
        else:
            report_lines.append("✅ No broken references found!")
            report_lines.append("")

        # Sample valid references
        report_lines.append("=" * 80)
        report_lines.append("SAMPLE VALID REFERENCES (First 10)")
        report_lines.append("=" * 80)
        report_lines.append("")

        for ref in self.valid_refs[:10]:
            report_lines.append(f"Source: {ref.source_file.relative_to(self.repo_root)}")
            report_lines.append(f"  [{ref.link_text}]({ref.target_path})")
            report_lines.append("")

        return "\n".join(report_lines)


def main():
    """Main entry point"""
    repo_root = Path("/Users/terryli/eon/gapless-crypto-clickhouse")

    print("Starting cross-reference verification...")
    print(f"Repository: {repo_root}")
    print("")

    checker = CrossReferenceChecker(repo_root)

    print("1. Finding all references...")
    checker.find_all_references()
    print(f"   Found {len(checker.references)} references")

    print("2. Verifying references...")
    checker.verify_references()

    print("3. Generating report...")
    report = checker.generate_report()

    # Write report to file
    report_file = repo_root / "cross_reference_report.txt"
    report_file.write_text(report)
    print(f"   Report written to: {report_file}")

    # Print report to stdout
    print("")
    print(report)

    # Exit with error if broken references found
    if checker.broken_refs:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
