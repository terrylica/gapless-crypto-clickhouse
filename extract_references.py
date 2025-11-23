#!/usr/bin/env python3
"""Extract all file references from markdown files."""

import re
from pathlib import Path
from typing import Dict, List, Set

def extract_markdown_links(content: str) -> List[str]:
    """Extract markdown link paths [text](path)."""
    # Match [text](path) but not [text](http://...)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    links = []
    for text, path in matches:
        # Skip HTTP/HTTPS URLs
        if path.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        links.append(path)
    return links

def extract_file_paths(content: str) -> List[str]:
    """Extract file paths mentioned in text."""
    paths = []

    # Pattern for file paths with extensions
    # Matches: docs/file.md, src/module.py, ./relative/path.md, ../parent/file.md
    pattern = r'(?:^|\s|`)((?:\.{0,2}/)?[\w\-./]+\.\w+)(?:\s|`|$|,|;|\))'
    matches = re.findall(pattern, content)

    for match in matches:
        # Filter out common false positives
        if any(ext in match for ext in ['.md', '.py', '.yaml', '.json', '.txt', '.sh']):
            paths.append(match)

    return paths

def main():
    repo_root = Path('/Users/terryli/eon/gapless-crypto-clickhouse')

    # Find all markdown files (excluding node_modules and tmp/archive)
    md_files = []
    for md_file in repo_root.rglob('*.md'):
        if 'node_modules' in str(md_file) or 'tmp/archive' in str(md_file):
            continue
        md_files.append(md_file)

    # Store all references
    references: Dict[str, Set[str]] = {}

    for md_file in sorted(md_files):
        try:
            content = md_file.read_text(encoding='utf-8')

            # Extract both types of references
            md_links = extract_markdown_links(content)
            file_paths = extract_file_paths(content)

            all_refs = set(md_links + file_paths)

            if all_refs:
                references[str(md_file.relative_to(repo_root))] = all_refs

        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    # Print results
    print(f"Found {len(md_files)} markdown files")
    print(f"Found {len(references)} files with references")

    total_refs = sum(len(refs) for refs in references.values())
    print(f"Total references: {total_refs}")

    # Save detailed results
    output_file = repo_root / 'EXTRACTED_REFERENCES.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for source_file, refs in sorted(references.items()):
            f.write(f"\n{source_file}:\n")
            for ref in sorted(refs):
                f.write(f"  - {ref}\n")

    print(f"\nDetailed results saved to: {output_file}")

if __name__ == '__main__':
    main()
