#!/usr/bin/env python3
"""
GitHub Repository Lister
Lists all public repositories for a given GitHub user or organization.
"""

import urllib.request
import json
import sys
from typing import List, Dict, Any


def fetch_repos(username: str, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch repositories for a GitHub user.

    Args:
        username: GitHub username or organization name
        page: Page number for pagination
        per_page: Number of repositories per page (max 100)

    Returns:
        List of repository dictionaries
    """
    url = f"https://api.github.com/users/{username}/repos?page={page}&per_page={per_page}&sort=updated"

    try:
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'GitHub-Repo-Lister')

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Error: User '{username}' not found", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def list_all_repos(username: str) -> List[Dict[str, Any]]:
    """
    Fetch all repositories for a user (handles pagination).

    Args:
        username: GitHub username or organization name

    Returns:
        List of all repository dictionaries
    """
    all_repos = []
    page = 1

    while True:
        repos = fetch_repos(username, page=page)
        if not repos:
            break
        all_repos.extend(repos)
        page += 1

        # GitHub API returns up to 100 repos per page
        if len(repos) < 100:
            break

    return all_repos


def display_repos(repos: List[Dict[str, Any]], username: str):
    """
    Display repository information in a formatted way.

    Args:
        repos: List of repository dictionaries
        username: GitHub username
    """
    if not repos:
        print(f"No repositories found for user '{username}'")
        return

    print(f"\n{'='*80}")
    print(f"GitHub Repositories for: {username}")
    print(f"Total Repositories: {len(repos)}")
    print(f"{'='*80}\n")

    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo['name']}")
        print(f"   URL: {repo['html_url']}")
        print(f"   Description: {repo['description'] or 'No description'}")
        print(f"   Language: {repo['language'] or 'Not specified'}")
        print(f"   Stars: ⭐ {repo['stargazers_count']} | Forks: 🍴 {repo['forks_count']}")
        print(f"   Private: {'Yes' if repo['private'] else 'No'}")
        print(f"   Updated: {repo['updated_at']}")
        print(f"   {'-'*76}")


def main():
    """Main function to list GitHub repositories."""
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        # Default to kumagoro-chan
        username = "kumagoro-chan"
        print(f"No username provided, using default: {username}\n")

    print(f"Fetching repositories for '{username}'...")
    repos = list_all_repos(username)
    display_repos(repos, username)


if __name__ == "__main__":
    main()
