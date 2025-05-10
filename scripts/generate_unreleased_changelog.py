#!/usr/bin/env python3
"""
Script to create a changelog from the latest tag to the current commit
and add it to the main changelog.md file.
"""

import os
import re
import sys
import subprocess
from collections import defaultdict
from datetime import datetime


def run_cmd(cmd: str) -> str:
    """Run a shell command and return the output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(result.stderr)
        return ""
    return result.stdout.strip()


def get_tags() -> list[str]:
    """Get all git tags sorted by version."""
    tags = run_cmd("git tag -l").split("\n")
    # Sort tags semantically (0.1.0, 0.2.0, etc.)
    return sorted(tags, key=lambda x: [int(n) for n in x.split(".")])


def categorize_commit(message: str) -> str:
    """Categorize a commit message."""
    message = message.lower()

    # Common prefixes in commit messages
    if re.match(r"^add", message) or re.match(r"^feat", message):
        return "added"
    elif re.match(r"^fix", message) or "fix" in message:
        return "fixed"
    elif re.match(r"^change", message) or re.match(r"^refactor", message) or re.match(r"^update", message):
        return "changed"
    elif re.match(r"^remove", message) or re.match(r"^delete", message):
        return "removed"
    elif re.match(r"^deprecate", message):
        return "deprecated"
    elif re.match(r"^security", message) or "security" in message:
        return "security"
    else:
        return "added"  # Default category


def get_file_changes(start_tag: str | None, end_tag: str) -> dict[str, list]:
    """Get detailed file changes between tags."""
    if start_tag is None:
        range_spec = end_tag
    else:
        range_spec = f"{start_tag}..{end_tag}"

    # Get list of changed files with status (A=added, M=modified, D=deleted)
    file_changes = run_cmd(f"git diff --name-status {range_spec}")

    # Parse file changes
    changes = {"added": [], "modified": [], "deleted": [], "renamed": []}

    for line in file_changes.split("\n"):
        if not line.strip():
            continue

        parts = line.split("\t")
        status = parts[0]

        if status.startswith("A"):
            changes["added"].append(parts[-1])
        elif status.startswith("M"):
            changes["modified"].append(parts[-1])
        elif status.startswith("D"):
            changes["deleted"].append(parts[-1])
        elif status.startswith("R"):
            changes["renamed"].append((parts[1], parts[2]))  # From, To

    return changes


def group_files_by_component(files: list[str]) -> dict[str, list[str]]:
    """Group files by component (e.g., adapters, utils, models)."""
    components = defaultdict(list)

    for file in files:
        if "adapters/" in file:
            component = "adapters"
            subcomponent = file.split("adapters/")[1].split("/")[0] if "/adapters/" in file else "core"
            components[f"{component}/{subcomponent}"].append(file)
        elif "helpers/" in file:
            component = "helpers"
            if "decorators/" in file:
                components["helpers/decorators"].append(file)
            elif "utils/" in file:
                components["helpers/utils"].append(file)
            elif "interceptors/" in file:
                components["helpers/interceptors"].append(file)
            elif "metaclasses/" in file:
                components["helpers/metaclasses"].append(file)
            else:
                components["helpers/core"].append(file)
        elif "models/" in file:
            component = "models"
            if "entities/" in file:
                components["models/entities"].append(file)
            elif "dtos/" in file:
                components["models/dtos"].append(file)
            elif "errors/" in file:
                components["models/errors"].append(file)
            elif "types/" in file:
                components["models/types"].append(file)
            else:
                components["models/core"].append(file)
        elif "configs/" in file:
            components["configs"].append(file)
        elif file.startswith("docs/"):
            components["documentation"].append(file)
        elif file.startswith("tests/") or file.startswith("features/"):
            components["tests"].append(file)
        else:
            components["other"].append(file)

    return components


def analyze_tag_changes(start_tag: str | None, end_tag: str) -> dict:
    """Analyze changes between two tags in detail."""
    print(f"Analyzing changes between {start_tag or 'beginning'} and {end_tag}...")

    # Get commits
    if start_tag is None:
        range_spec = end_tag
    else:
        range_spec = f"{start_tag}..{end_tag}"

    # Get commit messages
    commits = run_cmd(f"git log {range_spec} --pretty=format:'%s'").split("\n")
    commits = [c for c in commits if c]

    # Get file changes
    file_changes = get_file_changes(start_tag, end_tag)

    # Group files by component
    added_by_component = group_files_by_component(file_changes["added"])
    modified_by_component = group_files_by_component(file_changes["modified"])
    deleted_by_component = group_files_by_component(file_changes["deleted"])

    # Categorize commits
    categorized_commits = defaultdict(list)
    for commit in commits:
        category = categorize_commit(commit)
        # Clean up the commit message
        message = commit
        # Remove common prefixes
        message = re.sub(
            r"^(fix|feat|chore|docs|style|refactor|perf|test|build|ci|revert)(\([^)]+\))?:", "", message
        ).strip()
        # Capitalize first letter
        if message:
            message = message[0].upper() + message[1:]
        if message:
            categorized_commits[category].append(message)

    return {
        "commits": categorized_commits,
        "file_changes": file_changes,
        "added_by_component": added_by_component,
        "modified_by_component": modified_by_component,
        "deleted_by_component": deleted_by_component,
    }


def add_unreleased_to_changelog() -> None:
    """Generate a changelog for unreleased changes and add it to the main changelog.md file."""
    # Path to the main changelog file
    changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs/changelog.md")

    if not os.path.exists(changelog_path):
        print(f"Error: Changelog file not found at {changelog_path}")
        sys.exit(1)

    # Get tags
    tags = get_tags()
    if not tags:
        print("No tags found in repository")
        sys.exit(1)

    latest_tag = tags[-1]
    print(f"Latest tag: {latest_tag}")
    print(f"Generating changelog from {latest_tag} to HEAD (current commit)...")

    # The new version should be incremented from the latest tag
    version_parts = latest_tag.split(".")
    # Increment the last part (patch version)
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    new_version = ".".join(version_parts)

    today = datetime.now().strftime("%Y-%m-%d")

    # Set prev_tag explicitly to the latest tag
    prev_tag = latest_tag

    # Generate changelog using analyze_tag_changes with HEAD as the end tag
    analysis_results = analyze_tag_changes(prev_tag, "HEAD")

    # If there are no commits since the last tag, exit
    if not any(analysis_results["commits"].values()):
        print("No changes detected since the last tag.")
        sys.exit(0)

    # Build the new changelog entry
    new_entry = f"## [{new_version}] - {today}\n\n"

    # Add sections for each change category
    categories = [
        ("Added", "added", "New features and functionality"),
        ("Changed", "changed", "Changes to existing functionality"),
        ("Fixed", "fixed", "Bug fixes and improvements"),
        ("Removed", "removed", "Removed features or functionality"),
        ("Deprecated", "deprecated", "Features that will be removed in future versions"),
        ("Security", "security", "Security enhancements"),
    ]

    # Add sections only if they have content
    for title, key, description in categories:
        if key in analysis_results["commits"] and analysis_results["commits"][key]:
            new_entry += f"### {title}\n\n"

            # Group by component if possible
            by_component = defaultdict(list)
            for message in analysis_results["commits"][key]:
                # Try to identify component from message
                component = "General"
                for comp in ["adapter", "model", "config", "util", "decorator", "test"]:
                    if comp in message.lower():
                        component = comp.capitalize() + "s"
                        break
                by_component[component].append(message)

            # Output by component
            for component, messages in by_component.items():
                if component != "General":
                    new_entry += f"#### {component}\n\n"
                for message in messages:
                    new_entry += f"- {message}\n"
                new_entry += "\n"

            # If there was only "General" component, don't add the extra newline
            if len(by_component) == 1 and "General" in by_component:
                new_entry += "\n"

    # Read the existing changelog content
    with open(changelog_path, "r") as f:
        content = f.read()

    # Find position to insert new entry (after the header)
    header_match = re.search(r"^# Changelog\s+[^\n]*\s+", content, re.MULTILINE)
    if header_match:
        insert_pos = header_match.end()
        new_content = content[:insert_pos] + "\n" + new_entry + content[insert_pos:]
    else:
        # If no header found, prepend the new entry
        new_content = new_entry + content

    # Write the updated content back to the file
    with open(changelog_path, "w") as f:
        f.write(new_content)

    print(f"Added {new_version} changelog to {changelog_path}")


if __name__ == "__main__":
    add_unreleased_to_changelog()
