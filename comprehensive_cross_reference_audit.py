#!/usr/bin/env python3
"""Comprehensive cross-reference audit for the repository."""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from urllib.parse import unquote

class ReferenceAuditor:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.broken_refs = []
        self.valid_refs = []
        self.issues = []

    def extract_markdown_links(self, content: str) -> List[Tuple[str, int]]:
        """Extract markdown link paths [text](path) with line numbers."""
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        lines = content.split('\n')
        results = []

        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(pattern, line)
            for match in matches:
                text, path = match.groups()
                # Skip HTTP/HTTPS URLs and anchors
                if path.startswith(('http://', 'https://', '#', 'mailto:')):
                    continue
                results.append((path, line_num))

        return results

    def extract_python_imports(self, content: str) -> List[Tuple[str, int]]:
        """Extract Python module references in documentation."""
        results = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Look for import statements in code blocks or inline code
            if 'import ' in line or 'from ' in line:
                # Extract module paths
                import_pattern = r'(?:from|import)\s+([\w.]+)'
                matches = re.finditer(import_pattern, line)
                for match in matches:
                    module = match.group(1)
                    results.append((module, line_num))

        return results

    def extract_file_references(self, content: str) -> List[Tuple[str, int]]:
        """Extract file path references in text (non-markdown links)."""
        results = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Pattern for backtick-quoted file paths
            pattern = r'`([^`]+\.(md|py|yaml|yml|json|txt|sh|mmd))`'
            matches = re.finditer(pattern, line)
            for match in matches:
                path = match.group(1)
                results.append((path, line_num))

        return results

    def resolve_path(self, source_file: Path, referenced_path: str) -> Path:
        """Resolve a referenced path relative to source file or repo root."""
        # Remove URL fragments and query strings
        referenced_path = referenced_path.split('#')[0].split('?')[0]

        # Decode URL encoding
        referenced_path = unquote(referenced_path)

        # Handle absolute paths
        if referenced_path.startswith('/Users/'):
            return Path(referenced_path)

        # Handle relative paths
        if referenced_path.startswith('./') or referenced_path.startswith('../'):
            return (source_file.parent / referenced_path).resolve()

        # Try as absolute from repo root
        abs_path = self.repo_root / referenced_path
        if abs_path.exists():
            return abs_path

        # Try relative to source file
        rel_path = (source_file.parent / referenced_path).resolve()
        return rel_path

    def check_python_module(self, module_name: str) -> bool:
        """Check if a Python module exists in the repository."""
        # Convert module path to file path
        module_parts = module_name.split('.')

        # Check for package directory
        package_path = self.repo_root / 'src' / '/'.join(module_parts)
        if package_path.is_dir() and (package_path / '__init__.py').exists():
            return True

        # Check for module file
        module_file = self.repo_root / 'src' / '/'.join(module_parts[:-1]) / f"{module_parts[-1]}.py"
        if module_file.exists():
            return True

        return False

    def audit_file(self, md_file: Path) -> None:
        """Audit a single markdown file for all types of references."""
        try:
            content = md_file.read_text(encoding='utf-8')

            # Check markdown links
            md_links = self.extract_markdown_links(content)
            for ref_path, line_num in md_links:
                resolved = self.resolve_path(md_file, ref_path)
                if resolved.exists():
                    self.valid_refs.append({
                        'source': md_file.relative_to(self.repo_root),
                        'target': ref_path,
                        'type': 'markdown_link',
                        'line': line_num,
                        'status': 'valid'
                    })
                else:
                    self.broken_refs.append({
                        'source': md_file.relative_to(self.repo_root),
                        'target': ref_path,
                        'resolved': resolved,
                        'type': 'markdown_link',
                        'line': line_num,
                        'status': 'broken'
                    })

            # Check Python imports
            py_imports = self.extract_python_imports(content)
            for module, line_num in py_imports:
                # Only check if it looks like a project module
                if module.startswith('gapless_crypto'):
                    if not self.check_python_module(module):
                        self.issues.append({
                            'source': md_file.relative_to(self.repo_root),
                            'target': module,
                            'type': 'python_import',
                            'line': line_num,
                            'status': 'potentially_broken'
                        })

            # Check file references in backticks
            file_refs = self.extract_file_references(content)
            for ref_path, line_num in file_refs:
                resolved = self.resolve_path(md_file, ref_path)
                if not resolved.exists():
                    self.issues.append({
                        'source': md_file.relative_to(self.repo_root),
                        'target': ref_path,
                        'resolved': resolved,
                        'type': 'backtick_reference',
                        'line': line_num,
                        'status': 'potentially_broken'
                    })

        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    def generate_report(self) -> str:
        """Generate comprehensive audit report."""
        total = len(self.valid_refs) + len(self.broken_refs)

        report = []
        report.append("# Cross-Reference Consistency Audit (Clean Slate)\n")
        report.append("## Reference Statistics\n")
        report.append(f"- Total markdown link references: {total}")
        report.append(f"- Valid references: {len(self.valid_refs)}")
        report.append(f"- Broken references: {len(self.broken_refs)}")
        report.append(f"- Potential issues found: {len(self.issues)}")

        if total > 0:
            success_rate = (len(self.valid_refs) / total) * 100
            report.append(f"- Success rate: {success_rate:.1f}%")

        report.append("\n## Broken References\n")
        if self.broken_refs:
            for i, ref in enumerate(self.broken_refs, 1):
                report.append(f"{i}. **File**: `{ref['source']}` (line {ref['line']})")
                report.append(f"   - **References**: `{ref['target']}`")
                report.append(f"   - **Resolved to**: `{ref['resolved']}`")
                report.append(f"   - **Status**: Missing/Wrong Path\n")
        else:
            report.append("No broken markdown link references found! ✅\n")

        report.append("\n## Potential Issues\n")
        if self.issues:
            # Group by type
            by_type: Dict[str, List] = {}
            for issue in self.issues:
                issue_type = issue['type']
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)

            for issue_type, issues_list in by_type.items():
                report.append(f"\n### {issue_type.replace('_', ' ').title()} ({len(issues_list)})\n")
                for issue in issues_list[:10]:  # Show first 10
                    report.append(f"- `{issue['source']}` (line {issue['line']}) → `{issue['target']}`")
        else:
            report.append("No potential issues found! ✅\n")

        report.append("\n## Consistency Issues\n")
        # Check for path format consistency
        path_formats = {'absolute': 0, 'relative': 0, 'repo_relative': 0}
        for ref in self.valid_refs:
            target = ref['target']
            if target.startswith('/Users/'):
                path_formats['absolute'] += 1
            elif target.startswith(('./','../')):
                path_formats['relative'] += 1
            else:
                path_formats['repo_relative'] += 1

        report.append(f"- Absolute paths: {path_formats['absolute']}")
        report.append(f"- Relative paths (./ or ../): {path_formats['relative']}")
        report.append(f"- Repository-relative paths: {path_formats['repo_relative']}")

        # Calculate score
        score = 10
        if self.broken_refs:
            score -= min(len(self.broken_refs) * 2, 5)
        if self.issues:
            score -= min(len(self.issues) * 0.5, 3)

        # Check for path format inconsistency
        if path_formats['absolute'] > 0 and path_formats['repo_relative'] > 0:
            report.append("\n⚠️  **Inconsistency detected**: Mix of absolute and repo-relative paths")
            score -= 1

        report.append(f"\n## Score: {max(0, int(score))}/10\n")

        rationale = []
        if self.broken_refs:
            rationale.append(f"{len(self.broken_refs)} broken markdown links")
        if self.issues:
            rationale.append(f"{len(self.issues)} potential issues")
        if path_formats['absolute'] > 0 and path_formats['repo_relative'] > 0:
            rationale.append("inconsistent path formats")

        if rationale:
            report.append(f"**Rationale**: Deductions for: {', '.join(rationale)}")
        else:
            report.append("**Rationale**: All references are valid and consistent!")

        return '\n'.join(report)

def main():
    repo_root = Path('/Users/terryli/eon/gapless-crypto-clickhouse')
    auditor = ReferenceAuditor(repo_root)

    # Find all markdown files (excluding node_modules and tmp/archive)
    md_files = []
    for md_file in repo_root.rglob('*.md'):
        if 'node_modules' in str(md_file) or 'tmp/archive' in str(md_file):
            continue
        md_files.append(md_file)

    print(f"Auditing {len(md_files)} markdown files...")

    # Audit all files
    for md_file in sorted(md_files):
        auditor.audit_file(md_file)

    # Generate report
    report = auditor.generate_report()
    print(report)

    # Save report
    report_file = repo_root / 'CROSS_REFERENCE_AUDIT_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved to: {report_file}")

if __name__ == '__main__':
    main()
