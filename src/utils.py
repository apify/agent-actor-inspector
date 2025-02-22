import os

import requests
from apify_client import ApifyClient

from src.const import REQUESTS_TIMEOUT_SECS

APIFY_API_ENDPOINT_GET_DEFAULT_BUILD = 'https://api.apify.com/v2/acts/{actor_id}/builds/default'


def get_actor_id(apify_client: ApifyClient, actor_name: str) -> str:
    """
    Retrieve the actor ID for a given actor name.

    Args:
        apify_client (ApifyClient): An instance of the ApifyClient class.
        actor_name (str): The name of the actor.

    Returns:
        str: The ID of the actor.

    Raises:
        ValueError: If the actor is not found or the actor ID cannot be retrieved.
    """
    if not (actor := apify_client.actor(actor_name).get()):
        raise ValueError(f'Actor {actor_name} not found.')

    if not (actor_id := actor.get('id')):
        raise ValueError(f'Failed to get the Actor object ID for {actor_name}.')

    return actor_id


def generate_file_tree(files: list[dict]) -> dict:
    """
    Generate a file tree hierarchy from a list of file dictionaries.

    Args:
        files (list): List of dictionaries containing 'name' keys with file paths

    Returns:
        dict: Nested dictionary representing the file tree structure
    """
    tree = {}

    for file_info in files:
        # Split the path into components
        path_parts = file_info['name'].split('/')

        # Start with the root of our tree
        current = tree

        # Process each part of the path
        for i, part in enumerate(path_parts):
            # If it's the last part (the file), set it to None
            if i == len(path_parts) - 1:
                current[part] = None
            # Otherwise, it's a directory
            else:
                # If the directory doesn't exist yet, create it
                if part not in current:
                    current[part] = {}
                # Move to the next level
                current = current[part]

    return tree


def get_actor_github_urls(apify_client: ApifyClient, actor_name: str) -> list[str]:
    """
    Retrieve the GitHub repository URLs associated with an actor.

    Args:
        apify_client (ApifyClient): An instance of the ApifyClient class.
        actor_name (str): The name of the actor.

    Returns:
        list[str]: A list of GitHub repository URLs associated with the actor.

    Raises:
        ValueError: If the actor is not found or the actor ID cannot be retrieved.
    """
    actor_id = get_actor_id(apify_client, actor_name)
    github_urls = []
    build = get_actor_latest_build(apify_client, actor_id)
    if github_repo_url := build.get('actVersion', {}).get('gitRepoUrl'):
        github_urls.append(github_repo_url)

    versions = apify_client.actor(actor_id).versions().list().items
    github_urls.extend(version.get('gitRepoUrl') for version in versions if version.get('gitRepoUrl'))

    return github_urls


def github_repo_exists(repository_url: str) -> bool:
    """
    Check if a GitHub repository exists.

    Args:
        repository_url (str): The URL of the GitHub repository.

    Returns:
        bool: True if the repository exists, False otherwise.
    """
    verify_response = requests.get(repository_url, timeout=REQUESTS_TIMEOUT_SECS)
    return verify_response.status_code == requests.codes.ok


def get_actor_source_files(apify_client: ApifyClient, actor_name: str) -> list[dict]:
    """
    Retrieve the source files for a given actor.

    Args:
        apify_client (ApifyClient): An instance of the ApifyClient class.
        actor_name (str): The name of the actor.

    Returns:
        list[dict]: A list of dictionaries representing the source files of the actor.
    """
    actor_id = get_actor_id(apify_client, actor_name)
    versions = apify_client.actor(actor_id).versions().list().items
    latest_vesion = filter(lambda x: x.get('buildTag') == 'latest', versions)
    if not (version := next(latest_vesion, None)):
        return []

    source_files = version.get('sourceFiles')
    text_source_files = filter(lambda x: x.get('format', '').lower() == 'text', source_files)
    return list(text_source_files)


def get_apify_token() -> str:
    """
    Retrieve the Apify API token from environment variables.

    Returns:
        str: The Apify API token.

    Raises:
        ValueError: If the APIFY_TOKEN environment variable is not set.
    """
    if not (token := os.getenv('APIFY_TOKEN')):
        raise ValueError('APIFY_TOKEN environment variable is not set')
    return token


def get_actor_latest_build(apify_client: ApifyClient, actor_name: str) -> dict:
    """Get the latest build of an Actor from the default build tag.

    Args:
        apify_client (ApifyClient): An instance of the ApifyClient class.
        actor_name (str): Actor name from Apify store to run.

    Returns:
        dict: The latest build of the Actor.

    Raises:
        ValueError: If the Actor is not found or the build data is not found.
        TypeError: If the build is not a dictionary.
    """
    actor_obj_id = get_actor_id(apify_client, actor_name)

    url = APIFY_API_ENDPOINT_GET_DEFAULT_BUILD.format(actor_id=actor_obj_id)
    response = requests.request('GET', url, timeout=REQUESTS_TIMEOUT_SECS)

    build = response.json()
    if not isinstance(build, dict):
        msg = f'Failed to get the latest build of the Actor {actor_name}.'
        raise TypeError(msg)

    if (data := build.get('data')) is None:
        msg = f'Failed to get the latest build data of the Actor {actor_name}.'
        raise ValueError(msg)

    return data
