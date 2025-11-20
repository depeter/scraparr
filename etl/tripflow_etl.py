#!/usr/bin/env python3
"""
ETL Pipeline for syncing data from Scraparr to Tripflow database

This script extracts data from Scraparr's various scraper schemas,
transforms it to match Tripflow's unified schema, and loads it into
the dedicated Tripflow PostgreSQL instance.
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection settings
SCRAPARR_DB_URL = os.getenv(
    'SCRAPARR_DB_URL',
    'postgresql://scraparr:scraparr@localhost:5432/scraparr'
)
TRIPFLOW_DB_URL = os.getenv(
    'TRIPFLOW_DB_URL',
    'postgresql://tripflow:tripflow@localhost:5432/tripflow'
)

# ETL Configuration
BATCH_SIZE = 1000
ENABLE_DEDUPLICATION = True
DEDUP_DISTANCE_METERS = 50  # Consider locations within 50m as potential duplicates


class LocationType(Enum):
    """Tripflow location types"""
    CAMPSITE = 'CAMPSITE'
    PARKING = 'PARKING'
    REST_AREA = 'REST_AREA'
    SERVICE_AREA = 'SERVICE_AREA'
    POI = 'POI'
    EVENT = 'EVENT'
    ATTRACTION = 'ATTRACTION'
    RESTAURANT = 'RESTAURANT'
    HOTEL = 'HOTEL'
    ACTIVITY = 'ACTIVITY'


class PriceType(Enum):
    """Price types"""
    FREE = 'free'
    PAID = 'paid'
    DONATION = 'donation'
    UNKNOWN = 'unknown'


@dataclass
class SyncStats:
    """Statistics for a sync operation"""
    source: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class TripflowETL:
    """Main ETL pipeline class"""

    def __init__(self):
        self.scraparr_conn = None
        self.tripflow_conn = None
        self.sync_stats = {}

    async def connect(self):
        """Establish database connections"""
        logger.info("Connecting to databases...")
        self.scraparr_conn = await asyncpg.connect(SCRAPARR_DB_URL)
        self.tripflow_conn = await asyncpg.connect(TRIPFLOW_DB_URL)
        logger.info("Database connections established")

    async def disconnect(self):
        """Close database connections"""
        if self.scraparr_conn:
            await self.scraparr_conn.close()
        if self.tripflow_conn:
            await self.tripflow_conn.close()
        logger.info("Database connections closed")

    def map_park4night_type(self, park4night_type: str) -> str:
        """Map Park4Night location types to Tripflow types"""
        type_mapping = {
            'camping': LocationType.CAMPSITE.value,
            'parking': LocationType.PARKING.value,
            'rest area': LocationType.REST_AREA.value,
            'aire de service': LocationType.SERVICE_AREA.value,
            'service area': LocationType.SERVICE_AREA.value,
            'poi': LocationType.POI.value,
        }
        return type_mapping.get(
            (park4night_type or '').lower(),
            LocationType.POI.value
        )

    def determine_price_type(self, price_text: str) -> str:
        """Determine price type from text"""
        if not price_text:
            return PriceType.UNKNOWN.value

        price_lower = price_text.lower()
        if any(word in price_lower for word in ['gratuit', 'free', 'gratis', '0€', '0 €']):
            return PriceType.FREE.value
        elif any(word in price_lower for word in ['donation', 'don']):
            return PriceType.DONATION.value
        elif any(char in price_text for char in ['€', '$', '£', '¥']):
            return PriceType.PAID.value
        else:
            return PriceType.UNKNOWN.value

    def extract_amenities(self, services_json: Any) -> List[str]:
        """Extract amenities from Park4Night services JSON"""
        if not services_json:
            return []

        amenities = []
        if isinstance(services_json, str):
            try:
                services_json = json.loads(services_json)
            except:
                return []

        if isinstance(services_json, list):
            return services_json

        # Map common Park4Night service fields to amenities
        service_mapping = {
            'eau': 'water',
            'eau_noire': 'waste_disposal',
            'eau_usee': 'grey_water',
            'electricite': 'electricity',
            'wifi': 'wifi',
            'internet': 'internet',
            'wc': 'toilet',
            'douche': 'shower',
            'laverie': 'laundry',
            'poubelle': 'trash',
            'animaux': 'pets_allowed',
            'pic_nic': 'picnic_area',
            'barbecue': 'bbq',
        }

        if isinstance(services_json, dict):
            for key, value in services_json.items():
                if value and key in service_mapping:
                    amenities.append(service_mapping[key])

        return amenities

    async def sync_park4night(self) -> SyncStats:
        """Sync Park4Night data to Tripflow"""
        logger.info("Starting Park4Night sync...")
        stats = SyncStats(source='park4night', started_at=datetime.now())

        try:
            # Check if scraper_1 schema exists (Park4Night is registered as scraper 1)
            schema_exists = await self.scraparr_conn.fetchval("""
                SELECT EXISTS (
                    SELECT schema_name FROM information_schema.schemata
                    WHERE schema_name = 'scraper_1'
                )
            """)

            if not schema_exists:
                logger.warning("Park4Night schema (scraper_1) does not exist")
                stats.warnings.append("Schema scraper_1 not found")
                return stats

            # Count total records
            total_count = await self.scraparr_conn.fetchval(
                "SELECT COUNT(*) FROM scraper_1.places"
            )
            logger.info(f"Found {total_count} Park4Night places to sync")

            # Process in batches
            offset = 0
            while offset < total_count:
                # Fetch batch
                places = await self.scraparr_conn.fetch("""
                    SELECT
                        id, nom, type, latitude, longitude,
                        pays, ville, description, prix,
                        rating, nb_comment, services,
                        raw_data, updated_at, scraped_at
                    FROM scraper_1.places
                    WHERE latitude IS NOT NULL
                        AND longitude IS NOT NULL
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """, BATCH_SIZE, offset)

                # Transform and load
                for place in places:
                    try:
                        await self.upsert_location({
                            'external_id': f"park4night_{place['id']}",
                            'source': 'park4night',
                            'name': place['nom'] or 'Unknown',
                            'description': place['description'],
                            'location_type': self.map_park4night_type(place['type']),
                            'latitude': float(place['latitude']),
                            'longitude': float(place['longitude']),
                            'country': place['pays'],
                            'city': place['ville'],
                            'rating': float(place['rating']) if place['rating'] else None,
                            'review_count': place['nb_comment'] or 0,
                            'price_type': self.determine_price_type(place['prix']),
                            'price_info': place['prix'],
                            'amenities': json.dumps(self.extract_amenities(place['services'])),
                            'raw_data': place['raw_data'],
                            'updated_at': place['updated_at'] or place['scraped_at']
                        })
                        stats.records_processed += 1

                    except Exception as e:
                        logger.error(f"Error processing Park4Night place {place['id']}: {e}")
                        stats.records_failed += 1
                        stats.errors.append(f"Place {place['id']}: {str(e)}")

                offset += BATCH_SIZE
                logger.info(f"Park4Night progress: {offset}/{total_count}")

                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Park4Night sync failed: {e}")
            stats.errors.append(str(e))

        stats.completed_at = datetime.now()
        return stats

    async def sync_uitinvlaanderen(self) -> SyncStats:
        """Sync UiT in Vlaanderen events to Tripflow"""
        logger.info("Starting UiT in Vlaanderen sync...")
        stats = SyncStats(source='uitinvlaanderen', started_at=datetime.now())

        try:
            # Check if scraper_2 schema exists (UiT is in scraper_2)
            schema_exists = await self.scraparr_conn.fetchval("""
                SELECT EXISTS (
                    SELECT schema_name FROM information_schema.schemata
                    WHERE schema_name = 'scraper_2'
                )
            """)

            if not schema_exists:
                logger.warning("UiT schema (scraper_2) does not exist")
                stats.warnings.append("Schema scraper_2 not found")
                return stats

            # Fetch all events with coordinates
            events = await self.scraparr_conn.fetch("""
                SELECT
                    event_id, name, description, start_date, end_date,
                    location_name, street_address, city, postal_code,
                    latitude, longitude, organizer, event_type,
                    themes, url, image_url, scraped_at, updated_at
                FROM scraper_2.events
                WHERE latitude IS NOT NULL
                    AND longitude IS NOT NULL
                ORDER BY event_id
            """)

            logger.info(f"Found {len(events)} UiT events to sync")

            for event in events:
                try:
                    # First, create/update the location
                    location_id = await self.upsert_location({
                        'external_id': f"uit_location_{event['event_id']}",
                        'source': 'uitinvlaanderen',
                        'source_url': event['url'],
                        'name': event['location_name'] or event['name'],
                        'description': event['description'],
                        'location_type': LocationType.EVENT.value,
                        'latitude': float(event['latitude']),
                        'longitude': float(event['longitude']),
                        'address': event['street_address'],
                        'city': event['city'],
                        'country': event['country'] or 'Belgium',
                        'country_code': 'BE',
                        'postal_code': event['postal_code'],
                        'website': event['url'],
                        'images': json.dumps([event['image_url']]) if event['image_url'] else '[]',
                        'main_image_url': event['image_url'],
                        'tags': json.dumps(event['themes'].split(',')) if event['themes'] else json.dumps([]),
                        'updated_at': event['updated_at'] or event['scraped_at']
                    })

                    # Then create the event
                    if location_id:
                        await self.upsert_event({
                            'location_id': location_id,
                            'external_id': event['event_id'],
                            'source': 'uitinvlaanderen',
                            'name': event['name'],
                            'description': event['description'],
                            'event_type': event['event_type'],
                            'start_date': event['start_date'],
                            'end_date': event['end_date'],
                            'organizer': event['organizer'],
                            'themes': event['themes'].split(',') if event['themes'] else []
                        })

                    stats.records_processed += 1

                except Exception as e:
                    logger.error(f"Error processing UiT event {event['event_id']}: {e}")
                    stats.records_failed += 1
                    stats.errors.append(f"Event {event['event_id']}: {str(e)}")

        except Exception as e:
            logger.error(f"UiT sync failed: {e}")
            stats.errors.append(str(e))

        stats.completed_at = datetime.now()
        return stats

    async def upsert_location(self, location_data: Dict[str, Any]) -> Optional[int]:
        """Insert or update a location in Tripflow"""
        try:
            # Prepare geom value
            lat = location_data['latitude']
            lon = location_data['longitude']

            # Calculate popularity score
            popularity = self.calculate_popularity_score(
                location_data.get('rating'),
                location_data.get('rating_count', 0),
                location_data.get('review_count', 0)
            )

            result = await self.tripflow_conn.fetchval("""
                INSERT INTO tripflow.locations (
                    external_id, source, source_url, name, description,
                    location_type, latitude, longitude, geom,
                    address, city, region, country, country_code, postal_code,
                    rating, rating_count, review_count, popularity_score,
                    price_type, price_info,
                    phone, email, website,
                    amenities, images, main_image_url, tags,
                    raw_data, updated_at
                ) VALUES (
                    $1, $2::tripflow.location_source, $3, $4, $5,
                    $6::tripflow.location_type, $7, $8, ST_MakePoint($8, $7),
                    $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18,
                    $19::tripflow.price_type, $20,
                    $21, $22, $23,
                    $24::jsonb, $25::jsonb, $26, $27,
                    $28::jsonb, $29
                )
                ON CONFLICT (external_id, source) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    location_type = EXCLUDED.location_type,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    geom = EXCLUDED.geom,
                    city = EXCLUDED.city,
                    country = EXCLUDED.country,
                    rating = EXCLUDED.rating,
                    review_count = EXCLUDED.review_count,
                    popularity_score = EXCLUDED.popularity_score,
                    price_type = EXCLUDED.price_type,
                    price_info = EXCLUDED.price_info,
                    amenities = EXCLUDED.amenities,
                    images = EXCLUDED.images,
                    tags = EXCLUDED.tags,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """,
                location_data.get('external_id'),
                location_data.get('source'),
                location_data.get('source_url'),
                location_data.get('name'),
                location_data.get('description'),
                location_data.get('location_type'),
                lat, lon,
                location_data.get('address'),
                location_data.get('city'),
                location_data.get('region'),
                location_data.get('country'),
                location_data.get('country_code'),
                location_data.get('postal_code'),
                location_data.get('rating'),
                location_data.get('rating_count', 0),
                location_data.get('review_count', 0),
                popularity,
                location_data.get('price_type', 'unknown'),
                location_data.get('price_info'),
                location_data.get('phone'),
                location_data.get('email'),
                location_data.get('website'),
                location_data.get('amenities', '[]'),
                location_data.get('images', '[]'),
                location_data.get('main_image_url'),
                location_data.get('tags', []),
                location_data.get('raw_data'),
                location_data.get('updated_at', datetime.now())
            )

            return result

        except Exception as e:
            logger.error(f"Failed to upsert location: {e}")
            raise

    async def upsert_event(self, event_data: Dict[str, Any]) -> bool:
        """Insert or update an event in Tripflow"""
        try:
            await self.tripflow_conn.execute("""
                INSERT INTO tripflow.events (
                    location_id, external_id, source,
                    name, description, event_type,
                    start_date, end_date,
                    organizer, themes
                ) VALUES (
                    $1, $2, $3::tripflow.location_source,
                    $4, $5, $6,
                    $7, $8,
                    $9, $10
                )
                ON CONFLICT (external_id, source) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    event_type = EXCLUDED.event_type,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    organizer = EXCLUDED.organizer,
                    themes = EXCLUDED.themes,
                    updated_at = NOW()
            """,
                event_data['location_id'],
                event_data['external_id'],
                event_data['source'],
                event_data['name'],
                event_data['description'],
                event_data['event_type'],
                event_data['start_date'],
                event_data['end_date'],
                event_data['organizer'],
                event_data['themes']
            )
            return True

        except Exception as e:
            logger.error(f"Failed to upsert event: {e}")
            return False

    def calculate_popularity_score(self, rating: Optional[float],
                                  rating_count: int,
                                  review_count: int) -> float:
        """Calculate popularity score for ranking"""
        score = 0.0

        # Rating contributes up to 50 points
        if rating:
            score += rating * 10

        # Rating count contributes up to 30 points
        if rating_count > 0:
            score += min(30, rating_count / 10)

        # Review count contributes up to 20 points
        if review_count > 0:
            score += min(20, review_count / 5)

        return round(score, 2)

    async def log_sync_results(self, stats: SyncStats):
        """Log sync results to the database"""
        try:
            await self.tripflow_conn.execute("""
                INSERT INTO tripflow.sync_log (
                    sync_type, source, started_at, completed_at,
                    duration_seconds, records_processed, records_inserted,
                    records_updated, records_failed, records_skipped,
                    status, error_message, warnings, sync_params
                ) VALUES (
                    $1, $2::tripflow.location_source, $3, $4,
                    $5, $6, $7, $8, $9, $10,
                    $11, $12, $13::jsonb, $14::jsonb
                )
            """,
                'full',  # sync_type
                stats.source,
                stats.started_at,
                stats.completed_at,
                int((stats.completed_at - stats.started_at).total_seconds()) if stats.completed_at else None,
                stats.records_processed,
                stats.records_inserted,
                stats.records_updated,
                stats.records_failed,
                stats.records_skipped,
                'completed' if not stats.errors else 'failed',
                '; '.join(stats.errors) if stats.errors else None,
                json.dumps(stats.warnings),
                json.dumps({'batch_size': BATCH_SIZE})
            )
        except Exception as e:
            logger.error(f"Failed to log sync results: {e}")

    async def deduplicate_locations(self):
        """Find and mark potential duplicate locations"""
        logger.info("Starting deduplication process...")

        try:
            # Find potential duplicates within 50 meters
            duplicates = await self.tripflow_conn.fetch("""
                WITH potential_duplicates AS (
                    SELECT
                        l1.id as id1,
                        l2.id as id2,
                        l1.name as name1,
                        l2.name as name2,
                        l1.source as source1,
                        l2.source as source2,
                        ST_Distance(l1.geom::geography, l2.geom::geography) as distance_meters
                    FROM tripflow.locations l1
                    JOIN tripflow.locations l2
                        ON l1.id < l2.id
                        AND l1.source != l2.source  -- Different sources
                        AND ST_DWithin(l1.geom::geography, l2.geom::geography, $1)
                )
                SELECT * FROM potential_duplicates
                WHERE distance_meters < $1
                ORDER BY distance_meters
            """, DEDUP_DISTANCE_METERS)

            logger.info(f"Found {len(duplicates)} potential duplicate pairs")

            # For now, just log them - could implement merge logic later
            for dup in duplicates[:10]:  # Show first 10
                logger.info(
                    f"Potential duplicate: {dup['name1']} ({dup['source1']}) "
                    f"<-> {dup['name2']} ({dup['source2']}) "
                    f"at {dup['distance_meters']:.1f}m"
                )

        except Exception as e:
            logger.error(f"Deduplication failed: {e}")

    async def calculate_data_quality_metrics(self):
        """Calculate and store data quality metrics"""
        logger.info("Calculating data quality metrics...")

        try:
            for source in ['park4night', 'uitinvlaanderen']:
                metrics = await self.tripflow_conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_records,
                        COUNT(description) as records_with_description,
                        COUNT(CASE WHEN images != '[]'::jsonb THEN 1 END) as records_with_images,
                        COUNT(rating) as records_with_ratings,
                        COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as records_with_coordinates,
                        COUNT(address) as records_with_address,
                        COUNT(price_info) as records_with_price
                    FROM tripflow.locations
                    WHERE source = $1::tripflow.location_source
                """, source)

                if metrics['total_records'] > 0:
                    completeness = (
                        (metrics['records_with_description'] / metrics['total_records']) * 20 +
                        (metrics['records_with_images'] / metrics['total_records']) * 20 +
                        (metrics['records_with_coordinates'] / metrics['total_records']) * 30 +
                        (metrics['records_with_address'] / metrics['total_records']) * 15 +
                        (metrics['records_with_price'] / metrics['total_records']) * 15
                    )

                    await self.tripflow_conn.execute("""
                        INSERT INTO tripflow.data_quality_metrics (
                            source, metric_date, total_records,
                            records_with_description, records_with_images,
                            records_with_ratings, records_with_coordinates,
                            records_with_address, records_with_price,
                            completeness_score
                        ) VALUES (
                            $1::tripflow.location_source, CURRENT_DATE, $2,
                            $3, $4, $5, $6, $7, $8, $9
                        )
                        ON CONFLICT (source, metric_date) DO UPDATE SET
                            total_records = EXCLUDED.total_records,
                            records_with_description = EXCLUDED.records_with_description,
                            records_with_images = EXCLUDED.records_with_images,
                            records_with_ratings = EXCLUDED.records_with_ratings,
                            records_with_coordinates = EXCLUDED.records_with_coordinates,
                            records_with_address = EXCLUDED.records_with_address,
                            records_with_price = EXCLUDED.records_with_price,
                            completeness_score = EXCLUDED.completeness_score
                    """,
                        source,
                        metrics['total_records'],
                        metrics['records_with_description'],
                        metrics['records_with_images'],
                        metrics['records_with_ratings'],
                        metrics['records_with_coordinates'],
                        metrics['records_with_address'],
                        metrics['records_with_price'],
                        completeness
                    )

                    logger.info(
                        f"{source}: {metrics['total_records']} records, "
                        f"{completeness:.1f}% completeness"
                    )

        except Exception as e:
            logger.error(f"Failed to calculate quality metrics: {e}")

    async def run_full_sync(self):
        """Run complete ETL pipeline"""
        logger.info("Starting full ETL sync...")
        start_time = datetime.now()

        try:
            await self.connect()

            # Sync each source
            park4night_stats = await self.sync_park4night()
            await self.log_sync_results(park4night_stats)

            uit_stats = await self.sync_uitinvlaanderen()
            await self.log_sync_results(uit_stats)

            # Post-processing
            if ENABLE_DEDUPLICATION:
                await self.deduplicate_locations()

            await self.calculate_data_quality_metrics()

            # Summary
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"ETL sync completed in {total_time:.1f} seconds")
            logger.info(f"Park4Night: {park4night_stats.records_processed} processed, "
                       f"{park4night_stats.records_failed} failed")
            logger.info(f"UiT: {uit_stats.records_processed} processed, "
                       f"{uit_stats.records_failed} failed")

        except Exception as e:
            logger.error(f"ETL sync failed: {e}")
            raise
        finally:
            await self.disconnect()


async def main():
    """Main entry point"""
    etl = TripflowETL()
    await etl.run_full_sync()


if __name__ == "__main__":
    asyncio.run(main())