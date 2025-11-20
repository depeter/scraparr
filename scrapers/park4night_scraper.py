"""
Park4Night API Scraper

This scraper interacts with the park4night.com public API to fetch camping spots,
parking locations, and reviews for motorhomes, campers, and RVs.

API Documentation: https://github.com/gtoselli/park4night-api
"""
import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text, Boolean, JSON, func, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import random
from datetime import datetime


class Park4NightScraper(BaseScraper):
    """
    Scraper for Park4Night public API

    Fetches camping spots and parking locations with reviews and details.
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://guest.park4night.com/services/V4.1"

    def define_tables(self) -> List[Table]:
        """
        Define database tables for storing Park4Night data

        Creates two tables:
        - places: Main camping/parking locations
        - reviews: User reviews for each place
        """
        places_table = Table(
            'places',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('nom', String(500)),
            Column('type', String(100)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('pays', String(100)),
            Column('ville', String(200)),
            Column('description', Text),  # Fallback description (priority: en > fr > nl > de > es > it)
            Column('prix', String(100)),
            Column('rating', Float),
            Column('nb_comment', Integer),
            Column('services', JSON),
            Column('raw_data', JSON),  # Store complete API response
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
        )

        reviews_table = Table(
            'reviews',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer, index=True),  # Foreign key to places.id
            Column('review_id', Integer),  # Original review ID from API
            Column('user_id', Integer),
            Column('username', String(200)),
            Column('note', Float),  # Rating
            Column('comment', Text),
            Column('date', String(50)),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
        )

        # Multilingual descriptions table
        place_descriptions_table = Table(
            'place_descriptions',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer, index=True),  # Foreign key to places.id
            Column('language_code', String(5)),  # ISO 639-1: en, nl, fr, de, es, it
            Column('description', Text),
            Column('created_at', DateTime, default=func.now()),
        )

        return [places_table, reviews_table, place_descriptions_table]

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """
        Store scraped data in database after scraping completes

        Args:
            results: List of places from scraping
            params: Original scraping parameters
        """
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} places in database...")

        try:
            from app.core.database import engine

            async with engine.begin() as conn:
                # Get table references
                tables = self.define_tables()
                places_table = tables[0]
                reviews_table = tables[1]
                place_descriptions_table = tables[2]

                # Create tables if they don't exist
                await conn.run_sync(self.metadata.create_all)

                # Insert or update places
                for place in results:
                    # Helper to safely convert values
                    def safe_int(val):
                        if val is None or val == '':
                            return None
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            return None

                    def safe_float(val):
                        if val is None or val == '':
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    # Extract multilingual descriptions
                    language_descriptions = {}
                    for lang_code in ['en', 'nl', 'fr', 'de', 'es', 'it']:
                        desc = place.get(f'description_{lang_code}')
                        if desc and desc.strip():
                            language_descriptions[lang_code] = desc.strip()

                    # Fallback description (priority: en > fr > nl > de > es > it)
                    fallback_description = (
                        language_descriptions.get('en') or
                        language_descriptions.get('fr') or
                        language_descriptions.get('nl') or
                        language_descriptions.get('de') or
                        language_descriptions.get('es') or
                        language_descriptions.get('it') or
                        place.get('description')
                    )

                    # Prepare place data with type conversions
                    place_data = {
                        'id': safe_int(place.get('id')),
                        'nom': place.get('titre') or place.get('nom'),
                        'type': place.get('type'),
                        'latitude': safe_float(place.get('latitude')),
                        'longitude': safe_float(place.get('longitude')),
                        'pays': place.get('pays'),
                        'ville': place.get('ville'),
                        'description': fallback_description,
                        'prix': place.get('prix_stationnement') or place.get('prix'),
                        'rating': safe_float(place.get('note_moyenne') or place.get('rating')),
                        'nb_comment': safe_int(place.get('nb_commentaires') or place.get('nbComment') or place.get('nb_comment')),
                        'services': place.get('services'),
                        'raw_data': place,  # Store complete response
                        'updated_at': datetime.utcnow(),
                    }

                    # Upsert place (insert or update if exists)
                    stmt = pg_insert(places_table).values(**place_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            'nom': stmt.excluded.nom,
                            'type': stmt.excluded.type,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'pays': stmt.excluded.pays,
                            'ville': stmt.excluded.ville,
                            'description': stmt.excluded.description,
                            'prix': stmt.excluded.prix,
                            'rating': stmt.excluded.rating,
                            'nb_comment': stmt.excluded.nb_comment,
                            'services': stmt.excluded.services,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)

                    # Insert multilingual descriptions
                    place_id = safe_int(place.get('id'))
                    if place_id and language_descriptions:
                        # Delete existing descriptions for this place (to handle updates)
                        from sqlalchemy import delete
                        await conn.execute(
                            delete(place_descriptions_table).where(
                                place_descriptions_table.c.place_id == place_id
                            )
                        )

                        # Insert all language descriptions
                        for lang_code, description in language_descriptions.items():
                            desc_data = {
                                'place_id': place_id,
                                'language_code': lang_code,
                                'description': description,
                            }
                            await conn.execute(
                                place_descriptions_table.insert().values(**desc_data)
                            )

                    # Insert reviews if present
                    reviews = place.get('reviews', [])
                    if reviews:
                        for review in reviews:
                            review_data = {
                                'place_id': safe_int(place.get('id')),
                                'review_id': review.get('id'),
                                'user_id': review.get('user_id'),
                                'username': review.get('username') or review.get('uuid'),
                                'note': review.get('note'),
                                'comment': review.get('comment') or review.get('commentaire'),
                                'date': review.get('date'),
                                'raw_data': review,
                            }

                            # Insert review (skip if already exists)
                            stmt = pg_insert(reviews_table).values(**review_data)
                            stmt = stmt.on_conflict_do_nothing()
                            await conn.execute(stmt)

                await conn.commit()

            self.log(f"✓ Successfully stored {len(results)} places in database schema '{self.schema_name}'")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")
            # Don't raise - we still want the execution to be marked as successful
            # The scraped data is returned even if storage fails

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main scraping method - fetches places by GPS coordinates

        Expected params:
            - latitude: GPS latitude (required, e.g., 42.3383)
            - longitude: GPS longitude (required, e.g., 9.5367)
            - include_reviews: Whether to fetch reviews for each place (default: False)
            - max_places: Maximum number of places to process (default: None, processes all)

        Returns:
            List of place objects with location details
        """
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        include_reviews = params.get("include_reviews", False)
        max_places = params.get("max_places")

        # Validate required parameters
        if latitude is None or longitude is None:
            raise ValueError("Both 'latitude' and 'longitude' parameters are required")

        self.log(f"Fetching places near coordinates: {latitude}, {longitude}")

        # Fetch places
        places = await self._get_places_by_location(latitude, longitude)

        if not places:
            self.log("No places found for the given coordinates")
            return []

        self.log(f"Found {len(places)} places")

        # Limit number of places if specified
        if max_places:
            places = places[:max_places]
            self.log(f"Limited to {max_places} places")

        # Fetch reviews if requested
        if include_reviews:
            self.log("Fetching reviews for each place...")
            places = await self._enrich_with_reviews(places)

        return places

    async def _get_places_by_location(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """
        Fetch places by GPS coordinates

        Args:
            latitude: GPS latitude
            longitude: GPS longitude

        Returns:
            List of place objects (up to 200)
        """
        url = f"{self.BASE_URL}/lieuxGetFilter.php"

        try:
            response = await self.http_client.get(
                url,
                params={
                    "latitude": latitude,
                    "longitude": longitude
                }
            )
            response.raise_for_status()

            data = response.json()

            # The API returns a dict with "lieux" key containing the list of places
            if isinstance(data, dict) and "lieux" in data:
                return data["lieux"]
            elif isinstance(data, list):
                # Fallback for old API format
                return data
            else:
                self.log(f"Unexpected response format: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}", level="warning")
                return []

        except Exception as e:
            self.log(f"Error fetching places: {str(e)}", level="error")
            raise

    async def _get_reviews(self, lieu_id: int) -> List[Dict[str, Any]]:
        """
        Fetch reviews for a specific location

        Args:
            lieu_id: Place identifier

        Returns:
            List of review objects
        """
        url = f"{self.BASE_URL}/commGet.php"

        try:
            response = await self.http_client.get(
                url,
                params={"lieu_id": lieu_id}
            )
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching reviews for place {lieu_id}: {str(e)}", level="warning")
            return []

    async def _enrich_with_reviews(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich places with their reviews

        Args:
            places: List of place objects

        Returns:
            Places with reviews added
        """
        for i, place in enumerate(places):
            lieu_id = place.get("id")

            if lieu_id:
                self.log(f"Fetching reviews for place {i+1}/{len(places)}: {lieu_id}")
                reviews = await self._get_reviews(lieu_id)
                place["reviews"] = reviews
                place["review_count"] = len(reviews)

                # Rate limiting - be respectful to the API
                if i < len(places) - 1:  # Don't sleep after the last request
                    await asyncio.sleep(0.5)
            else:
                place["reviews"] = []
                place["review_count"] = 0

        return places


class Park4NightUserScraper(BaseScraper):
    """
    Scraper for Park4Night user-specific data

    Fetches places created, reviewed, or visited by a specific user.
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://guest.park4night.com/services/V4.1"

    def define_tables(self) -> List[Table]:
        """Define database tables - same structure as Park4NightScraper"""
        places_table = Table(
            'places',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('nom', String(500)),
            Column('type', String(100)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('pays', String(100)),
            Column('ville', String(200)),
            Column('description', Text),
            Column('prix', String(100)),
            Column('rating', Float),
            Column('nb_comment', Integer),
            Column('services', JSON),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
        )

        return [places_table]

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store scraped user places in database"""
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} user places in database...")

        try:
            from app.core.database import engine

            async with engine.begin() as conn:
                tables = self.define_tables()
                places_table = tables[0]

                await conn.run_sync(self.metadata.create_all)

                for place in results:
                    place_data = {
                        'id': place.get('id'),
                        'nom': place.get('nom'),
                        'type': place.get('type'),
                        'latitude': place.get('latitude'),
                        'longitude': place.get('longitude'),
                        'pays': place.get('pays'),
                        'ville': place.get('ville'),
                        'description': place.get('description'),
                        'prix': place.get('prix'),
                        'rating': place.get('rating'),
                        'nb_comment': place.get('nbComment') or place.get('nb_comment'),
                        'services': place.get('services'),
                        'raw_data': place,
                        'updated_at': datetime.utcnow(),
                    }

                    stmt = pg_insert(places_table).values(**place_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={k: stmt.excluded[k] for k in place_data.keys() if k != 'id'}
                    )
                    await conn.execute(stmt)

                await conn.commit()

            self.log(f"✓ Successfully stored {len(results)} places in database schema '{self.schema_name}'")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch user-related places

        Expected params:
            - mode: Type of data to fetch ('created', 'reviewed', or 'visited')
            - uuid: Username (required for 'created' mode)
            - user_id: User identifier (required for 'reviewed' and 'visited' modes)

        Returns:
            List of place objects
        """
        mode = params.get("mode", "created")
        uuid = params.get("uuid")
        user_id = params.get("user_id")

        if mode == "created":
            if not uuid:
                raise ValueError("'uuid' parameter is required for mode='created'")
            return await self._get_user_created_places(uuid)

        elif mode == "reviewed":
            if not user_id:
                raise ValueError("'user_id' parameter is required for mode='reviewed'")
            return await self._get_user_reviewed_places(user_id)

        elif mode == "visited":
            if not user_id:
                raise ValueError("'user_id' parameter is required for mode='visited'")
            return await self._get_user_visited_places(user_id)

        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'created', 'reviewed', or 'visited'")

    async def _get_user_created_places(self, uuid: str) -> List[Dict[str, Any]]:
        """Fetch places created by a user"""
        url = f"{self.BASE_URL}/lieuGetUser.php"

        self.log(f"Fetching places created by user: {uuid}")

        try:
            response = await self.http_client.get(url, params={"uuid": uuid})
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                self.log(f"Found {len(data)} places created by user {uuid}")
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching user created places: {str(e)}", level="error")
            raise

    async def _get_user_reviewed_places(self, user_id: int) -> List[Dict[str, Any]]:
        """Fetch places reviewed by a user"""
        url = f"{self.BASE_URL}/lieuGetCommUser.php"

        self.log(f"Fetching places reviewed by user: {user_id}")

        try:
            response = await self.http_client.get(url, params={"user_id": user_id})
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                self.log(f"Found {len(data)} places reviewed by user {user_id}")
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching user reviewed places: {str(e)}", level="error")
            raise

    async def _get_user_visited_places(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch places visited by a user"""
        url = f"{self.BASE_URL}/lieuGetCommUser.php"

        self.log(f"Fetching places visited by user: {user_id}")

        try:
            response = await self.http_client.get(url, params={"user_id": user_id})
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                self.log(f"Found {len(data)} places visited by user {user_id}")
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching user visited places: {str(e)}", level="error")
            raise


class Park4NightBulkScraper(BaseScraper):
    """
    Bulk scraper for Park4Night - fetches data from multiple locations

    Useful for building a comprehensive database of camping spots in a region.
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://guest.park4night.com/services/V4.1"

    def define_tables(self) -> List[Table]:
        """Define database tables - same as Park4NightScraper"""
        places_table = Table(
            'places',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('nom', String(500)),
            Column('type', String(100)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('pays', String(100)),
            Column('ville', String(200)),
            Column('description', Text),
            Column('prix', String(100)),
            Column('rating', Float),
            Column('nb_comment', Integer),
            Column('services', JSON),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
        )

        reviews_table = Table(
            'reviews',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer, index=True),
            Column('review_id', Integer),
            Column('user_id', Integer),
            Column('username', String(200)),
            Column('note', Float),
            Column('comment', Text),
            Column('date', String(50)),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
        )

        # Multilingual descriptions table
        place_descriptions_table = Table(
            'place_descriptions',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer, index=True),  # Foreign key to places.id
            Column('language_code', String(5)),  # ISO 639-1: en, nl, fr, de, es, it
            Column('description', Text),
            Column('created_at', DateTime, default=func.now()),
        )

        return [places_table, reviews_table, place_descriptions_table]

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store bulk scraped data in database"""
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} places in database...")

        try:
            from app.core.database import engine

            async with engine.begin() as conn:
                tables = self.define_tables()
                places_table = tables[0]
                reviews_table = tables[1]
                place_descriptions_table = tables[2]

                await conn.run_sync(self.metadata.create_all)

                # Helper to safely convert values
                def safe_int(val):
                    if val is None or val == '':
                        return None
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                def safe_float(val):
                    if val is None or val == '':
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                for place in results:
                    # Extract multilingual descriptions
                    language_descriptions = {}
                    for lang_code in ['en', 'nl', 'fr', 'de', 'es', 'it']:
                        desc = place.get(f'description_{lang_code}')
                        if desc and desc.strip():
                            language_descriptions[lang_code] = desc.strip()

                    # Fallback description (priority: en > fr > nl > de > es > it)
                    fallback_description = (
                        language_descriptions.get('en') or
                        language_descriptions.get('fr') or
                        language_descriptions.get('nl') or
                        language_descriptions.get('de') or
                        language_descriptions.get('es') or
                        language_descriptions.get('it') or
                        place.get('description')
                    )

                    place_data = {
                        'id': safe_int(place.get('id')),
                        'nom': place.get('nom'),
                        'type': place.get('type'),
                        'latitude': safe_float(place.get('latitude')),
                        'longitude': safe_float(place.get('longitude')),
                        'pays': place.get('pays'),
                        'ville': place.get('ville'),
                        'description': fallback_description,
                        'prix': place.get('prix'),
                        'rating': safe_float(place.get('rating')),
                        'nb_comment': place.get('nbComment') or place.get('nb_comment'),
                        'services': place.get('services'),
                        'raw_data': place,
                        'updated_at': datetime.utcnow(),
                    }

                    stmt = pg_insert(places_table).values(**place_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            'nom': stmt.excluded.nom,
                            'type': stmt.excluded.type,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'pays': stmt.excluded.pays,
                            'ville': stmt.excluded.ville,
                            'description': stmt.excluded.description,
                            'prix': stmt.excluded.prix,
                            'rating': stmt.excluded.rating,
                            'nb_comment': stmt.excluded.nb_comment,
                            'services': stmt.excluded.services,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)

                    # Insert multilingual descriptions
                    place_id = safe_int(place.get('id'))
                    if place_id and language_descriptions:
                        # Delete existing descriptions for this place (to handle updates)
                        from sqlalchemy import delete
                        await conn.execute(
                            delete(place_descriptions_table).where(
                                place_descriptions_table.c.place_id == place_id
                            )
                        )

                        # Insert all language descriptions
                        for lang_code, description in language_descriptions.items():
                            desc_data = {
                                'place_id': place_id,
                                'language_code': lang_code,
                                'description': description,
                            }
                            await conn.execute(
                                place_descriptions_table.insert().values(**desc_data)
                            )

                    # Insert reviews if present
                    reviews = place.get('reviews', [])
                    if reviews:
                        for review in reviews:
                            review_data = {
                                'place_id': safe_int(place.get('id')),
                                'review_id': review.get('id'),
                                'user_id': review.get('user_id'),
                                'username': review.get('username') or review.get('uuid'),
                                'note': review.get('note'),
                                'comment': review.get('comment') or review.get('commentaire'),
                                'date': review.get('date'),
                                'raw_data': review,
                            }

                            stmt = pg_insert(reviews_table).values(**review_data)
                            stmt = stmt.on_conflict_do_nothing()
                            await conn.execute(stmt)

                await conn.commit()

            self.log(f"✓ Successfully stored {len(results)} places in database schema '{self.schema_name}'")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch places from multiple GPS coordinate pairs

        Expected params:
            - locations: List of dicts with 'latitude' and 'longitude' keys
                Example: [
                    {"latitude": 42.3383, "longitude": 9.5367},
                    {"latitude": 43.5, "longitude": 10.0}
                ]
            - include_reviews: Whether to fetch reviews (default: False)
            - delay_seconds: Delay between location requests (default: 1.0)

        Returns:
            List of all unique places from all locations
        """
        locations = params.get("locations", [])
        include_reviews = params.get("include_reviews", False)
        delay_seconds = params.get("delay_seconds", 1.0)

        if not locations:
            raise ValueError("'locations' parameter is required and must be a non-empty list")

        self.log(f"Fetching places from {len(locations)} locations")

        all_places = []
        seen_ids = set()

        for i, location in enumerate(locations):
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            if latitude is None or longitude is None:
                self.log(f"Skipping location {i+1}: missing coordinates", level="warning")
                continue

            self.log(f"Processing location {i+1}/{len(locations)}: {latitude}, {longitude}")

            try:
                # Fetch places for this location
                places = await self._get_places_by_location(latitude, longitude)

                # Deduplicate by ID
                new_places = []
                for place in places:
                    place_id = place.get("id")
                    if place_id and place_id not in seen_ids:
                        seen_ids.add(place_id)
                        new_places.append(place)

                self.log(f"Found {len(new_places)} new unique places from this location")
                all_places.extend(new_places)

                # Rate limiting
                if i < len(locations) - 1:
                    await asyncio.sleep(delay_seconds)

            except Exception as e:
                self.log(f"Error processing location {i+1}: {str(e)}", level="warning")
                continue

        self.log(f"Total unique places collected: {len(all_places)}")

        # Optionally fetch reviews
        if include_reviews and all_places:
            self.log("Fetching reviews for all places...")
            all_places = await self._enrich_with_reviews(all_places)

        return all_places

    async def _get_places_by_location(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """Fetch places by GPS coordinates"""
        url = f"{self.BASE_URL}/lieuxGetFilter.php"

        try:
            response = await self.http_client.get(
                url,
                params={
                    "latitude": latitude,
                    "longitude": longitude
                }
            )
            response.raise_for_status()

            data = response.json()

            # API returns dict with "lieux" key containing the list
            if isinstance(data, dict) and "lieux" in data:
                return data["lieux"]
            elif isinstance(data, list):
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching places: {str(e)}", level="error")
            raise

    async def _get_reviews(self, lieu_id: int) -> List[Dict[str, Any]]:
        """Fetch reviews for a specific location"""
        url = f"{self.BASE_URL}/commGet.php"

        try:
            response = await self.http_client.get(
                url,
                params={"lieu_id": lieu_id}
            )
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else []

        except Exception as e:
            self.log(f"Error fetching reviews for place {lieu_id}: {str(e)}", level="warning")
            return []

    async def _enrich_with_reviews(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich places with their reviews"""
        for i, place in enumerate(places):
            lieu_id = place.get("id")

            if lieu_id:
                if i % 10 == 0:  # Log progress every 10 places
                    self.log(f"Fetching reviews: {i+1}/{len(places)}")

                reviews = await self._get_reviews(lieu_id)
                place["reviews"] = reviews
                place["review_count"] = len(reviews)

                # Rate limiting
                await asyncio.sleep(0.3)
            else:
                place["reviews"] = []
                place["review_count"] = 0

        return places


class Park4NightGridScraper(BaseScraper):
    """
    Grid-based scraper for comprehensive Park4Night database coverage

    Generates a geographic grid over specified regions and systematically
    queries each grid point to collect all places. Handles the 200-place
    API limit by using dense enough grid spacing.
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://guest.park4night.com/services/V4.1"

    # Predefined regions for easy scraping
    REGIONS = {
        "europe": {"lat_min": 36.0, "lat_max": 71.0, "lon_min": -10.0, "lon_max": 40.0},
        "france": {"lat_min": 41.0, "lat_max": 51.5, "lon_min": -5.5, "lon_max": 10.0},
        "spain": {"lat_min": 36.0, "lat_max": 43.8, "lon_min": -9.5, "lon_max": 4.5},
        "italy": {"lat_min": 36.5, "lat_max": 47.0, "lon_min": 6.5, "lon_max": 18.5},
        "germany": {"lat_min": 47.0, "lat_max": 55.0, "lon_min": 5.5, "lon_max": 15.5},
        "uk": {"lat_min": 49.5, "lat_max": 61.0, "lon_min": -8.5, "lon_max": 2.0},
        "scandinavia": {"lat_min": 55.0, "lat_max": 71.0, "lon_min": 4.0, "lon_max": 31.0},
        "north_america": {"lat_min": 25.0, "lat_max": 72.0, "lon_min": -170.0, "lon_max": -52.0},
        "usa": {"lat_min": 25.0, "lat_max": 50.0, "lon_min": -125.0, "lon_max": -66.0},
        "canada": {"lat_min": 42.0, "lat_max": 72.0, "lon_min": -141.0, "lon_max": -52.0},
        "world": {"lat_min": -60.0, "lat_max": 75.0, "lon_min": -180.0, "lon_max": 180.0},
    }

    def define_tables(self) -> List[Table]:
        """Define database tables"""
        places_table = Table(
            'places',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('nom', String(500)),
            Column('type', String(100)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('pays', String(100)),
            Column('ville', String(200)),
            Column('description', Text),
            Column('prix', String(100)),
            Column('rating', Float),
            Column('nb_comment', Integer),
            Column('services', JSON),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True,
        )

        reviews_table = Table(
            'reviews',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer),  # Removed index=True to avoid duplicate index creation
            Column('review_id', Integer),
            Column('user_id', Integer),
            Column('username', String(200)),
            Column('note', Float),
            Column('comment', Text),
            Column('date', String(50)),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            extend_existing=True,
        )

        # Multilingual descriptions table
        place_descriptions_table = Table(
            'place_descriptions',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('place_id', Integer),  # Foreign key to places.id
            Column('language_code', String(5)),  # ISO 639-1: en, nl, fr, de, es, it
            Column('description', Text),
            Column('created_at', DateTime, default=func.now()),
            extend_existing=True,
        )

        # Progress tracking table
        grid_progress_table = Table(
            'grid_progress',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('region', String(100)),
            Column('grid_lat', Float),
            Column('grid_lon', Float),
            Column('places_found', Integer),
            Column('processed_at', DateTime, default=func.now()),
            extend_existing=True,
        )

        return [places_table, reviews_table, place_descriptions_table, grid_progress_table]

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store grid scraped data in database"""
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} places in database...")

        try:
            from app.core.database import engine

            async with engine.begin() as conn:
                tables = self.define_tables()
                places_table = tables[0]
                reviews_table = tables[1]
                place_descriptions_table = tables[2]
                grid_progress_table = tables[3]

                await conn.run_sync(self.metadata.create_all)

                # Helper functions for type conversion
                def safe_int(val):
                    if val is None or val == '':
                        return None
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                def safe_float(val):
                    if val is None or val == '':
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                for place in results:
                    # Extract multilingual descriptions
                    language_descriptions = {}
                    for lang_code in ['en', 'nl', 'fr', 'de', 'es', 'it']:
                        desc = place.get(f'description_{lang_code}')
                        if desc and desc.strip():
                            language_descriptions[lang_code] = desc.strip()

                    # Fallback description (priority: en > fr > nl > de > es > it)
                    fallback_description = (
                        language_descriptions.get('en') or
                        language_descriptions.get('fr') or
                        language_descriptions.get('nl') or
                        language_descriptions.get('de') or
                        language_descriptions.get('es') or
                        language_descriptions.get('it') or
                        place.get('description')
                    )

                    place_data = {
                        'id': safe_int(place.get('id')),
                        'nom': place.get('titre') or place.get('nom'),
                        'type': place.get('type'),
                        'latitude': safe_float(place.get('latitude')),
                        'longitude': safe_float(place.get('longitude')),
                        'pays': place.get('pays'),
                        'ville': place.get('ville'),
                        'description': fallback_description,
                        'prix': place.get('prix_stationnement') or place.get('prix'),
                        'rating': safe_float(place.get('note_moyenne') or place.get('rating')),
                        'nb_comment': safe_int(place.get('nb_commentaires') or place.get('nbComment') or place.get('nb_comment')),
                        'services': place.get('services'),
                        'raw_data': place,
                        'updated_at': datetime.utcnow(),
                    }

                    stmt = pg_insert(places_table).values(**place_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            'nom': stmt.excluded.nom,
                            'type': stmt.excluded.type,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'pays': stmt.excluded.pays,
                            'ville': stmt.excluded.ville,
                            'description': stmt.excluded.description,
                            'prix': stmt.excluded.prix,
                            'rating': stmt.excluded.rating,
                            'nb_comment': stmt.excluded.nb_comment,
                            'services': stmt.excluded.services,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)

                    # Insert multilingual descriptions
                    place_id = safe_int(place.get('id'))
                    if place_id and language_descriptions:
                        # Delete existing descriptions for this place (to handle updates)
                        from sqlalchemy import delete
                        await conn.execute(
                            delete(place_descriptions_table).where(
                                place_descriptions_table.c.place_id == place_id
                            )
                        )

                        # Insert all language descriptions
                        for lang_code, description in language_descriptions.items():
                            desc_data = {
                                'place_id': place_id,
                                'language_code': lang_code,
                                'description': description,
                            }
                            await conn.execute(
                                place_descriptions_table.insert().values(**desc_data)
                            )

                    # Insert reviews if present
                    reviews = place.get('reviews', [])
                    if reviews:
                        for review in reviews:
                            review_data = {
                                'place_id': safe_int(place.get('id')),
                                'review_id': review.get('id'),
                                'user_id': review.get('user_id'),
                                'username': review.get('username') or review.get('uuid'),
                                'note': review.get('note'),
                                'comment': review.get('comment') or review.get('commentaire'),
                                'date': review.get('date'),
                                'raw_data': review,
                            }

                            stmt = pg_insert(reviews_table).values(**review_data)
                            stmt = stmt.on_conflict_do_nothing()
                            await conn.execute(stmt)

                # Save grid progress if available
                if results and '_grid_progress' in results[0]:
                    grid_progress_data = results[0]['_grid_progress']
                    for progress_entry in grid_progress_data:
                        progress_data = {
                            'region': progress_entry['region'],
                            'grid_lat': progress_entry['grid_lat'],
                            'grid_lon': progress_entry['grid_lon'],
                            'places_found': progress_entry['places_found'],
                            'processed_at': datetime.utcnow(),
                        }
                        stmt = insert(grid_progress_table).values(**progress_data)
                        await conn.execute(stmt)

                await conn.commit()

            self.log(f"✓ Successfully stored {len(results)} places in database schema '{self.schema_name}'")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")

    def _generate_grid(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        grid_spacing: float
    ) -> List[tuple]:
        """
        Generate grid of coordinates covering a geographic region

        Args:
            lat_min: Minimum latitude
            lat_max: Maximum latitude
            lon_min: Minimum longitude
            lon_max: Maximum longitude
            grid_spacing: Distance between grid points in degrees

        Returns:
            List of (latitude, longitude) tuples
        """
        grid_points = []

        current_lat = lat_min
        while current_lat <= lat_max:
            current_lon = lon_min
            while current_lon <= lon_max:
                grid_points.append((round(current_lat, 4), round(current_lon, 4)))
                current_lon += grid_spacing
            current_lat += grid_spacing

        return grid_points

    async def _save_grid_progress(
        self,
        conn,
        region: str,
        lat: float,
        lon: float,
        places_found: int
    ) -> None:
        """Save progress for a grid point"""
        tables = self.define_tables()
        grid_progress_table = tables[2]

        progress_data = {
            'region': region,
            'grid_lat': lat,
            'grid_lon': lon,
            'places_found': places_found,
            'processed_at': datetime.utcnow(),
        }

        stmt = insert(grid_progress_table).values(**progress_data)
        await conn.execute(stmt)

    async def _get_processed_grid_points(self, conn, region: str) -> set:
        """Get already processed grid points for resumability"""
        from sqlalchemy import select

        tables = self.define_tables()
        grid_progress_table = tables[2]

        result = await conn.execute(
            select(grid_progress_table.c.grid_lat, grid_progress_table.c.grid_lon).where(
                grid_progress_table.c.region == region
            )
        )

        return {(row.grid_lat, row.grid_lon) for row in result}

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Systematically scrape a geographic region using a coordinate grid

        Expected params:
            - region: Named region from REGIONS dict (e.g., 'europe', 'france', 'world')
              OR custom region with:
              - lat_min, lat_max, lon_min, lon_max: Custom bounding box
            - grid_spacing: Distance between grid points in degrees (default: 0.5)
                           Smaller = denser grid = more comprehensive but slower
                           Recommended: 0.3-0.5 for dense areas, 1.0 for sparse
            - include_reviews: Fetch reviews for each place (default: False)
            - max_grid_points: Limit number of grid points (for testing, default: None)
            - resume: Continue from previously saved progress (default: True)
            - min_delay: Minimum delay between requests in seconds (default: 1.0)
            - max_delay: Maximum delay between requests in seconds (default: 5.0)

        Returns:
            List of all unique places found across the grid
        """
        # Determine region boundaries
        region_name = params.get("region")

        if region_name and region_name in self.REGIONS:
            bounds = self.REGIONS[region_name]
            lat_min = bounds["lat_min"]
            lat_max = bounds["lat_max"]
            lon_min = bounds["lon_min"]
            lon_max = bounds["lon_max"]
            self.log(f"Using predefined region: {region_name}")
        else:
            # Custom region
            lat_min = params.get("lat_min")
            lat_max = params.get("lat_max")
            lon_min = params.get("lon_min")
            lon_max = params.get("lon_max")
            region_name = params.get("region", "custom")

            if None in [lat_min, lat_max, lon_min, lon_max]:
                raise ValueError(
                    "Either provide 'region' from predefined regions or "
                    "all of: lat_min, lat_max, lon_min, lon_max"
                )

            self.log(f"Using custom region: {region_name}")

        grid_spacing = params.get("grid_spacing", 0.5)
        include_reviews = params.get("include_reviews", False)
        max_grid_points = params.get("max_grid_points")
        resume = params.get("resume", True)
        min_delay = params.get("min_delay", 1.0)
        max_delay = params.get("max_delay", 5.0)

        self.log(f"Region bounds: lat=[{lat_min}, {lat_max}], lon=[{lon_min}, {lon_max}]")
        self.log(f"Grid spacing: {grid_spacing} degrees")

        # Generate grid
        grid_points = self._generate_grid(lat_min, lat_max, lon_min, lon_max, grid_spacing)
        self.log(f"Generated grid with {len(grid_points)} points")

        # Get already processed points if resuming
        processed_points = set()
        if resume:
            try:
                from app.core.database import engine
                async with engine.begin() as conn:
                    # Try to get existing progress (table may not exist yet)
                    processed_points = await self._get_processed_grid_points(conn, region_name)
                    if processed_points:
                        self.log(f"Resuming: {len(processed_points)} grid points already processed")
            except Exception as e:
                self.log(f"Could not load progress (starting fresh): {str(e)}", level="warning")

        # Filter out already processed points
        grid_points = [p for p in grid_points if p not in processed_points]

        if max_grid_points:
            grid_points = grid_points[:max_grid_points]
            self.log(f"Limited to {max_grid_points} grid points for this run")

        self.log(f"Will process {len(grid_points)} grid points")

        # Report initial progress
        await self.report_progress(
            items_scraped=0,
            message=f"Starting grid scrape: {len(grid_points)} points to process"
        )

        # Process grid systematically
        all_places = []
        seen_ids = set()
        grid_progress = []  # Track progress in memory

        for i, (lat, lon) in enumerate(grid_points):
            self.log(f"Grid point {i+1}/{len(grid_points)}: ({lat}, {lon})")

            try:
                # Fetch places for this grid point
                places = await self._get_places_by_location(lat, lon)

                # Deduplicate
                new_places = []
                for place in places:
                    place_id = place.get("id")
                    if place_id and place_id not in seen_ids:
                        seen_ids.add(place_id)
                        new_places.append(place)

                self.log(f"  Found {len(places)} places ({len(new_places)} new)")
                all_places.extend(new_places)

                # Track progress in memory
                grid_progress.append({
                    'region': region_name,
                    'grid_lat': lat,
                    'grid_lon': lon,
                    'places_found': len(places),
                })

                # Rate limiting with random delay to avoid overwhelming the server
                if i < len(grid_points) - 1:
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)

                # Log progress summary every 50 points
                if (i + 1) % 50 == 0:
                    self.log(f"Progress: {i+1}/{len(grid_points)} points, {len(all_places)} unique places so far")

                # Report progress to WebSocket every 10 grid points
                if (i + 1) % 10 == 0:
                    await self.report_progress(
                        items_scraped=len(all_places),
                        message=f"Processed {i+1}/{len(grid_points)} grid points ({lat:.2f}, {lon:.2f})"
                    )

            except Exception as e:
                self.log(f"  Error processing grid point ({lat}, {lon}): {str(e)}", level="warning")
                continue

        self.log(f"✓ Grid scraping complete: {len(all_places)} unique places from {len(grid_points)} grid points")

        # Store grid progress for later saving
        for place in all_places:
            place['_grid_progress'] = grid_progress

        # Optionally fetch reviews
        if include_reviews and all_places:
            self.log("Fetching reviews for all places (this may take a while)...")
            all_places = await self._enrich_with_reviews(all_places)

        return all_places

    async def _get_places_by_location(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """Fetch places by GPS coordinates"""
        url = f"{self.BASE_URL}/lieuxGetFilter.php"

        try:
            response = await self.http_client.get(
                url,
                params={
                    "latitude": latitude,
                    "longitude": longitude
                }
            )
            response.raise_for_status()

            data = response.json()

            # API returns dict with "lieux" key containing the list
            if isinstance(data, dict) and "lieux" in data:
                return data["lieux"]
            elif isinstance(data, list):
                return data
            else:
                return []

        except Exception as e:
            self.log(f"Error fetching places: {str(e)}", level="error")
            raise

    async def _get_reviews(self, lieu_id: int) -> List[Dict[str, Any]]:
        """Fetch reviews for a specific location"""
        url = f"{self.BASE_URL}/commGet.php"

        try:
            response = await self.http_client.get(
                url,
                params={"lieu_id": lieu_id}
            )
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else []

        except Exception as e:
            self.log(f"Error fetching reviews for place {lieu_id}: {str(e)}", level="warning")
            return []

    async def _enrich_with_reviews(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich places with their reviews"""
        for i, place in enumerate(places):
            lieu_id = place.get("id")

            if lieu_id:
                if i % 50 == 0:  # Log progress every 50 places
                    self.log(f"Fetching reviews: {i+1}/{len(places)}")

                reviews = await self._get_reviews(lieu_id)
                place["reviews"] = reviews
                place["review_count"] = len(reviews)

                # Rate limiting with random delay to avoid overwhelming the server
                delay = random.uniform(1.0, 3.0)
                await asyncio.sleep(delay)
            else:
                place["reviews"] = []
                place["review_count"] = 0

        return places
