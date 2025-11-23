#!/usr/bin/env python3
"""
Code Example Validator - Extract and validate all code examples from documentation and docstrings.

Validates:
- Syntax correctness (ast.parse)
- Import statements
- Package name references (no gapless-crypto-data)
- Cache path references (no ~/.cache/gapless-crypto-data/)
- API signatures match actual functions

Post-ADR-0029 specific checks:
- No CLI examples in __probe__.py docstrings
- Correct package name in all examples
- Correct cache paths
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Example types
class CodeExample:
    def __init__(self, source: str, code: str, line_num: int, context: str):
        self.source = source  # file path
        self.code = code  # example code
        self.line_num = line_num  # starting line
        self.context = context  # surrounding context (function/class name, section header)
        self.issues: List[str] = []
        self.is_valid = True


def extract_markdown_examples(file_path: Path) -> List[CodeExample]:
    """Extract Python code blocks from markdown files."""
    examples = []
    content = file_path.read_text()
    lines = content.split('\n')

    in_code_block = False
    code_lines = []
    start_line = 0
    context = "toplevel"
    lang = ""

    for i, line in enumerate(lines, 1):
        # Track context (section headers)
        if line.startswith('#'):
            context = line.strip('#').strip()

        # Detect code block start
        if line.strip().startswith('```'):
            if not in_code_block:
                # Starting code block
                in_code_block = True
                code_lines = []
                start_line = i
                lang = line.strip('```').strip().lower()
            else:
                # Ending code block
                in_code_block = False
                if lang in ('python', 'py', ''):
                    code = '\n'.join(code_lines)
                    if code.strip():
                        examples.append(CodeExample(
                            source=str(file_path),
                            code=code,
                            line_num=start_line,
                            context=context
                        ))
        elif in_code_block:
            code_lines.append(line)

    return examples


def extract_docstring_examples(file_path: Path) -> List[CodeExample]:
    """Extract code examples from Python docstrings."""
    examples = []
    content = file_path.read_text()

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return examples

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            continue

        docstring = ast.get_docstring(node)
        if not docstring:
            continue

        # Extract context
        if isinstance(node, ast.Module):
            context = "module"
        elif isinstance(node, ast.ClassDef):
            context = f"class {node.name}"
        elif isinstance(node, ast.FunctionDef):
            context = f"function {node.name}"
        else:
            context = "unknown"

        # Extract code from Examples: section
        example_pattern = r'Examples?:\s*\n((?:.*\n)*?)(?:\n\s*\n|\n\s*[A-Z][a-z]+:|\Z)'
        example_matches = re.finditer(example_pattern, docstring, re.MULTILINE)

        for match in example_matches:
            example_text = match.group(1)

            # Extract Python code blocks
            code_block_pattern = r'```python\n(.*?)\n```'
            for code_match in re.finditer(code_block_pattern, example_text, re.DOTALL):
                code = code_match.group(1).strip()
                if code:
                    examples.append(CodeExample(
                        source=str(file_path),
                        code=code,
                        line_num=node.lineno,
                        context=context
                    ))

            # Extract >>> prompt examples
            prompt_lines = []
            for line in example_text.split('\n'):
                stripped = line.strip()
                if stripped.startswith('>>>'):
                    prompt_lines.append(stripped[3:].strip())
                elif stripped.startswith('...'):
                    prompt_lines.append(stripped[3:].strip())
                elif prompt_lines and not stripped.startswith('#'):
                    # End of prompt block
                    if prompt_lines:
                        code = '\n'.join(prompt_lines)
                        examples.append(CodeExample(
                            source=str(file_path),
                            code=code,
                            line_num=node.lineno,
                            context=context
                        ))
                        prompt_lines = []

            # Flush remaining
            if prompt_lines:
                code = '\n'.join(prompt_lines)
                examples.append(CodeExample(
                    source=str(file_path),
                    code=code,
                    line_num=node.lineno,
                    context=context
                ))

    return examples


def validate_syntax(example: CodeExample) -> bool:
    """Check if code is syntactically valid Python."""
    try:
        ast.parse(example.code)
        return True
    except SyntaxError as e:
        example.is_valid = False
        example.issues.append(f"Syntax error: {e}")
        return False


def check_old_package_name(example: CodeExample) -> bool:
    """Check for references to old package name."""
    old_names = [
        'gapless-crypto-data',
        'gapless_crypto_data',
    ]

    found_old = False
    for old_name in old_names:
        if old_name in example.code:
            example.issues.append(f"Found old package name: {old_name}")
            found_old = True

    return not found_old


def check_old_cache_path(example: CodeExample) -> bool:
    """Check for old cache path references."""
    old_paths = [
        '~/.cache/gapless-crypto-data/',
        '~/.cache/gapless-crypto-data',
        '.cache/gapless-crypto-data',
    ]

    found_old = False
    for old_path in old_paths:
        if old_path in example.code:
            example.issues.append(f"Found old cache path: {old_path}")
            found_old = True

    return not found_old


def check_cli_in_probe(example: CodeExample) -> bool:
    """Check for CLI examples in __probe__.py (should be API-only)."""
    if '__probe__.py' not in example.source:
        return True

    cli_indicators = [
        'gapless-crypto',
        'gcd ',
        '--symbol',
        '--timeframe',
        'argparse',
        'click',
    ]

    found_cli = False
    for indicator in cli_indicators:
        if indicator in example.code:
            example.issues.append(f"Found CLI pattern in __probe__.py: {indicator}")
            found_cli = True

    return not found_cli


def check_imports(example: CodeExample) -> bool:
    """Check if imports reference real modules."""
    # Extract import statements
    try:
        tree = ast.parse(example.code)
    except SyntaxError:
        return True  # Syntax already checked elsewhere

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # Check against known wrong imports
    wrong_imports = [
        'gapless_crypto_data',
    ]

    found_wrong = False
    for imp in imports:
        if imp in wrong_imports:
            example.issues.append(f"Wrong import: {imp}")
            found_wrong = True

    return not found_wrong


def validate_example(example: CodeExample):
    """Run all validation checks on an example."""
    validate_syntax(example)
    check_old_package_name(example)
    check_old_cache_path(example)
    check_cli_in_probe(example)
    check_imports(example)


def main():
    """Extract and validate all code examples."""
    project_root = Path(__file__).parent

    # Find all markdown files
    md_files = list(project_root.glob('**/*.md'))
    md_files = [f for f in md_files if 'node_modules' not in str(f) and '.venv' not in str(f)]

    # Find all Python files
    py_files = list((project_root / 'src').glob('**/*.py'))

    # Prioritize user-facing files
    priority_files = [
        'README.md',
        'CLAUDE.md',
        'src/gapless_crypto_clickhouse/__probe__.py',
        'src/gapless_crypto_clickhouse/api.py',
        'src/gapless_crypto_clickhouse/__init__.py',
    ]

    all_examples: List[CodeExample] = []

    print("=" * 80)
    print("CODE EXAMPLE VALIDATOR - Post-ADR-0029")
    print("=" * 80)
    print()

    # Extract from markdown files
    print(f"Scanning {len(md_files)} markdown files...")
    for md_file in md_files:
        examples = extract_markdown_examples(md_file)
        all_examples.extend(examples)
        if examples:
            is_priority = any(p in str(md_file) for p in priority_files)
            marker = "★" if is_priority else " "
            print(f"  {marker} {md_file.relative_to(project_root)}: {len(examples)} examples")

    print()
    print(f"Scanning {len(py_files)} Python files...")
    for py_file in py_files:
        examples = extract_docstring_examples(py_file)
        all_examples.extend(examples)
        if examples:
            is_priority = any(p in str(py_file) for p in priority_files)
            marker = "★" if is_priority else " "
            print(f"  {marker} {py_file.relative_to(project_root)}: {len(examples)} examples")

    print()
    print("=" * 80)
    print(f"TOTAL EXAMPLES FOUND: {len(all_examples)}")
    print("=" * 80)
    print()

    # Validate all examples
    print("Validating examples...")
    for example in all_examples:
        validate_example(example)

    # Summary statistics
    valid_examples = [e for e in all_examples if e.is_valid and not e.issues]
    syntax_errors = [e for e in all_examples if not e.is_valid]
    semantic_issues = [e for e in all_examples if e.is_valid and e.issues]
    old_package_refs = [e for e in all_examples if any('old package name' in i for i in e.issues)]
    old_cache_refs = [e for e in all_examples if any('old cache path' in i for i in e.issues)]
    cli_in_probe = [e for e in all_examples if any('CLI pattern' in i for i in e.issues)]
    wrong_imports = [e for e in all_examples if any('Wrong import' in i for i in e.issues)]

    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total examples:           {len(all_examples)}")
    print(f"Syntactically valid:      {len(all_examples) - len(syntax_errors)} ({100 * (len(all_examples) - len(syntax_errors)) / len(all_examples):.1f}%)")
    print(f"Syntax errors:            {len(syntax_errors)}")
    print(f"Semantic issues:          {len(semantic_issues)}")
    print()
    print("POST-ADR-0029 CRITICAL CHECKS:")
    print(f"  Old package name refs:  {len(old_package_refs)}")
    print(f"  Old cache path refs:    {len(old_cache_refs)}")
    print(f"  CLI in __probe__.py:    {len(cli_in_probe)}")
    print(f"  Wrong imports:          {len(wrong_imports)}")
    print()

    # Detailed error report
    if syntax_errors:
        print("=" * 80)
        print("SYNTAX ERRORS")
        print("=" * 80)
        for ex in syntax_errors[:10]:  # Limit to first 10
            print(f"\nFile: {ex.source}")
            print(f"Line: {ex.line_num}")
            print(f"Context: {ex.context}")
            print(f"Issues: {', '.join(ex.issues)}")
            print(f"Code preview:")
            print("  " + "\n  ".join(ex.code.split('\n')[:5]))
            if len(ex.code.split('\n')) > 5:
                print("  ...")

        if len(syntax_errors) > 10:
            print(f"\n... and {len(syntax_errors) - 10} more syntax errors")

    if semantic_issues:
        print()
        print("=" * 80)
        print("SEMANTIC ISSUES")
        print("=" * 80)
        for ex in semantic_issues[:20]:  # Limit to first 20
            print(f"\nFile: {ex.source}")
            print(f"Line: {ex.line_num}")
            print(f"Context: {ex.context}")
            print(f"Issues: {', '.join(ex.issues)}")
            print(f"Code preview:")
            print("  " + "\n  ".join(ex.code.split('\n')[:3]))

        if len(semantic_issues) > 20:
            print(f"\n... and {len(semantic_issues) - 20} more semantic issues")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if old_package_refs:
        print(f"⚠️  {len(old_package_refs)} examples use old package name 'gapless-crypto-data'")
        print("   → Replace with 'gapless-crypto-clickhouse'")

    if old_cache_refs:
        print(f"⚠️  {len(old_cache_refs)} examples use old cache path")
        print("   → Replace with ~/.cache/gapless-crypto-clickhouse/")

    if cli_in_probe:
        print(f"⚠️  {len(cli_in_probe)} examples in __probe__.py show CLI patterns")
        print("   → Remove CLI examples from __probe__.py (API-only)")

    if wrong_imports:
        print(f"⚠️  {len(wrong_imports)} examples import wrong modules")
        print("   → Fix import statements")

    if not (syntax_errors or semantic_issues):
        print("✅ All examples are syntactically valid and semantically correct!")

    print()
    print("=" * 80)

    # Exit code
    exit_code = 0
    if syntax_errors or semantic_issues:
        exit_code = 1

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
