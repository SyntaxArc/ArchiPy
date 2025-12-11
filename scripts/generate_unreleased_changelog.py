#!/usr/bin/env python3
"""
Script to generate a changelog from the latest tag to HEAD using Conventional Commits
and update the main changelog.md file.
"""

import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple


def run_cmd(cmd: str) -> str:
    """Run a shell command and return the output, raising an error on failure."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running command '{cmd}': {e.stderr}") from e


def get_tags() -> List[str]:
    """Get all git tags sorted semantically by version."""
    tags = run_cmd("git tag -l").splitlines()
    return sorted(tags, key=lambda x: [int(n) for n in x.lstrip("v").split(".") if n.isdigit()])


def categorize_commit(message: str) -> str:
    """Categorize a commit message based on Conventional Commits types."""
    message = message.lower().strip()
    conventional_types = {
        "feat": "added",
        "fix": "fixed",
        "docs": "documentation",
        "style": "style",
        "refactor": "changed",
        "test": "tests",
        "chore": "chore",
        "ci": "ci",
        "build": "build",
        "perf": "performance",
        "security": "security",
        "deprecate": "deprecated",
        "remove": "removed",
    }
    for prefix, category in conventional_types.items():
        if message.startswith(f"{prefix}:") or message.startswith(f"{prefix}("):
            return category
    return "chore"  # Default to chore for uncategorized commits


def get_commit_messages(start_tag: Optional[str], end_tag: str) -> List[str]:
    """Get commit messages between two tags or from start_tag to HEAD."""
    range_spec = f"{start_tag}..{end_tag}" if start_tag else end_tag
    commits = run_cmd(f"git log {range_spec} --pretty=format:'%s'").splitlines()
    return [commit.strip() for commit in commits if commit.strip()]


def get_file_changes(start_tag: Optional[str], end_tag: str) -> Dict[str, List]:
    """Get file changes between two tags or from start_tag to HEAD."""
    range_spec = f"{start_tag}..{end_tag}" if start_tag else end_tag
    file_changes = run_cmd(f"git diff --name-status {range_spec}")
    changes = {"added": [], "modified": [], "deleted": [], "renamed": []}

    for line in file_changes.splitlines():
        if not line.strip():
            continue
        status, *paths = line.split("\t")
        if status.startswith("A"):
            changes["added"].append(paths[-1])
        elif status.startswith("M"):
            changes["modified"].append(paths[-1])
        elif status.startswith("D"):
            changes["deleted"].append(paths[-1])
        elif status.startswith("R"):
            changes["renamed"].append((paths[0], paths[1]))
    return changes


def group_files_by_component(files: List[str]) -> Dict[str, List[str]]:
    """Group files by component for changelog organization."""
    components = defaultdict(list)
    for file in files:
        if "adapters/" in file:
            subcomponent = file.split("adapters/")[1].split("/")[0] if "/adapters/" in file else "core"
            components[f"adapters/{subcomponent}"].append(file)
        elif "helpers/" in file:
            component = "helpers"
            subdirs = ["decorators", "utils", "interceptors", "metaclasses"]
            matched = False
            for subdir in subdirs:
                if f"helpers/{subdir}/" in file:
                    components[f"{component}/{subdir}"].append(file)
                    matched = True
                    break
            if not matched:
                components["helpers/core"].append(file)
        elif "models/" in file:
            component = "models"
            subdirs = ["entities", "dtos", "errors", "types"]
            matched = False
            for subdir in subdirs:
                if f"models/{subdir}/" in file:
                    components[f"{component}/{subdir}"].append(file)
                    matched = True
                    break
            if not matched:
                components["models/core"].append(file)
        elif "configs/" in file:
            components["configs"].append(file)
        elif file.startswith("docs/"):
            components["documentation"].append(file)
        elif file.startswith(("tests/", "features/")):
            components["tests"].append(file)
        else:
            components["other"].append(file)
    return components


def format_commit_message(message: str) -> str:
    """Clean and format a commit message for the changelog."""
    # Remove Conventional Commits prefix (e.g., feat(ui):)
    message = re.sub(
        r"^(feat|fix|docs|style|refactor|test|chore|ci|build|perf|security|deprecate|remove)(\([^)]+\))?:",
        "",
        message,
    ).strip()
    # Capitalize first letter
    return message[0].upper() + message[1:] if message else message


def generate_changelog_entry(start_tag: Optional[str], end_tag: str, new_version: str) -> str:
    """Generate a changelog entry for changes between tags."""
    today = datetime.now().strftime("%Y-%m-%d")
    commits = get_commit_messages(start_tag, end_tag)
    if not commits:
        return ""

    # Categorize commits
    categorized_commits = defaultdict(list)
    for commit in commits:
        category = categorize_commit(commit)
        formatted_message = format_commit_message(commit)
        if formatted_message:
            categorized_commits[category].append(formatted_message)

    # File changes for additional context
    file_changes = get_file_changes(start_tag, end_tag)
    added_by_component = group_files_by_component(file_changes["added"])
    modified_by_component = group_files_by_component(file_changes["modified"])
    deleted_by_component = group_files_by_component(file_changes["deleted"])

    # Define changelog categories
    categories = [
        ("Added", "added", "New features and functionality"),
        ("Changed", "changed", "Changes to existing functionality"),
        ("Fixed", "fixed", "Bug fixes and improvements"),
        ("Removed", "removed", "Removed features or functionality"),
        ("Deprecated", "deprecated", "Features marked for future removal"),
        ("Security", "security", "Security enhancements"),
        ("Documentation", "documentation", "Documentation updates"),
        ("Style", "style", "Code style and formatting changes"),
        ("Tests", "tests", "Test additions or updates"),
        ("Chore", "chore", "Maintenance and miscellaneous tasks"),
        ("CI", "ci", "Continuous integration changes"),
        ("Build", "build", "Build system changes"),
        ("Performance", "performance", "Performance improvements"),
    ]

    # Build changelog entry
    changelog_entry = f"## [{new_version}] - {today}\n\n"
    for title, key, _ in categories:
        if key in categorized_commits and categorized_commits[key]:
            changelog_entry += f"### {title}\n\n"
            # Group by component
            by_component = defaultdict(list)
            for message in categorized_commits[key]:
                component = "General"
                for comp in ["adapter", "model", "config", "util", "decorator", "test"]:
                    if comp in message.lower():
                        component = comp.capitalize() + "s"
                        break
                by_component[component].append(message)

            for component, messages in sorted(by_component.items()):
                if component != "General":
                    changelog_entry += f"#### {component}\n\n"
                for message in sorted(messages):
                    changelog_entry += f"- {message}\n"
                changelog_entry += "\n"
    return changelog_entry


def update_changelog() -> None:
    """Update changelog.md with changes from the latest tag to HEAD."""
    changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs/changelog.md")
    if not os.path.exists(changelog_path):
        raise FileNotFoundError(f"Changelog file not found at {changelog_path}")

    tags = get_tags()
    if not tags:
        raise RuntimeError("No tags found in repository")

    latest_tag = tags[-1]
    print(f"Latest tag: {latest_tag}")
    print(f"Generating changelog from {latest_tag} to HEAD...")

    # Increment patch version
    version_parts = latest_tag.lstrip("v").split(".")
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    new_version = f"v{'.'.join(version_parts)}"

    changelog_entry = generate_changelog_entry(latest_tag, "HEAD", new_version)
    if not changelog_entry:
        print("No changes detected since the last tag.")
        return

    # Read existing changelog
    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Insert new entry after the header
    header_match = re.search(r"^# Changelog\s+[^\n]*\s+", content, re.MULTILINE)
    if header_match:
        insert_pos = header_match.end()
        new_content = content[:insert_pos] + "\n" + changelog_entry + content[insert_pos:]
    else:
        new_content = changelog_entry + "\n" + content

    # Write updated changelog
    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated {changelog_path} with version {new_version}")


if __name__ == "__main__":
    try:
        update_changelog()
    except Exception as e:
        print(f"Error: {e}")
