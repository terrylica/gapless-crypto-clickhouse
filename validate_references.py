#!/usr/bin/env python3
"""Validate all file references extracted from markdown files."""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import unquote

def extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    """Extract markdown link paths [text](path) with line context."""
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

def resolve_path(source_file: Path, referenced_path: str, repo_root: Path) -> Path:
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
    abs_path = repo_root / referenced_path
    if abs_path.exists():
        return abs_path

    # Try relative to source file
    rel_path = (source_file.parent / referenced_path).resolve()
    return rel_path

def main():
    repo_root = Path('/Users/terryli/eon/gapless-crypto-clickhouse')

    # Find all markdown files (excluding node_modules and tmp/archive)
    md_files = []
    for md_file in repo_root.rglob('*.md'):
        if 'node_modules' in str(md_file) or 'tmp/archive' in str(md_file):
            continue
        md_files.append(md_file)

    # Validate all references
    broken_refs = []
    valid_refs = []

    for md_file in sorted(md_files):
        try:
            content = md_file.read_text(encoding='utf-8')
            refs = extract_markdown_links(content)

            for ref_path, line_num in refs:
                resolved = resolve_path(md_file, ref_path, repo_root)

                if resolved.exists():
                    valid_refs.append({
                        'source': md_file.relative_to(repo_root),
                        'target': ref_path,
                        'resolved': resolved,
                        'line': line_num
                    })
                else:
                    broken_refs.append({
                        'source': md_file.relative_to(repo_root),
                        'target': ref_path,
                        'resolved': resolved,
                        'line': line_num
                    })

        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    # Print summary
    total = len(valid_refs) + len(broken_refs)
    print(f"Total markdown files: {len(md_files)}")
    print(f"Total references checked: {total}")
    print(f"Valid references: {len(valid_refs)}")
    print(f"Broken references: {len(broken_refs)}")

    if broken_refs:
        print(f"\n{'='*80}")
        print("BROKEN REFERENCES:")
        print(f"{'='*80}\n")

        for ref in broken_refs:
            print(f"File: {ref['source']} (line {ref['line']})")
            print(f"  References: {ref['target']}")
            print(f"  Resolved to: {ref['resolved']}")
            print(f"  Status: MISSING")
            print()

    # Save detailed report
    report_file = repo_root / 'REFERENCE_VALIDATION_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Cross-Reference Validation Report\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total markdown files: {len(md_files)}\n")
        f.write(f"- Total references checked: {total}\n")
        f.write(f"- Valid references: {len(valid_refs)}\n")
        f.write(f"- Broken references: {len(broken_refs)}\n")
        f.write(f"- Success rate: {len(valid_refs)/total*100:.1f}%\n\n")

        if broken_refs:
            f.write(f"## Broken References ({len(broken_refs)})\n\n")
            for ref in sorted(broken_refs, key=lambda x: str(x['source'])):
                f.write(f"### {ref['source']} (line {ref['line']})\n\n")
                f.write(f"- **References**: `{ref['target']}`\n")
                f.write(f"- **Resolved to**: `{ref['resolved']}`\n")
                f.write(f"- **Status**: ❌ MISSING\n\n")

        f.write(f"## Valid References ({len(valid_refs)})\n\n")
        f.write(f"<details>\n<summary>Click to expand</summary>\n\n")
        for ref in sorted(valid_refs, key=lambda x: str(x['source']))[:20]:
            f.write(f"- `{ref['source']}` → `{ref['target']}` ✅\n")
        f.write(f"\n... and {len(valid_refs)-20} more\n")
        f.write(f"</details>\n")

    print(f"\nDetailed report saved to: {report_file}")

if __name__ == '__main__':
    main()
