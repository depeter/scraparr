#!/usr/bin/env python3
"""
UiTinVlaanderen API Investigation Script

Quick check to see if UiTdatabank has a public API available.
"""

import requests
from bs4 import BeautifulSoup
import json

def check_api_availability():
    """Check if UiTdatabank has public API"""

    print("=" * 60)
    print("UiTinVlaanderen API Investigation")
    print("=" * 60)

    # URLs to check for API documentation
    urls_to_check = [
        'https://www.uitinvlaanderen.be/',
        'https://www.uitdatabank.be/',
        'https://documentatie.uitdatabank.be/',
        'https://docs.publiq.be/',
        'https://www.uitinvlaanderen.be/api',
        'https://api.uitdatabank.be/',
    ]

    print("\n📡 Checking potential API endpoints...")
    print("-" * 60)

    for url in urls_to_check:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })

            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {url}: {response.status_code}")

            if response.status_code == 200:
                # Look for API keywords
                keywords = ['api', 'developer', 'documentation', 'endpoints',
                           'json', 'rest', 'graphql', 'swagger', 'openapi']
                content = response.text.lower()

                found_keywords = [kw for kw in keywords if kw in content]
                if found_keywords:
                    print(f"   🔍 Found API keywords: {', '.join(found_keywords)}")

                # Check for JSON response
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    print("   📄 Returns JSON!")
                    try:
                        data = response.json()
                        print(f"   📊 JSON keys: {list(data.keys())[:5]}")
                    except:
                        pass

        except requests.exceptions.RequestException as e:
            print(f"❌ {url}: ERROR - {e}")

    # Check robots.txt
    print("\n🤖 Checking robots.txt...")
    print("-" * 60)
    try:
        robots_url = 'https://www.uitinvlaanderen.be/robots.txt'
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            print(response.text[:500])
            if '/api/' in response.text.lower():
                print("\n⚠️  WARNING: /api/ mentioned in robots.txt!")
    except Exception as e:
        print(f"❌ Could not fetch robots.txt: {e}")

    # Check sitemap
    print("\n🗺️  Checking sitemap.xml...")
    print("-" * 60)
    try:
        sitemap_url = 'https://www.uitinvlaanderen.be/sitemap.xml'
        response = requests.get(sitemap_url, timeout=10)
        if response.status_code == 200:
            print(response.text[:800])
    except Exception as e:
        print(f"❌ Could not fetch sitemap: {e}")

    # Check main agenda page for API calls
    print("\n📄 Analyzing main agenda page...")
    print("-" * 60)
    try:
        response = requests.get('https://www.uitinvlaanderen.be/agenda',
                              timeout=10,
                              headers={'User-Agent': 'Mozilla/5.0'})

        if response.status_code == 200:
            # Check for API endpoints in HTML
            api_patterns = ['/api/', '/rest/', '/v1/', '/v2/', '/v3/',
                          'api.', 'graphql', '/__', '/ajax/']

            found_patterns = []
            for pattern in api_patterns:
                if pattern in response.text:
                    found_patterns.append(pattern)

            if found_patterns:
                print(f"✅ Found potential API patterns: {', '.join(found_patterns)}")
            else:
                print("❌ No obvious API patterns found in HTML")

            # Check for JSON-LD structured data
            soup = BeautifulSoup(response.text, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            if json_ld_scripts:
                print(f"\n✅ Found {len(json_ld_scripts)} JSON-LD structured data blocks!")
                for i, script in enumerate(json_ld_scripts[:2]):
                    try:
                        data = json.loads(script.string)
                        print(f"\n   JSON-LD Block {i+1}:")
                        print(f"   Type: {data.get('@type')}")
                        print(f"   Keys: {list(data.keys())[:8]}")
                    except Exception as e:
                        print(f"   Could not parse JSON-LD: {e}")
            else:
                print("❌ No JSON-LD structured data found")

    except Exception as e:
        print(f"❌ Error analyzing agenda page: {e}")

    # Try common API endpoints
    print("\n🔍 Testing common API endpoint patterns...")
    print("-" * 60)

    api_test_urls = [
        'https://api.uitdatabank.be/events',
        'https://api.uitdatabank.be/v3/events',
        'https://www.uitdatabank.be/api/events',
        'https://www.uitinvlaanderen.be/api/events',
    ]

    for url in api_test_urls:
        try:
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            })

            if response.status_code in [200, 401, 403]:
                print(f"✅ {url}: {response.status_code}")
                if response.status_code == 401:
                    print("   ℹ️  Requires authentication (API likely exists!)")
                elif response.status_code == 403:
                    print("   ℹ️  Forbidden (API exists but access restricted)")
                else:
                    print(f"   Content-Type: {response.headers.get('Content-Type')}")
            else:
                print(f"❌ {url}: {response.status_code}")
        except:
            print(f"❌ {url}: Not found")

    print("\n" + "=" * 60)
    print("Investigation complete!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("1. Check browser Network tab at https://www.uitinvlaanderen.be/agenda")
    print("2. Look for XHR/Fetch requests when browsing events")
    print("3. Contact publiq (UiTdatabank operator) for API access if needed")
    print("4. Review documentation at https://docs.publiq.be/ (if found)")


if __name__ == '__main__':
    check_api_availability()
