#!/usr/bin/env python3
"""Test Wikidata SPARQL API"""

import asyncio
import httpx
import re

async def main():
    async with httpx.AsyncClient() as client:
        # Test query for Belgian museums from Wikidata
        query = """
        SELECT DISTINCT
            ?item
            ?itemLabel
            ?itemDescription
            ?coord
            ?image
            ?website
            ?wikipedia
            ?heritage ?heritageLabel
        WHERE {
            ?item wdt:P31/wdt:P279* wd:Q33506 .
            ?item wdt:P17 wd:Q31 .
            ?item wdt:P625 ?coord .

            OPTIONAL { ?item wdt:P18 ?image . }
            OPTIONAL { ?item wdt:P856 ?website . }
            OPTIONAL { ?item wdt:P1435 ?heritage . }

            OPTIONAL {
                ?wikipedia schema:about ?item ;
                           schema:isPartOf <https://en.wikipedia.org/> .
            }

            SERVICE wikibase:label { bd:serviceParam wikibase:language "en,nl,fr" . }
        }
        LIMIT 100
        """

        print("Testing Wikidata SPARQL for Belgian museums...")

        response = await client.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "Scraparr/1.0 (test)",
            },
            timeout=60.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            print(f"\nFound {len(bindings)} museums in Belgium from Wikidata!\n")

            for binding in bindings[:10]:
                item_uri = binding.get('item', {}).get('value', '')
                wikidata_id = item_uri.split('/')[-1]
                name = binding.get('itemLabel', {}).get('value', '')
                description = binding.get('itemDescription', {}).get('value', '')
                coord = binding.get('coord', {}).get('value', '')
                image = binding.get('image', {}).get('value', '')
                wikipedia = binding.get('wikipedia', {}).get('value', '')
                heritage = binding.get('heritageLabel', {}).get('value', '')

                # Parse coordinates
                lat, lon = None, None
                if coord:
                    match = re.search(r'Point\(([-.0-9]+)\s+([-.0-9]+)\)', coord)
                    if match:
                        lon = float(match.group(1))
                        lat = float(match.group(2))

                print(f"  {name} ({wikidata_id})")
                if description:
                    print(f"    {description[:80]}...")
                print(f"    Coords: {lat:.5f}, {lon:.5f}" if lat else "    Coords: N/A")
                print(f"    Image: {'Yes' if image else 'No'} | Wikipedia: {'Yes' if wikipedia else 'No'}")
                if heritage:
                    print(f"    Heritage: {heritage}")
                print()

        # Also test castles
        print("\n" + "="*60)
        print("Testing castles in Belgium...")

        query2 = """
        SELECT DISTINCT
            ?item
            ?itemLabel
            ?coord
            ?image
            ?inception
        WHERE {
            ?item wdt:P31/wdt:P279* wd:Q23413 .
            ?item wdt:P17 wd:Q31 .
            ?item wdt:P625 ?coord .

            OPTIONAL { ?item wdt:P18 ?image . }
            OPTIONAL { ?item wdt:P571 ?inception . }

            SERVICE wikibase:label { bd:serviceParam wikibase:language "en,nl,fr" . }
        }
        LIMIT 50
        """

        response2 = await client.get(
            "https://query.wikidata.org/sparql",
            params={"query": query2, "format": "json"},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "Scraparr/1.0 (test)",
            },
            timeout=60.0
        )

        if response2.status_code == 200:
            data2 = response2.json()
            bindings2 = data2.get('results', {}).get('bindings', [])
            print(f"\nFound {len(bindings2)} castles in Belgium!\n")

            for binding in bindings2[:5]:
                name = binding.get('itemLabel', {}).get('value', '')
                inception = binding.get('inception', {}).get('value', '')
                image = binding.get('image', {}).get('value', '')

                print(f"  {name}")
                if inception:
                    year_match = re.search(r'(\d{4})', inception)
                    if year_match:
                        print(f"    Built: {year_match.group(1)}")
                print(f"    Has image: {'Yes' if image else 'No'}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
