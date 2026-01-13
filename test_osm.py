#!/usr/bin/env python3
"""Test OpenStreetMap Overpass API"""

import asyncio
import httpx

EUROPEAN_COUNTRIES = {
    "belgium": {"name": "Belgium", "iso": "BE", "bbox": [49.5, 2.5, 51.5, 6.4]},
}

async def main():
    async with httpx.AsyncClient() as client:
        bbox = EUROPEAN_COUNTRIES['belgium']['bbox']
        south, west, north, east = bbox

        # Query for museums in Belgium
        query = f"""
        [out:json][timeout:60];
        (
            node["tourism"="museum"]({south},{west},{north},{east});
            way["tourism"="museum"]({south},{west},{north},{east});
        );
        out center tags;
        """

        print(f"Testing Overpass API for Belgium museums...")
        print(f"Bbox: {bbox}")

        response = await client.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            print(f"\nFound {len(elements)} museums in Belgium!\n")

            for elem in elements[:10]:
                tags = elem.get('tags', {})
                name = tags.get('name', 'Unnamed')
                lat = elem.get('lat') or elem.get('center', {}).get('lat')
                lon = elem.get('lon') or elem.get('center', {}).get('lon')
                website = tags.get('website', 'N/A')
                wikidata = tags.get('wikidata', 'N/A')

                print(f"  {name}")
                print(f"    Coords: {lat:.5f}, {lon:.5f}")
                print(f"    Website: {website[:60]}..." if len(str(website)) > 60 else f"    Website: {website}")
                print(f"    Wikidata: {wikidata}")
                print()

        # Also test historic monuments
        print("\n" + "="*60)
        query2 = f"""
        [out:json][timeout:60];
        (
            node["historic"="monument"]({south},{west},{north},{east});
            way["historic"="monument"]({south},{west},{north},{east});
        );
        out center tags;
        """

        response2 = await client.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query2},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60.0
        )

        if response2.status_code == 200:
            data2 = response2.json()
            elements2 = data2.get('elements', [])
            print(f"\nFound {len(elements2)} historic monuments in Belgium!\n")

            for elem in elements2[:5]:
                tags = elem.get('tags', {})
                name = tags.get('name', 'Unnamed')
                lat = elem.get('lat') or elem.get('center', {}).get('lat')
                lon = elem.get('lon') or elem.get('center', {}).get('lon')

                print(f"  {name}")
                print(f"    Coords: {lat:.5f}, {lon:.5f}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
