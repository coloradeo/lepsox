"""
iNaturalist API integration via MCP server
"""
from typing import Optional, Dict, Any
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

from ..config import INAT_MCP_URL, US_STATE_NAMES


class INatValidator:
    """iNaturalist API integration for species/location validation

    Note: MCP server handles caching, so we don't cache on our side.
    """

    def __init__(self, server_url: Optional[str] = None, timeout: int = 30, mock_mode: bool = False):
        self.server_url = server_url or INAT_MCP_URL
        self.timeout = timeout  # Timeout in seconds for MCP calls
        self.mock_mode = mock_mode  # Use mock responses instead of real MCP calls

    async def check_species(self, genus: str, species: str, family: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate species against iNaturalist database

        Args:
            genus: Genus name
            species: Species epithet
            family: Optional family name for additional validation

        Returns:
            Dict with validation results including hierarchy info
        """
        # Mock mode for testing without MCP server
        if self.mock_mode:
            return {
                'valid': False,
                'error': 'Mock mode - MCP server not available',
                'needs_manual_review': True
            }

        try:
            # Apply timeout to entire MCP call
            return await asyncio.wait_for(
                self._check_species_impl(genus, species, family),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return {'valid': False, 'error': f'Timeout after {self.timeout}s', 'needs_manual_review': True}
        except Exception as e:
            return {'valid': False, 'error': f'MCP error: {str(e)}', 'needs_manual_review': True}

    async def _check_species_impl(self, genus: str, species: str, family: Optional[str] = None) -> Dict[str, Any]:
        """Internal implementation for check_species"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Search for species
                full_name = f"{genus} {species}"
                result = await session.call_tool("search_species", {
                    "query": full_name,
                    "limit": 3
                })

                # Use structuredContent (direct dict) instead of parsing content text
                data = result.structuredContent if hasattr(result, 'structuredContent') else {}

                if data.get('results'):
                    # Check if any result matches
                    for taxon in data['results']:
                        if genus.lower() in taxon.get('name', '').lower():
                            validated = {
                                'valid': True,
                                'taxon_id': taxon.get('id'),  # MCP returns 'id', not 'taxon_id'
                                'correct_name': taxon['name'],
                                'common_name': taxon.get('common_name', ''),
                                'family': taxon.get('family'),
                                'genus': taxon.get('genus'),
                                'species': taxon.get('species'),
                                'rank': taxon.get('rank')
                            }

                            # Check hierarchy if family provided
                            if family and taxon.get('family'):
                                if taxon['family'].lower() != family.lower():
                                    validated['hierarchy_mismatch'] = True
                                    validated['suggested_family'] = taxon['family']

                            return validated

                return {'valid': False, 'error': 'Species not found'}

    async def check_location(self, county: str, state: str, country: str) -> Dict[str, Any]:
        """
        Validate location against iNaturalist places

        Args:
            county: County name
            state: State/province code
            country: Country code

        Returns:
            Dict with validation results
        """
        # Mock mode for testing without MCP server
        if self.mock_mode:
            return {'valid': False, 'error': 'Mock mode - MCP server not available', 'needs_manual_review': True}

        try:
            return await asyncio.wait_for(
                self._check_location_impl(county, state, country),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return {'valid': False, 'error': f'Timeout after {self.timeout}s', 'needs_manual_review': True}
        except Exception as e:
            return {'valid': False, 'error': f'MCP error: {str(e)}', 'needs_manual_review': True}

    async def _check_location_impl(self, county: str, state: str, country: str) -> Dict[str, Any]:
        """Internal implementation for check_location"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Search for place - add "County" suffix for better iNat matching
                # iNat searches better with just "County Name County" than full "County, State, Country"
                place_query = f"{county} County"
                result = await session.call_tool("search_places", {
                    "query": place_query,
                    "limit": 5
                })

                # Use structuredContent (direct dict) instead of parsing content text
                data = result.structuredContent if hasattr(result, 'structuredContent') else {}

                if data.get('results'):
                    # Filter results to match the correct state/country if possible
                    for place in data['results']:
                        display = place.get('display_name', '')
                        # Check if this result matches our state (simple check)
                        if state in display or country in display:
                            return {
                                'valid': True,
                                'place_id': place['id'],
                                'display_name': place['display_name']
                            }

                    # If no exact match, return first result
                    return {
                        'valid': True,
                        'place_id': data['results'][0]['id'],
                        'display_name': data['results'][0]['display_name']
                    }

                return {'valid': False, 'error': 'Location not found'}

    async def check_record_status(
        self,
        taxon_id: int,
        place_id: Optional[int] = None,
        state: Optional[str] = None,
        county: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if observation is a state or county record

        Args:
            taxon_id: iNaturalist taxon ID
            place_id: Optional iNaturalist place ID
            state: Optional state code
            county: Optional county name

        Returns:
            Dict with record status information
        """
        try:
            return await asyncio.wait_for(
                self._check_record_status_impl(taxon_id, place_id, state, county),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return {'error': f'Timeout after {self.timeout}s'}
        except Exception as e:
            return {'error': f'MCP error: {str(e)}'}

    async def _check_record_status_impl(
        self,
        taxon_id: int,
        place_id: Optional[int] = None,
        state: Optional[str] = None,
        county: Optional[str] = None
    ) -> Dict[str, Any]:
        """Internal implementation for check_record_status"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # If no place_id but we have a state, look it up
                if not place_id and state:
                    # Convert state code to full name (e.g., MN → Minnesota)
                    state_name = US_STATE_NAMES.get(state.upper(), state)

                    # Search for the state place_id
                    search_result = await session.call_tool("search_places", {
                        "query": state_name,
                        "limit": 1
                    })

                    search_data = search_result.structuredContent if hasattr(search_result, 'structuredContent') else {}
                    if search_data.get('results'):
                        place_id = search_data['results'][0]['id']
                    else:
                        return {'error': f'Could not find place_id for state: {state_name}'}

                # Build parameters for count_observations
                if not place_id:
                    return {'error': 'Could not determine place_id for location'}

                params = {
                    "taxon_id": taxon_id,
                    "place_id": place_id
                }

                # Count existing observations
                result = await session.call_tool("count_observations", params)

                # Use structuredContent (direct dict) instead of parsing content text
                data = result.structuredContent if hasattr(result, 'structuredContent') else {}

                # If no observations, it's a new record
                # MCP server returns 'count', not 'total_results'
                total = data.get('count', 0)
                return {
                    'is_new_record': total == 0,
                    'existing_count': total,
                    'query_url': data.get('query_url', '')
                }
