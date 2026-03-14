"""
AI Security Review Agent

Uses Claude to review code diffs for security vulnerabilities:
- Injection attacks (SQL, command, XSS)
- Authentication/authorization bypasses
- Secrets/credentials exposure
- Insecure data handling
- OWASP Top 10 violations

Modes:
- Default: Reviews git diff only (changed lines)
- --full-scan: Reviews all Python source files for a baseline audit

Exit code 0 = pass, 1 = security issues found.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

import anthropic


DIFF_SYSTEM_PROMPT = """You are a senior application security engineer reviewing a code diff.
Analyze the changes for security vulnerabilities. Focus on:

1. **Injection** — SQL injection, command injection, XSS, template injection
2. **Auth bypass** — missing authentication checks, broken access control, privilege escalation
3. **Secrets exposure** — hardcoded API keys, passwords, tokens, connection strings
4. **Insecure data handling** — unvalidated input, missing sanitization, unsafe deserialization
5. **OWASP Top 10** — any other common web application security issues

Rules:
- Only flag REAL security issues in the CHANGED lines (+ lines in the diff)
- Do NOT flag style issues, performance issues, or best-practice suggestions
- Do NOT flag test files unless they contain hardcoded real credentials
- For each issue, specify: severity (CRITICAL/HIGH/MEDIUM), file, line, and a one-line fix
- If the diff is clean, respond with exactly: NO_ISSUES_FOUND

Output format when issues are found:
SECURITY_ISSUES_FOUND

[SEVERITY] file:line — Description
  Fix: One-line remediation

Example:
SECURITY_ISSUES_FOUND

[HIGH] api/server.py:42 — SQL query built with f-string using user input
  Fix: Use parameterized query with SQLAlchemy bindparams

[MEDIUM] api/auth.py:15 — JWT secret hardcoded as string literal
  Fix: Load from environment variable"""

FULL_SCAN_SYSTEM_PROMPT = """You are a senior application security engineer performing a full security audit.
Analyze the provided source code for security vulnerabilities. Focus on:

1. **Injection** — SQL injection, command injection, XSS, template injection
2. **Auth bypass** — missing authentication checks, broken access control, privilege escalation
3. **Secrets exposure** — hardcoded API keys, passwords, tokens, connection strings
4. **Insecure data handling** — unvalidated input, missing sanitization, unsafe deserialization
5. **OWASP Top 10** — any other common web application security issues

Rules:
- Only flag REAL security issues, not style or performance
- Do NOT flag test files unless they contain hardcoded real credentials
- For each issue, specify: severity (CRITICAL/HIGH/MEDIUM), file, line, and a one-line fix
- If the code is clean, respond with exactly: NO_ISSUES_FOUND

Output format when issues are found:
SECURITY_ISSUES_FOUND

[SEVERITY] file:line — Description
  Fix: One-line remediation"""

SCAN_DIRS = ["api", "lambda", "scripts"]


def get_diff():
    """Get the git diff to review."""
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True)
        result = subprocess.run(
            ["git", "diff", f"origin/{base_ref}...HEAD", "--", "*.py"],
            capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "--", "*.py"],
            capture_output=True, text=True
        )
    return result.stdout


def collect_source_files():
    """Collect all Python source files from scan directories."""
    files = []
    for scan_dir in SCAN_DIRS:
        path = Path(scan_dir)
        if path.exists():
            files.extend(sorted(path.rglob("*.py")))
    return files


def build_source_payload(files):
    """Read source files and build a single payload for review."""
    chunks = []
    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8")
            chunks.append(f"### {filepath}\n```python\n{content}\n```")
        except (OSError, UnicodeDecodeError):
            continue
    return "\n\n".join(chunks)


def review_code(code: str, system_prompt: str, mode_label: str) -> tuple[bool, str]:
    """Send code to Claude for security review. Returns (has_issues, response)."""
    client = anthropic.Anthropic()

    if mode_label == "diff":
        user_msg = f"Review this code diff for security vulnerabilities:\n\n```diff\n{code}\n```"
    else:
        user_msg = f"Perform a full security audit of the following source files:\n\n{code}"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}]
    )

    response = message.content[0].text
    has_issues = "SECURITY_ISSUES_FOUND" in response
    return has_issues, response


def main():
    parser = argparse.ArgumentParser(description="AI Security Review Agent")
    parser.add_argument(
        "--full-scan", action="store_true",
        help="Scan all Python source files instead of just the git diff"
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — skipping AI security review")
        sys.exit(0)

    if args.full_scan:
        print("Mode: FULL SCAN — reviewing all Python source files")
        print(f"Scanning directories: {', '.join(SCAN_DIRS)}")
        files = collect_source_files()
        if not files:
            print("No Python files found to scan.")
            sys.exit(0)
        print(f"Found {len(files)} Python files")
        code = build_source_payload(files)
        system_prompt = FULL_SCAN_SYSTEM_PROMPT
        mode_label = "full-scan"
    else:
        print("Mode: DIFF — reviewing changed lines only")
        code = get_diff()
        if not code.strip():
            print("No Python file changes to review.")
            sys.exit(0)
        system_prompt = DIFF_SYSTEM_PROMPT
        mode_label = "diff"

    # Truncate very large inputs to stay within context limits
    max_chars = 80000
    if len(code) > max_chars:
        code = code[:max_chars] + "\n\n... [truncated]"
        print(f"Warning: input truncated to {max_chars} chars")

    print(f"Reviewing {len(code)} chars of Python code...")
    print("=" * 60)

    has_issues, response = review_code(code, system_prompt, mode_label)

    print(response)
    print("=" * 60)

    if has_issues:
        print(f"\nAI Security Review ({mode_label}): FAILED — issues found above")
        sys.exit(1)
    else:
        print(f"\nAI Security Review ({mode_label}): PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
