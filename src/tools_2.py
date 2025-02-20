"""This module defines the tools used by the agent.

Feel free to modify or add new tools to suit your specific needs.

To learn how to create a new tool, see:
- https://docs.crewai.com/concepts/tools
"""

from __future__ import annotations

import datetime
import logging

from apify_client import ApifyClient
from crewai.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.models import ActorStoreList, PricingInfo
from src.utils import get_apify_token

# Importing crewAI tools
logger = logging.getLogger('apify')

class SearchRelatedActorsInput(BaseModel):
    """Input schema for SearchRelatedActors."""
    search: str = Field(..., description='A string of keywords to search by. The search is performed across the title,'
                                         'name, description, username, and README of an Actor.')
    limit: int = Field(10, description='The maximum number of Actors to return', gt=0, le=100)
    offset: int = Field(0, description='The number of items to skip from the start of the results.', ge=0)

class SearchRelatedActorsTool(BaseTool):
    name: str = 'search_related_actors'
    description: str = (
        'Discover available Actors using a full-text search with specified keywords.'
        'The tool returns a list of Actors, including details such as name, description, run statistics,'
        'and pricing information, number of stars, and URL.'
        'Search with only few keywords, otherwise it will return empty results'
    )
    args_schema: type[BaseModel] = SearchRelatedActorsInput

    def _run(self, search: str, limit: int = 10, offset: int = 0) -> ActorStoreList | None:
        """ Execute the tool's logic to search related actors by keyword. """
        try:
            logger.info(f"Searching for Actors related to '{search}'")
            apify_client = ApifyClient(token=get_apify_token())
            search_results = apify_client.store().list(limit=limit, offset=offset, search=search).items
            logger.info(f"Found {len(search_results)} Actors related to '{search}'")
        except Exception as e:
            logger.exception(f"Failed to search for Actors related to '{search}'")
            raise ValueError(f"Failed to search for Actors related to '{search}': {e}") from None

        return ActorStoreList.model_validate(search_results, strict=False)

@tool
def tool_get_actor_pricing_information(actor_id: str) -> PricingInfo:
    """Get the pricing information of an Apify Actor.

    Args:
        actor_id (str): The ID of the Apify Actor.

    Returns:
        str: The README content of the specified Actor.

    Raises:
        ValueError: If the README for the Actor cannot be retrieved.
    """
    apify_client = ApifyClient(token=get_apify_token())
    if not (actor := apify_client.actor(actor_id).get()):
        msg = f'Actor {actor_id} not found.'
        raise ValueError(msg)

    if not (pricing_info := actor.get('pricingInfos')):
        raise ValueError(f'Failed to find pricing information for the Actor {actor_id}.')

    current_pricing = None
    for pricing_entry in pricing_info:
        if pricing_entry.get('startedAt') > datetime.datetime.now(datetime.timezone.utc):
            break
        current_pricing = pricing_entry

    return PricingInfo.model_validate(current_pricing)

if __name__ == '__main__':
    # Execute the tool with structured input
    tool = SearchRelatedActorsTool()
    result = tool._run({'search': 'apify', 'limit': 10, 'offset': 0})
    print(result)