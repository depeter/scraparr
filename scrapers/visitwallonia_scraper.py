"""
Visit Wallonia / CGT PIVOT Tourism Scraper

This scraper fetches tourism data from the Wallonia (Belgium) PIVOT database
via the Open Data Wallonie-Bruxelles (ODWB) OpenDataSoft API.

Available datasets:
- cgt-pivot-attractions-et-loisirs: Attractions and leisure activities (~8,500 records)
- cgt-pivot-restaurants: Restaurants (~3,200 records)
- cgt-pivot-hotels: Gîtes/lodges (~3,000+ records)
- cgt-pivot-meubles: Furnished accommodations
- cgt-pivot-villages-de-vacances: Vacation villages
- cgt-pivot-organismes-touristiques: Tourism organizations

API Documentation: https://www.odwb.be/api/explore/v2.1/
Data source: Commissariat Général au Tourisme (CGT) - Wallonie

Author: Scraparr
"""
import sys
import os
sys.path.insert(0, '/app/backend')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.scrapers.base import BaseScraper, ScraperType
except ImportError:
    # Fallback for standalone testing
    from abc import ABC, abstractmethod
    from enum import Enum

    class ScraperType(str, Enum):
        API = "api"
        WEB = "web"

    class BaseScraper(ABC):
        scraper_type = ScraperType.API
        def __init__(self, scraper_id=0, schema_name=None, config=None, headers=None, execution_id=None):
            self.scraper_id = scraper_id
            self.schema_name = schema_name
            self.config = config or {}
            self.headers = headers or {}
            self.execution_id = execution_id
            self.logs = []
            import httpx
            self.http_client = httpx.AsyncClient(timeout=300.0)
            from sqlalchemy import MetaData
            self.metadata = MetaData(schema=schema_name)

        def log(self, message, level="info"):
            print(f"[{level.upper()}] {message}")
            self.logs.append(f"[{level}] {message}")

        async def report_progress(self, items, msg):
            pass

        async def cleanup(self):
            await self.http_client.aclose()

from typing import Dict, Any, List, Optional
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text, JSON, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import random
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VisitWalloniaScraper(BaseScraper):
    """
    Scraper for Visit Wallonia tourism data via ODWB OpenDataSoft API

    The PIVOT database contains official tourism data for the Wallonia region
    of Belgium, maintained by the Commissariat Général au Tourisme (CGT).
    """

    scraper_type = ScraperType.API

    BASE_URL = "https://www.odwb.be/api/explore/v2.1/catalog/datasets"
    ARCGIS_URL = "https://geoservices.wallonie.be/arcgis/rest/services/TOURISME/OFFRES_TOURISTIQUES/MapServer"

    # ArcGIS layer IDs for enrichment (phone, email, website, facebook)
    ARCGIS_LAYERS = {
        "attractions": 10,  # Decouvertes et divertissements
        "restaurants": 8,
        "gites": 3,
        "chambres_hotes": 13,
        "meubles": 4,
        "camping": 5,
        "villages_vacances": 7,
        "organismes": 12,
    }

    # Available datasets with their identifiers
    DATASETS = {
        "attractions": "cgt-pivot-attractions-et-loisirs",
        "restaurants": "cgt-pivot-restaurants",
        "gites": "cgt-pivot-hotels",  # Note: dataset is called "hotels" but contains gîtes
        "meubles": "cgt-pivot-meubles",  # Furnished rentals
        "villages_vacances": "cgt-pivot-villages-de-vacances",
        "organismes": "cgt-pivot-organismes-touristiques",
        "camping": "cgt-pivot-campings",  # Campings if available
        "chambres_hotes": "cgt-pivot-chambres-dhotes",  # B&Bs if available
    }

    def define_tables(self) -> List[Table]:
        """Define database tables for storing Visit Wallonia data"""

        # Main POI (Points of Interest) table - unified schema for all datasets
        poi_table = Table(
            'pois',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('codecgt', String(50), unique=True),  # Unique CGT identifier
            Column('dataset', String(100), index=True),  # Source dataset name
            Column('nom', String(500)),  # Name
            Column('description', Text),  # Description if available
            Column('typeoffre_id', String(20)),  # Offer type ID (string from API)
            Column('typeoffre_label', String(200)),  # Offer type label

            # Address fields
            Column('rue', String(300)),  # Street
            Column('numero', String(20)),  # Street number
            Column('cp', String(10)),  # Postal code
            Column('commune', String(100), index=True),  # Municipality
            Column('localite', String(100)),  # Locality
            Column('province', String(100)),  # Province

            # Geographic coordinates
            Column('latitude', Float),
            Column('longitude', Float),
            Column('altitude', Float),

            # Organization info
            Column('organisme_id', String(50)),
            Column('organisme_label', String(200)),

            # Contact info (from ArcGIS enrichment)
            Column('phone', String(50)),
            Column('email', String(200)),
            Column('website', String(500)),
            Column('facebook', String(500)),

            # Metadata
            Column('datecreation', DateTime),  # Original creation date
            Column('datemodification', DateTime),  # Last modification date
            Column('raw_data', JSON),  # Store complete API response
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        # Scraping progress tracking
        progress_table = Table(
            'scrape_progress',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('dataset', String(100)),
            Column('total_records', Integer),
            Column('records_fetched', Integer),
            Column('last_offset', Integer),
            Column('completed', Integer, default=0),  # 0 or 1
            Column('processed_at', DateTime, default=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        return [poi_table, progress_table]

    async def _fetch_arcgis_contact_data(self, layer_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Fetch contact data from ArcGIS REST service for a specific layer.
        Uses OBJECTID-based pagination since resultOffset is blocked.

        Returns a dict mapping CODE (codecgt) to contact info.
        """
        import httpx

        contact_data = {}
        min_objectid = 0
        batch_size = 2000  # ArcGIS default max return

        # Custom headers for ArcGIS - browser-like to avoid 403
        arcgis_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://geoservices.wallonie.be/",
        }

        while True:
            url = f"{self.ARCGIS_URL}/{layer_id}/query"
            params = {
                "where": f"OBJECTID>{min_objectid}",
                "outFields": "OBJECTID,CODE,PHONE1,MAIL,SITE_WEB,FACEBOOK",
                "returnGeometry": "false",
                "orderByFields": "OBJECTID",
                "f": "json"
            }

            try:
                # Use separate client with browser headers for ArcGIS
                async with httpx.AsyncClient(headers=arcgis_headers, timeout=60.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    features = data.get("features", [])
                    if not features:
                        break

                    max_oid = 0
                    for feature in features:
                        attrs = feature.get("attributes", {})
                        code = attrs.get("CODE")
                        oid = attrs.get("OBJECTID", 0)
                        if oid > max_oid:
                            max_oid = oid
                        if code:
                            contact_data[code] = {
                                "phone": attrs.get("PHONE1"),
                                "email": attrs.get("MAIL"),
                                "website": attrs.get("SITE_WEB"),
                                "facebook": attrs.get("FACEBOOK"),
                            }

                    # Check if there are more records
                    if len(features) < batch_size:
                        break

                    min_objectid = max_oid

            except Exception as e:
                self.log(f"Error fetching ArcGIS layer {layer_id}: {str(e)}", level="warning")
                break

        return contact_data

    async def _fetch_dataset_records(
        self,
        dataset_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Fetch records from a specific ODWB dataset

        Args:
            dataset_id: The OpenDataSoft dataset identifier
            offset: Pagination offset
            limit: Number of records per request (max 100)

        Returns:
            API response with records and total count
        """
        url = f"{self.BASE_URL}/{dataset_id}/records"

        params = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"Error fetching {dataset_id} (offset {offset}): {str(e)}", level="error")
            raise

    def _parse_record(self, record: Dict[str, Any], dataset_name: str) -> Dict[str, Any]:
        """
        Parse a record from the API into standardized format

        Args:
            record: Raw record from API
            dataset_name: Name of the source dataset

        Returns:
            Parsed record dictionary
        """
        fields = record.get("record", {}).get("fields", {}) if "record" in record else record.get("fields", record)

        # Handle geo point
        geo_point = fields.get("adresse_point_geo") or fields.get("geo_point_2d")
        lat = None
        lon = None
        if geo_point:
            if isinstance(geo_point, dict):
                lat = geo_point.get("lat")
                lon = geo_point.get("lon")
            elif isinstance(geo_point, list) and len(geo_point) == 2:
                lat, lon = geo_point

        # Fallback to explicit lat/lon fields
        if lat is None:
            lat = fields.get("adresse1_latitude") or fields.get("latitude")
        if lon is None:
            lon = fields.get("adresse1_longitude") or fields.get("longitude")

        # Parse dates (convert to naive UTC for PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
        date_creation = None
        date_modification = None
        try:
            if fields.get("datecreation"):
                dt = datetime.fromisoformat(
                    fields["datecreation"].replace("Z", "+00:00")
                )
                # Convert to naive UTC datetime
                date_creation = dt.replace(tzinfo=None) if dt.tzinfo else dt
            if fields.get("datemodification"):
                dt = datetime.fromisoformat(
                    fields["datemodification"].replace("Z", "+00:00")
                )
                # Convert to naive UTC datetime
                date_modification = dt.replace(tzinfo=None) if dt.tzinfo else dt
        except (ValueError, AttributeError):
            pass

        return {
            "codecgt": fields.get("codecgt"),
            "dataset": dataset_name,
            "nom": fields.get("nom"),
            "description": fields.get("description") or fields.get("descriptionsynthese"),
            "typeoffre_id": fields.get("typeoffre_idtypeoffre"),
            "typeoffre_label": fields.get("typeoffre_label_value"),
            "rue": fields.get("adresse1_rue"),
            "numero": fields.get("adresse1_numero"),
            "cp": fields.get("adresse1_cp"),
            "commune": fields.get("adresse1_commune_value"),
            "localite": fields.get("adresse1_localite_value"),
            "province": fields.get("adresse1_province_value"),
            "latitude": float(lat) if lat else None,
            "longitude": float(lon) if lon else None,
            "altitude": float(fields.get("adresse1_altitude")) if fields.get("adresse1_altitude") else None,
            "organisme_id": fields.get("adresse1_organisme_idmdt"),
            "organisme_label": fields.get("adresse1_organisme_label"),
            "datecreation": date_creation,
            "datemodification": date_modification,
            "raw_data": fields,
        }

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape tourism data from Visit Wallonia PIVOT database

        Expected params:
            - datasets: List of datasets to scrape. Options:
                - "all": Scrape all available datasets
                - "attractions": Attractions and leisure
                - "restaurants": Restaurants
                - "gites": Gîtes/lodges
                - "meubles": Furnished rentals
                - "villages_vacances": Vacation villages
                - "organismes": Tourism organizations
              Default: ["attractions", "restaurants", "gites"]

            - limit_per_dataset: Max records per dataset (default: None = all)
            - page_size: Records per API request (default: 100, max: 100)
            - min_delay: Min delay between requests (default: 0.5)
            - max_delay: Max delay between requests (default: 2.0)
            - resume: Resume from last progress (default: True)
            - enrich_contacts: Fetch phone/email/website from ArcGIS (default: True)

        Returns:
            List of all scraped POI records
        """
        # Get parameters
        datasets_param = params.get("datasets", ["attractions", "restaurants", "gites"])
        limit_per_dataset = params.get("limit_per_dataset")
        page_size = min(params.get("page_size", 100), 100)  # Max 100
        min_delay = params.get("min_delay", 0.5)
        max_delay = params.get("max_delay", 2.0)
        resume = params.get("resume", True)
        enrich_contacts = params.get("enrich_contacts", True)

        # Determine which datasets to scrape
        if datasets_param == "all" or "all" in datasets_param:
            datasets_to_scrape = list(self.DATASETS.keys())
        else:
            datasets_to_scrape = datasets_param if isinstance(datasets_param, list) else [datasets_param]

        self.log(f"Starting Visit Wallonia scrape for datasets: {datasets_to_scrape}")
        self.log(f"Rate limiting: {min_delay}-{max_delay}s delay between requests")

        all_records = []

        for dataset_key in datasets_to_scrape:
            if dataset_key not in self.DATASETS:
                self.log(f"Unknown dataset: {dataset_key}, skipping", level="warning")
                continue

            dataset_id = self.DATASETS[dataset_key]
            self.log(f"\n--- Scraping dataset: {dataset_key} ({dataset_id}) ---")

            # Fetch contact data from ArcGIS if enabled
            contact_lookup = {}
            if enrich_contacts and dataset_key in self.ARCGIS_LAYERS:
                layer_id = self.ARCGIS_LAYERS[dataset_key]
                self.log(f"Fetching contact data from ArcGIS layer {layer_id}...")
                contact_lookup = await self._fetch_arcgis_contact_data(layer_id)
                self.log(f"Found contact data for {len(contact_lookup)} records")

            try:
                # Fetch first page to get total count
                first_response = await self._fetch_dataset_records(dataset_id, offset=0, limit=1)
                total_count = first_response.get("total_count", 0)

                if total_count == 0:
                    self.log(f"Dataset {dataset_key} has no records or doesn't exist", level="warning")
                    continue

                self.log(f"Dataset {dataset_key}: {total_count} total records available")

                # Determine how many to fetch
                records_to_fetch = min(total_count, limit_per_dataset) if limit_per_dataset else total_count

                dataset_records = []
                offset = 0

                while offset < records_to_fetch:
                    current_limit = min(page_size, records_to_fetch - offset)

                    self.log(f"Fetching {dataset_key}: offset {offset}, limit {current_limit}")

                    response = await self._fetch_dataset_records(dataset_id, offset=offset, limit=current_limit)

                    results = response.get("results", [])
                    if not results:
                        self.log(f"No more results for {dataset_key}")
                        break

                    for record in results:
                        parsed = self._parse_record(record, dataset_key)
                        if parsed.get("codecgt"):  # Only add if has valid ID
                            # Enrich with contact data if available
                            codecgt = parsed["codecgt"]
                            if codecgt in contact_lookup:
                                contact = contact_lookup[codecgt]
                                parsed["phone"] = contact.get("phone")
                                parsed["email"] = contact.get("email")
                                parsed["website"] = contact.get("website")
                                parsed["facebook"] = contact.get("facebook")
                            dataset_records.append(parsed)

                    offset += len(results)

                    # Progress reporting
                    await self.report_progress(
                        len(all_records) + len(dataset_records),
                        f"Fetched {len(dataset_records)}/{records_to_fetch} from {dataset_key}"
                    )

                    # Rate limiting
                    if offset < records_to_fetch:
                        delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(delay)

                all_records.extend(dataset_records)
                self.log(f"Completed {dataset_key}: {len(dataset_records)} records fetched")

            except Exception as e:
                self.log(f"Error scraping dataset {dataset_key}: {str(e)}", level="error")
                continue

        self.log(f"\n=== Scraping complete: {len(all_records)} total records ===")
        return all_records

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Store scraped data in database using upsert"""
        if not results:
            self.log("No results to store in database")
            return

        self.log(f"Storing {len(results)} POIs in database...")

        try:
            from app.core.database import engine
            from sqlalchemy import text

            async with engine.begin() as conn:
                # Ensure schema exists
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))

                tables = self.define_tables()
                poi_table = tables[0]

                await conn.run_sync(self.metadata.create_all)

                # Batch upsert
                batch_size = 500
                total_stored = 0

                for i in range(0, len(results), batch_size):
                    batch = results[i:i + batch_size]

                    for record in batch:
                        poi_data = {
                            'codecgt': record.get('codecgt'),
                            'dataset': record.get('dataset'),
                            'nom': record.get('nom'),
                            'description': record.get('description'),
                            'typeoffre_id': record.get('typeoffre_id'),
                            'typeoffre_label': record.get('typeoffre_label'),
                            'rue': record.get('rue'),
                            'numero': record.get('numero'),
                            'cp': record.get('cp'),
                            'commune': record.get('commune'),
                            'localite': record.get('localite'),
                            'province': record.get('province'),
                            'latitude': record.get('latitude'),
                            'longitude': record.get('longitude'),
                            'altitude': record.get('altitude'),
                            'organisme_id': record.get('organisme_id'),
                            'organisme_label': record.get('organisme_label'),
                            'phone': record.get('phone'),
                            'email': record.get('email'),
                            'website': record.get('website'),
                            'facebook': record.get('facebook'),
                            'datecreation': record.get('datecreation'),
                            'datemodification': record.get('datemodification'),
                            'raw_data': record.get('raw_data'),
                            'updated_at': datetime.utcnow(),
                        }

                        # Upsert
                        stmt = pg_insert(poi_table).values(**poi_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['codecgt'],
                            set_={
                                'dataset': stmt.excluded.dataset,
                                'nom': stmt.excluded.nom,
                                'description': stmt.excluded.description,
                                'typeoffre_id': stmt.excluded.typeoffre_id,
                                'typeoffre_label': stmt.excluded.typeoffre_label,
                                'rue': stmt.excluded.rue,
                                'numero': stmt.excluded.numero,
                                'cp': stmt.excluded.cp,
                                'commune': stmt.excluded.commune,
                                'localite': stmt.excluded.localite,
                                'province': stmt.excluded.province,
                                'latitude': stmt.excluded.latitude,
                                'longitude': stmt.excluded.longitude,
                                'altitude': stmt.excluded.altitude,
                                'organisme_id': stmt.excluded.organisme_id,
                                'organisme_label': stmt.excluded.organisme_label,
                                'phone': stmt.excluded.phone,
                                'email': stmt.excluded.email,
                                'website': stmt.excluded.website,
                                'facebook': stmt.excluded.facebook,
                                'datecreation': stmt.excluded.datecreation,
                                'datemodification': stmt.excluded.datemodification,
                                'raw_data': stmt.excluded.raw_data,
                                'updated_at': stmt.excluded.updated_at,
                            }
                        )
                        await conn.execute(stmt)

                    total_stored += len(batch)
                    self.log(f"Stored batch: {total_stored}/{len(results)} records")

                self.log(f"Successfully stored {len(results)} POIs in database")

        except Exception as e:
            self.log(f"Error storing data in database: {str(e)}", level="error")
            raise


# For standalone testing
if __name__ == "__main__":
    import asyncio

    async def test():
        scraper = VisitWalloniaScraper(
            scraper_id=0,
            schema_name="test_visitwallonia"
        )

        params = {
            "datasets": ["attractions"],
            "limit_per_dataset": 10,
            "min_delay": 0.5,
            "max_delay": 1.0
        }

        try:
            results = await scraper.scrape(params)
            print(f"\nFound {len(results)} records")

            for record in results[:3]:
                print(f"\n- {record['nom']}")
                print(f"  Type: {record['typeoffre_label']}")
                print(f"  Location: {record['commune']}, {record['cp']}")
                print(f"  Coords: ({record['latitude']}, {record['longitude']})")
        finally:
            await scraper.cleanup()

    asyncio.run(test())
