"""
iNaturalist API integration via MCP server
"""
from typing import Optional, Dict, Any
from mcp import ClientSession
from mcp.client.sse import sse_client

from ..config import INAT_MCP_URL


class INatValidator:
    """iNaturalist API integration for species/location validation

    Includes caching to avoid repeated API calls during validation runs.
    """

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or INAT_MCP_URL

        # Caches for validation run
        self._species_cache: Dict[str, Dict[str, Any]] = {}
        self._location_cache: Dict[str, Dict[str, Any]] = {}
        self._record_cache: Dict[str, Dict[str, Any]] = {}

    async def check_species(self, genus: str, species: str, family: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate species against iNaturalist database with caching

        Args:
            genus: Genus name
            species: Species epithet
            family: Optional family name for additional validation

        Returns:
            Dict with validation results including hierarchy info
        """
        # Check cache first
        cache_key = f"{genus}_{species}_{family or ''}"
        if cache_key in self._species_cache:
            return self._species_cache[cache_key]

        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Search for species
                full_name = f"{genus} {species}"
                result = await session.call_tool("search_species", {
                    "query": full_name,
                    "limit": 3
                })

                if result.get('results'):
                    # Check if any result matches
                    for taxon in result['results']:
                        if genus.lower() in taxon.get('name', '').lower():
                            validated = {
                                'valid': True,
                                'taxon_id': taxon['taxon_id'],
                                'correct_name': taxon['name'],
                                'common_name': taxon.get('preferred_common_name', ''),
                                'family': taxon.get('family'),
                                'genus': taxon.get('genus'),
                                'species': taxon.get('species')
                            }

                            # Check hierarchy if family provided
                            if family and taxon.get('family'):
                                if taxon['family'].lower() != family.lower():
                                    validated['hierarchy_mismatch'] = True
                                    validated['suggested_family'] = taxon['family']

                            # Cache and return
                            self._species_cache[cache_key] = validated
                            return validated

                not_found = {'valid': False, 'error': 'Species not found'}
                self._species_cache[cache_key] = not_found
                return not_found

    async def check_location(self, county: str, state: str, country: str) -> Dict[str, Any]:
        """
        Validate location against iNaturalist places with caching

        Args:
            county: County name
            state: State/province code
            country: Country code

        Returns:
            Dict with validation results
        """
        # Check cache first
        cache_key = f"{county}_{state}_{country}"
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]

        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Search for place
                place_query = f"{county}, {state}, {country}"
                result = await session.call_tool("search_places", {
                    "query": place_query,
                    "limit": 5
                })

                if result.get('results'):
                    validated = {
                        'valid': True,
                        'place_id': result['results'][0]['id'],
                        'display_name': result['results'][0]['display_name']
                    }
                    self._location_cache[cache_key] = validated
                    return validated

                not_found = {'valid': False, 'error': 'Location not found'}
                self._location_cache[cache_key] = not_found
                return not_found

    async def check_record_status(
        self,
        taxon_id: int,
        place_id: Optional[int] = None,
        state: Optional[str] = None,
        county: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if observation is a state or county record with caching

        Args:
            taxon_id: iNaturalist taxon ID
            place_id: Optional iNaturalist place ID
            state: Optional state code
            county: Optional county name

        Returns:
            Dict with record status information
        """
        # Check cache first
        cache_key = f"{taxon_id}_{place_id or ''}_{state or ''}_{county or ''}"
        if cache_key in self._record_cache:
            return self._record_cache[cache_key]

        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Build place parameters
                if place_id:
                    place_param = {"place_id": place_id}
                elif county and state:
                    place_param = {"place_name": f"{county}, {state}"}
                elif state:
                    place_param = {"place_name": state}
                else:
                    return {'error': 'No location specified'}

                # Count existing observations
                result = await session.call_tool("count_observations", {
                    "taxon_id": taxon_id,
                    **place_param,
                    "quality_grade": "research"
                })

                # If no observations, it's a new record
                total = result.get('total_results', 0)
                record_status = {
                    'is_new_record': total == 0,
                    'existing_count': total,
                    'query_url': result.get('query_url', '')
                }

                self._record_cache[cache_key] = record_status
                return record_status

    def clear_cache(self):
        """Clear all caches (useful between validation runs)"""
        self._species_cache.clear()
        self._location_cache.clear()
        self._record_cache.clear()
