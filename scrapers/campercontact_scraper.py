"""
CamperContact API Scraper

This scraper interacts with the campercontact.com public map API to fetch camping spots
and motorhome parking locations across Europe.

API Endpoint: https://services.campercontact.com/search/results/map
Detail Pages: https://www.campercontact.com/en/{country}/{region}/{city}/{sitecode}/{slug}

The detail pages are server-side rendered Next.js pages with all data embedded
in the __NEXT_DATA__ script tag as JSON.
"""
import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List, Optional
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Boolean, JSON, Text, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import random
import re
import json
from datetime import datetime


class CamperContactGridScraper(BaseScraper):
    """
    Grid-based scraper for comprehensive CamperContact database coverage

    Generates a geographic grid over specified regions and systematically
    queries each grid area to collect all camperplaces.
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://services.campercontact.com"

    # Predefined regions for easy scraping
    REGIONS = {
        "europe": {"lat_min": 36.0, "lat_max": 71.0, "lon_min": -10.0, "lon_max": 40.0},
        "uk": {"lat_min": 49.5, "lat_max": 61.0, "lon_min": -8.5, "lon_max": 2.0},
        "france": {"lat_min": 41.0, "lat_max": 51.5, "lon_min": -5.5, "lon_max": 10.0},
        "spain": {"lat_min": 36.0, "lat_max": 43.8, "lon_min": -9.5, "lon_max": 4.5},
        "portugal": {"lat_min": 36.8, "lat_max": 42.2, "lon_min": -9.5, "lon_max": -6.2},
        "italy": {"lat_min": 36.5, "lat_max": 47.0, "lon_min": 6.5, "lon_max": 18.5},
        "germany": {"lat_min": 47.0, "lat_max": 55.0, "lon_min": 5.5, "lon_max": 15.5},
        "netherlands": {"lat_min": 50.7, "lat_max": 53.6, "lon_min": 3.2, "lon_max": 7.3},
        "belgium": {"lat_min": 49.5, "lat_max": 51.5, "lon_min": 2.5, "lon_max": 6.5},
        "scandinavia": {"lat_min": 55.0, "lat_max": 71.2, "lon_min": 4.5, "lon_max": 31.6},
        "austria": {"lat_min": 46.4, "lat_max": 49.0, "lon_min": 9.5, "lon_max": 17.2},
        "switzerland": {"lat_min": 45.8, "lat_max": 47.8, "lon_min": 5.9, "lon_max": 10.5},
        "greece": {"lat_min": 34.8, "lat_max": 41.8, "lon_min": 19.3, "lon_max": 28.3},
        "norway": {"lat_min": 58.0, "lat_max": 71.2, "lon_min": 4.5, "lon_max": 31.0},
        "sweden": {"lat_min": 55.3, "lat_max": 69.1, "lon_min": 11.0, "lon_max": 24.2},
        "denmark": {"lat_min": 54.5, "lat_max": 57.8, "lon_min": 8.0, "lon_max": 15.2},
        "poland": {"lat_min": 49.0, "lat_max": 54.9, "lon_min": 14.1, "lon_max": 24.2},
        "croatia": {"lat_min": 42.4, "lat_max": 46.5, "lon_min": 13.5, "lon_max": 19.4},
        "ireland": {"lat_min": 51.4, "lat_max": 55.4, "lon_min": -10.5, "lon_max": -5.5},
        "czech_republic": {"lat_min": 48.5, "lat_max": 51.1, "lon_min": 12.1, "lon_max": 18.9},
        "hungary": {"lat_min": 45.7, "lat_max": 48.6, "lon_min": 16.1, "lon_max": 22.9},
        "romania": {"lat_min": 43.6, "lat_max": 48.3, "lon_min": 20.3, "lon_max": 29.7},
        "bulgaria": {"lat_min": 41.2, "lat_max": 44.2, "lon_min": 22.4, "lon_max": 28.6},
        "slovakia": {"lat_min": 47.7, "lat_max": 49.6, "lon_min": 16.8, "lon_max": 22.6},
        "slovenia": {"lat_min": 45.4, "lat_max": 46.9, "lon_min": 13.4, "lon_max": 16.6},
        "estonia": {"lat_min": 57.5, "lat_max": 59.7, "lon_min": 21.8, "lon_max": 28.2},
        "latvia": {"lat_min": 55.7, "lat_max": 58.1, "lon_min": 21.0, "lon_max": 28.2},
        "lithuania": {"lat_min": 53.9, "lat_max": 56.5, "lon_min": 21.0, "lon_max": 26.8},
        "finland": {"lat_min": 60.0, "lat_max": 70.1, "lon_min": 20.0, "lon_max": 31.6},
        "iceland": {"lat_min": 63.4, "lat_max": 66.6, "lon_min": -24.5, "lon_max": -13.5},
        "serbia": {"lat_min": 42.2, "lat_max": 46.2, "lon_min": 18.8, "lon_max": 23.0},
    }

    def define_tables(self) -> List[Table]:
        """Define database tables for storing CamperContact data"""

        places_table = Table(
            'places',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('poi_id', String(50), unique=True),  # e.g., "poi-56495"
            Column('sitecode', Integer),  # Numeric site identifier
            Column('type', String(50)),  # e.g., "camperplace"
            Column('latitude', Float),
            Column('longitude', Float),
            Column('is_bookable', Boolean),
            Column('is_claimed', Boolean),
            Column('subscription_level', Integer),
            # Detail page fields (from __NEXT_DATA__)
            Column('name', String(500)),
            Column('description', Text),
            Column('rating', Float),
            Column('street', String(500)),
            Column('house_number', String(50)),
            Column('postal_code', String(20)),
            Column('city', String(200)),
            Column('province', String(200)),
            Column('country', String(100)),
            Column('phone', String(100)),
            Column('email', String(200)),
            Column('website', String(500)),
            Column('price_per_night', Float),
            Column('price_currency', String(10)),
            Column('capacity', Integer),
            Column('photos', JSON),  # List of photo URLs
            Column('amenities', JSON),  # List of amenity objects
            Column('usps', JSON),  # Unique selling points / features
            Column('opening_hours', JSON),
            Column('detail_raw_data', JSON),  # Full detail page data
            Column('detail_scraped_at', DateTime),  # When detail was scraped
            Column('raw_data', JSON),  # Store complete API response
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

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
            schema=self.schema_name
        )

        # Track detail scraping progress
        detail_progress_table = Table(
            'detail_progress',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('sitecode', Integer, unique=True),
            Column('status', String(50)),  # 'success', 'failed', 'not_found'
            Column('error_message', Text),
            Column('processed_at', DateTime, default=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        return [places_table, grid_progress_table, detail_progress_table]

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store scraped data in database"""
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} places in database...")

        try:
            from app.core.database import engine
            from sqlalchemy import text

            async with engine.begin() as conn:
                # Ensure schema exists
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))

                tables = self.define_tables()
                places_table = tables[0]

                await conn.run_sync(self.metadata.create_all)

                for place in results:
                    place_data = {
                        'poi_id': place.get('id'),
                        'sitecode': place.get('sitecode'),
                        'type': place.get('type'),
                        'latitude': place.get('location', {}).get('lat'),
                        'longitude': place.get('location', {}).get('lon'),
                        'is_bookable': place.get('isBookable', False),
                        'is_claimed': place.get('isClaimed', False),
                        'subscription_level': place.get('subscriptionLevel', 0),
                        'raw_data': place,
                        'updated_at': datetime.utcnow(),
                    }

                    # Upsert: insert or update if poi_id already exists
                    stmt = pg_insert(places_table).values(**place_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['poi_id'],
                        set_={
                            'sitecode': stmt.excluded.sitecode,
                            'type': stmt.excluded.type,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'is_bookable': stmt.excluded.is_bookable,
                            'is_claimed': stmt.excluded.is_claimed,
                            'subscription_level': stmt.excluded.subscription_level,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)

                self.log(f"Successfully stored {len(results)} places")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")
            raise

    def _generate_grid(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        grid_spacing: float
    ) -> List[tuple]:
        """
        Generate grid of bounding boxes covering a geographic region

        For CamperContact, we generate boxes instead of points.
        Each box will be used for a bounding box query.
        """
        grid_boxes = []

        current_lat = lat_min
        while current_lat < lat_max:
            current_lon = lon_min
            while current_lon < lon_max:
                # Create a bounding box
                box_lat_min = round(current_lat, 4)
                box_lat_max = round(min(current_lat + grid_spacing, lat_max), 4)
                box_lon_min = round(current_lon, 4)
                box_lon_max = round(min(current_lon + grid_spacing, lon_max), 4)

                grid_boxes.append((box_lat_min, box_lat_max, box_lon_min, box_lon_max))

                current_lon += grid_spacing
            current_lat += grid_spacing

        return grid_boxes

    async def _save_grid_progress(
        self,
        conn,
        region: str,
        lat: float,
        lon: float,
        places_found: int
    ) -> None:
        """Save progress for a grid point"""
        from sqlalchemy import insert

        tables = self.define_tables()
        grid_progress_table = tables[1]

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
        grid_progress_table = tables[1]

        result = await conn.execute(
            select(grid_progress_table.c.grid_lat, grid_progress_table.c.grid_lon).where(
                grid_progress_table.c.region == region
            )
        )

        return {(row.grid_lat, row.grid_lon) for row in result}

    async def _fetch_detail_page(self, sitecode: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detail page data from CamperContact website.

        The website uses Next.js SSR, so all data is embedded in __NEXT_DATA__ JSON.
        CamperContact has a redirect system: /en/-/-/-/{sitecode}/x redirects to the
        correct full URL with country/region/city/slug.

        Args:
            sitecode: The CamperContact sitecode identifier

        Returns:
            Parsed POI data from the detail page, or None if not found
        """
        # CamperContact redirects /en/-/-/-/{sitecode}/x to the correct full URL
        # This is a reliable way to fetch any place by sitecode
        url = f"https://www.campercontact.com/en/-/-/-/{sitecode}/x"

        try:
            response = await self.http_client.get(
                url,
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
            )

            if response.status_code == 200:
                html = response.text

                # Check if we got an error page
                if 'statusCode":404' in html or 'statusCode":500' in html:
                    return None

                # Extract __NEXT_DATA__ JSON
                match = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    html
                )

                if match:
                    try:
                        data = json.loads(match.group(1))
                        poi_data = data.get('props', {}).get('pageProps', {}).get('poiV2')

                        if poi_data:
                            return poi_data
                    except json.JSONDecodeError as e:
                        self.log(f"JSON decode error for sitecode {sitecode}: {str(e)}", level="warning")
                        return None

            return None

        except Exception as e:
            self.log(f"Error fetching detail for sitecode {sitecode}: {str(e)}", level="warning")
            return None

    def _parse_detail_data(self, poi_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse POI detail data into structured fields.

        Args:
            poi_data: The poiV2 object from __NEXT_DATA__

        Returns:
            Dictionary with parsed fields ready for database storage
        """
        # Extract address
        address = poi_data.get('address', {})

        # Extract contact details
        contact = poi_data.get('contactDetails', {})

        # Extract photos
        photos_data = poi_data.get('photos', {})
        photos = []
        if isinstance(photos_data, dict):
            for photo in photos_data.get('items', []):
                if photo.get('url'):
                    photos.append({
                        'url': photo['url'],
                        'type': photo.get('type', 'photo'),
                        'display_type': photo.get('displayType')
                    })

        # Extract pricing
        prices = poi_data.get('prices', [])
        price_per_night = None
        price_currency = None
        if prices:
            first_price = prices[0]
            price_per_night = first_price.get('pricePerNight')
            price_currency = first_price.get('currency')

        # Extract capacity
        capacity_data = poi_data.get('capacity', {})
        capacity = capacity_data.get('numberOfSpaces') if isinstance(capacity_data, dict) else None

        # Extract location from detail data (more accurate than map API)
        location = poi_data.get('location', {})

        return {
            'name': poi_data.get('name'),
            'description': poi_data.get('description'),
            'rating': poi_data.get('rating'),
            'street': address.get('street'),
            'house_number': address.get('houseNumber'),
            'postal_code': address.get('postalCode'),
            'city': address.get('city'),
            'province': address.get('province'),
            'country': address.get('country'),
            'phone': contact.get('phoneNumber'),
            'email': contact.get('email'),
            'website': contact.get('website'),
            'price_per_night': price_per_night,
            'price_currency': price_currency,
            'capacity': capacity,
            'photos': photos,
            'amenities': poi_data.get('amenities', []),
            'usps': poi_data.get('usps', []),
            'opening_hours': poi_data.get('openingHours'),
            'latitude': location.get('latitude'),
            'longitude': location.get('longitude'),
            'detail_raw_data': poi_data,
            'detail_scraped_at': datetime.utcnow()
        }

    async def _get_processed_details(self, conn) -> set:
        """Get sitecodes that have already had details scraped."""
        from sqlalchemy import select

        tables = self.define_tables()
        detail_progress_table = tables[2]

        try:
            result = await conn.execute(
                select(detail_progress_table.c.sitecode)
            )
            return {row.sitecode for row in result}
        except Exception:
            return set()

    async def _save_detail_progress(
        self,
        conn,
        sitecode: int,
        status: str,
        error_message: str = None
    ) -> None:
        """Save detail scraping progress."""
        tables = self.define_tables()
        detail_progress_table = tables[2]

        progress_data = {
            'sitecode': sitecode,
            'status': status,
            'error_message': error_message,
            'processed_at': datetime.utcnow(),
        }

        stmt = pg_insert(detail_progress_table).values(**progress_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['sitecode'],
            set_={
                'status': stmt.excluded.status,
                'error_message': stmt.excluded.error_message,
                'processed_at': stmt.excluded.processed_at,
            }
        )
        await conn.execute(stmt)

    async def _get_markers_by_bbox(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        poi_type: str = "camperplace"
    ) -> List[Dict[str, Any]]:
        """
        Fetch markers within a bounding box

        Args:
            lat_min: Bottom latitude
            lat_max: Top latitude
            lon_min: Left longitude
            lon_max: Right longitude
            poi_type: Type of POI to fetch (camperplace, camping, microcamping)

        Returns:
            List of marker objects from the API
        """
        url = f"{self.BASE_URL}/search/results/map"

        try:
            response = await self.http_client.get(
                url,
                params={
                    "topleft_lat": lat_max,  # Top of box
                    "topleft_lon": lon_min,  # Left of box
                    "bottomright_lat": lat_min,  # Bottom of box
                    "bottomright_lon": lon_max,  # Right of box
                    "poiType": poi_type
                }
            )
            response.raise_for_status()

            data = response.json()

            # Extract markers from response
            markers = data.get("markers", [])
            clusters = data.get("clusters", [])

            if clusters:
                self.log(f"Warning: Found {len(clusters)} clusters in response. Grid may be too large.", level="warning")

            return markers

        except Exception as e:
            self.log(f"Error fetching markers: {str(e)}", level="error")
            raise

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Systematically scrape a geographic region using a coordinate grid

        Expected params:
            - region: Named region from REGIONS dict (e.g., 'europe', 'france')
              OR custom region with:
              - lat_min, lat_max, lon_min, lon_max: Custom bounding box
            - poi_type: Type of POI to scrape (default: 'camperplace')
                       Options: 'camperplace', 'camping', 'microcamping'
            - grid_spacing: Distance between grid points in degrees (default: 0.5)
                           Smaller = denser grid = more comprehensive but slower
                           Recommended: 0.3-0.5 for dense areas, 1.0 for sparse
            - max_grid_boxes: Limit number of grid boxes (for testing, default: None)
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
            lat_min = params.get("lat_min")
            lat_max = params.get("lat_max")
            lon_min = params.get("lon_min")
            lon_max = params.get("lon_max")

            if not all([lat_min, lat_max, lon_min, lon_max]):
                raise ValueError(
                    "Either 'region' or all of (lat_min, lat_max, lon_min, lon_max) must be provided"
                )

            region_name = f"custom_{lat_min}_{lat_max}_{lon_min}_{lon_max}"
            self.log(f"Using custom region: {lat_min}-{lat_max}, {lon_min}-{lon_max}")

        # Get grid parameters
        grid_spacing = params.get("grid_spacing", 0.5)
        poi_type = params.get("poi_type", "camperplace")
        max_grid_boxes = params.get("max_grid_boxes")
        resume = params.get("resume", True)
        min_delay = params.get("min_delay", 1.0)
        max_delay = params.get("max_delay", 5.0)

        # Validate poi_type
        valid_poi_types = ["camperplace", "camping", "microcamping"]
        if poi_type not in valid_poi_types:
            raise ValueError(f"Invalid poi_type '{poi_type}'. Must be one of: {', '.join(valid_poi_types)}")

        self.log(f"POI type: {poi_type}")

        # Generate grid
        grid_boxes = self._generate_grid(lat_min, lat_max, lon_min, lon_max, grid_spacing)
        self.log(f"Generated {len(grid_boxes)} grid boxes (spacing: {grid_spacing}°)")

        # Resume logic: skip already processed grid boxes
        if resume:
            try:
                from app.core.database import engine
                async with engine.begin() as conn:
                    processed_points = await self._get_processed_grid_points(conn, region_name)
                    if processed_points:
                        original_count = len(grid_boxes)
                        # Filter out processed boxes (using center point for matching)
                        grid_boxes = [
                            box for box in grid_boxes
                            if ((box[0] + box[1]) / 2, (box[2] + box[3]) / 2) not in processed_points
                        ]
                        skipped = original_count - len(grid_boxes)
                        self.log(f"Resume: Skipping {skipped} already processed boxes, {len(grid_boxes)} remaining")
            except Exception as e:
                self.log(f"Could not load resume progress: {str(e)}", level="warning")

        # Limit for testing
        if max_grid_boxes:
            grid_boxes = grid_boxes[:max_grid_boxes]
            self.log(f"Limited to {max_grid_boxes} grid boxes for testing")

        # Scrape each grid box
        all_markers = []
        seen_poi_ids = set()
        total_boxes = len(grid_boxes)

        for idx, (box_lat_min, box_lat_max, box_lon_min, box_lon_max) in enumerate(grid_boxes):
            box_center_lat = (box_lat_min + box_lat_max) / 2
            box_center_lon = (box_lon_min + box_lon_max) / 2

            self.log(f"Processing grid box {idx + 1}/{total_boxes}: "
                    f"lat={box_lat_min:.2f}-{box_lat_max:.2f}, "
                    f"lon={box_lon_min:.2f}-{box_lon_max:.2f}")

            try:
                # Fetch markers for this box
                markers = await self._get_markers_by_bbox(
                    box_lat_min, box_lat_max, box_lon_min, box_lon_max, poi_type
                )

                # Deduplicate by POI ID
                new_markers = []
                for marker in markers:
                    poi_id = marker.get("id")
                    if poi_id and poi_id not in seen_poi_ids:
                        seen_poi_ids.add(poi_id)
                        new_markers.append(marker)

                all_markers.extend(new_markers)

                self.log(f"Box {idx + 1}/{total_boxes}: Found {len(markers)} markers "
                        f"({len(new_markers)} new, {len(seen_poi_ids)} total unique)")

                # Save progress
                try:
                    from app.core.database import engine
                    async with engine.begin() as conn:
                        await conn.run_sync(self.metadata.create_all)
                        await self._save_grid_progress(
                            conn, region_name, box_center_lat, box_center_lon, len(new_markers)
                        )
                except Exception as e:
                    self.log(f"Could not save progress: {str(e)}", level="warning")

                # Rate limiting
                if idx < total_boxes - 1:
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)

            except Exception as e:
                self.log(f"Error processing box {idx + 1}: {str(e)}", level="error")
                continue

        self.log(f"Grid scraping complete! Total unique places found: {len(all_markers)}")
        return all_markers


class CamperContactDetailScraper(CamperContactGridScraper):
    """
    Detail page scraper for CamperContact places.

    This scraper fetches detail pages for places already collected by the grid scraper.
    It enriches existing database records with detailed information including:
    - Name, description, rating
    - Full address (street, city, postal code, province, country)
    - Contact info (phone, email, website)
    - Pricing information
    - Photos
    - Amenities and features

    IMPORTANT: This scraper uses the same schema (scraper_5) as the grid scraper
    since it updates the same places table.
    """

    scraper_type = ScraperType.WEB

    # Override schema_name to use the same schema as the grid scraper
    # This allows the detail scraper to update records created by the grid scraper
    SHARED_SCHEMA = "scraper_5"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force using scraper_5 schema regardless of scraper ID
        self._schema_name = self.SHARED_SCHEMA

    @property
    def schema_name(self):
        return self._schema_name

    @schema_name.setter
    def schema_name(self, value):
        # Always use SHARED_SCHEMA
        self._schema_name = self.SHARED_SCHEMA

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store detailed data by updating existing place records."""
        if not results:
            self.log("No detail results to store")
            return

        self.log(f"Updating {len(results)} places with detail data...")

        try:
            from app.core.database import engine
            from sqlalchemy import text

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))

                tables = self.define_tables()
                places_table = tables[0]

                await conn.run_sync(self.metadata.create_all)

                updated_count = 0
                for place in results:
                    if not place.get('sitecode'):
                        continue

                    # Update existing record with detail data
                    update_data = {
                        'name': place.get('name'),
                        'description': place.get('description'),
                        'rating': place.get('rating'),
                        'street': place.get('street'),
                        'house_number': place.get('house_number'),
                        'postal_code': place.get('postal_code'),
                        'city': place.get('city'),
                        'province': place.get('province'),
                        'country': place.get('country'),
                        'phone': place.get('phone'),
                        'email': place.get('email'),
                        'website': place.get('website'),
                        'price_per_night': place.get('price_per_night'),
                        'price_currency': place.get('price_currency'),
                        'capacity': place.get('capacity'),
                        'photos': place.get('photos'),
                        'amenities': place.get('amenities'),
                        'usps': place.get('usps'),
                        'opening_hours': place.get('opening_hours'),
                        'detail_raw_data': place.get('detail_raw_data'),
                        'detail_scraped_at': place.get('detail_scraped_at'),
                        'updated_at': datetime.utcnow(),
                    }

                    # Update latitude/longitude if we got more accurate values
                    if place.get('latitude'):
                        update_data['latitude'] = place['latitude']
                    if place.get('longitude'):
                        update_data['longitude'] = place['longitude']

                    # Remove None values to avoid overwriting good data with NULL
                    update_data = {k: v for k, v in update_data.items() if v is not None}

                    from sqlalchemy import update
                    stmt = update(places_table).where(
                        places_table.c.sitecode == place['sitecode']
                    ).values(**update_data)
                    result = await conn.execute(stmt)

                    if result.rowcount > 0:
                        updated_count += 1

                self.log(f"Successfully updated {updated_count} places with detail data")

        except Exception as e:
            self.log(f"Error storing detail data: {str(e)}", level="error")
            raise

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape detail pages for places that don't have detail data yet.

        Expected params:
            - max_places: Maximum number of places to scrape details for (default: 1000)
            - min_delay: Minimum delay between requests (default: 2.0)
            - max_delay: Maximum delay between requests (default: 5.0)
            - resume: Skip already processed sitecodes (default: True)
            - sitecodes: Optional list of specific sitecodes to scrape

        Returns:
            List of place data with detail information
        """
        max_places = params.get("max_places", 1000)
        min_delay = params.get("min_delay", 2.0)
        max_delay = params.get("max_delay", 5.0)
        resume = params.get("resume", True)
        specific_sitecodes = params.get("sitecodes", [])

        self.log(f"Starting detail scraping (max {max_places} places)")

        # Get sitecodes to process
        sitecodes_to_process = []

        try:
            from app.core.database import engine
            from sqlalchemy import select, text

            async with engine.begin() as conn:
                # Ensure tables exist
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
                tables = self.define_tables()
                await conn.run_sync(self.metadata.create_all)

                places_table = tables[0]

                if specific_sitecodes:
                    # Use provided sitecodes
                    sitecodes_to_process = specific_sitecodes
                    self.log(f"Using {len(sitecodes_to_process)} provided sitecodes")
                else:
                    # Get sitecodes that don't have detail data yet
                    result = await conn.execute(
                        select(places_table.c.sitecode).where(
                            places_table.c.detail_scraped_at.is_(None)
                        ).order_by(places_table.c.id).limit(max_places * 2)  # Get extra in case some fail
                    )
                    sitecodes_to_process = [row.sitecode for row in result if row.sitecode]
                    self.log(f"Found {len(sitecodes_to_process)} places without detail data")

                # Filter out already processed sitecodes if resuming
                if resume and sitecodes_to_process:
                    processed = await self._get_processed_details(conn)
                    original_count = len(sitecodes_to_process)
                    sitecodes_to_process = [
                        sc for sc in sitecodes_to_process
                        if sc not in processed
                    ]
                    skipped = original_count - len(sitecodes_to_process)
                    if skipped > 0:
                        self.log(f"Resume: Skipping {skipped} already processed sitecodes")

        except Exception as e:
            self.log(f"Error loading sitecodes: {str(e)}", level="error")
            raise

        if not sitecodes_to_process:
            self.log("No sitecodes to process")
            return []

        # Limit to max_places
        sitecodes_to_process = sitecodes_to_process[:max_places]
        self.log(f"Processing {len(sitecodes_to_process)} sitecodes")

        # Fetch detail pages
        all_details = []
        success_count = 0
        fail_count = 0

        for idx, sitecode in enumerate(sitecodes_to_process):
            self.log(f"Fetching detail {idx + 1}/{len(sitecodes_to_process)}: sitecode {sitecode}")

            try:
                poi_data = await self._fetch_detail_page(sitecode)

                if poi_data:
                    detail_data = self._parse_detail_data(poi_data)
                    detail_data['sitecode'] = sitecode
                    all_details.append(detail_data)
                    success_count += 1

                    # Save progress
                    try:
                        from app.core.database import engine
                        async with engine.begin() as conn:
                            await self._save_detail_progress(conn, sitecode, 'success')
                    except Exception as e:
                        self.log(f"Could not save progress: {str(e)}", level="warning")

                    self.log(f"Success: {detail_data.get('name', 'Unknown')} "
                            f"({success_count} success, {fail_count} failed)")
                else:
                    fail_count += 1

                    # Save progress as failed
                    try:
                        from app.core.database import engine
                        async with engine.begin() as conn:
                            await self._save_detail_progress(conn, sitecode, 'not_found')
                    except Exception:
                        pass

                    self.log(f"No detail found for sitecode {sitecode}")

            except Exception as e:
                fail_count += 1

                # Save error progress
                try:
                    from app.core.database import engine
                    async with engine.begin() as conn:
                        await self._save_detail_progress(conn, sitecode, 'failed', str(e))
                except Exception:
                    pass

                self.log(f"Error fetching detail for {sitecode}: {str(e)}", level="warning")

            # Rate limiting
            if idx < len(sitecodes_to_process) - 1:
                delay = random.uniform(min_delay, max_delay)
                await asyncio.sleep(delay)

        self.log(f"Detail scraping complete! {success_count} success, {fail_count} failed")
        return all_details
