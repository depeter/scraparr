#!/usr/bin/env python3
"""
Analyze captured mitmproxy traffic and extract API endpoints
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

try:
    from mitmproxy import io
    from mitmproxy.exceptions import FlowReadException
except ImportError:
    print("Error: mitmproxy not installed")
    print("Install with: pip3 install mitmproxy")
    sys.exit(1)


def analyze_flow(flow):
    """Extract relevant information from a flow"""
    request = flow.request
    response = flow.response

    info = {
        'method': request.method,
        'url': request.url,
        'host': request.host,
        'path': request.path,
        'scheme': request.scheme,
        'headers': dict(request.headers),
        'status_code': response.status_code if response else None,
        'response_headers': dict(response.headers) if response else None,
        'query_params': dict(parse_qs(urlparse(request.url).query)),
    }

    # Try to parse request body
    if request.content:
        try:
            info['request_body'] = request.text
            if request.headers.get('content-type', '').startswith('application/json'):
                info['request_json'] = json.loads(request.text)
        except:
            info['request_body'] = '<binary data>'

    # Try to parse response body
    if response and response.content:
        try:
            info['response_body'] = response.text[:1000]  # First 1000 chars
            if response.headers.get('content-type', '').startswith('application/json'):
                info['response_json'] = json.loads(response.text)
        except:
            info['response_body'] = '<binary or too large>'

    return info


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_traffic.py <capture_file.mitm>")
        print("\nExample:")
        print("  python3 analyze_traffic.py campercontact_traffic.mitm")
        sys.exit(1)

    capture_file = sys.argv[1]

    if not Path(capture_file).exists():
        print(f"Error: File not found: {capture_file}")
        sys.exit(1)

    print(f"Analyzing: {capture_file}")
    print("=" * 80)
    print()

    # Group requests by domain
    domains = defaultdict(list)
    api_endpoints = defaultdict(list)

    with open(capture_file, "rb") as logfile:
        freader = io.FlowReader(logfile)
        try:
            for flow in freader.stream():
                if flow.request:
                    info = analyze_flow(flow)
                    domains[info['host']].append(info)

                    # Try to identify API endpoints
                    if any(x in info['path'].lower() for x in ['api', 'graphql', 'rest', 'v1', 'v2']):
                        api_endpoints[info['host']].append(info)
        except FlowReadException as e:
            print(f"Warning: Error reading flow: {e}")

    # Print summary
    print(f"Total domains: {len(domains)}")
    print()

    # Print domains sorted by number of requests
    print("Domains by request count:")
    print("-" * 80)
    for host, requests in sorted(domains.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {host}: {len(requests)} requests")
    print()

    # Focus on likely API domains
    print("Potential API endpoints:")
    print("=" * 80)

    for host, endpoints in api_endpoints.items():
        print(f"\n{host}")
        print("-" * 80)

        # Group by path pattern
        paths = defaultdict(list)
        for ep in endpoints:
            paths[ep['path']].append(ep)

        for path, eps in sorted(paths.items()):
            methods = list(set(ep['method'] for ep in eps))
            status_codes = list(set(ep['status_code'] for ep in eps if ep['status_code']))

            print(f"  {', '.join(methods):8} {path}")
            print(f"           Status: {status_codes}")

            # Print headers that might contain auth
            for ep in eps[:1]:  # Just first example
                auth_headers = {k: v for k, v in ep['headers'].items()
                              if k.lower() in ['authorization', 'x-api-key', 'x-auth-token', 'api-key']}
                if auth_headers:
                    print(f"           Auth headers: {auth_headers}")

            print()

    # Save detailed analysis to JSON
    output_file = capture_file.replace('.mitm', '_analysis.json')

    # Prepare data for JSON export (remove non-serializable items)
    export_data = {}
    for host, requests in domains.items():
        export_data[host] = []
        for req in requests:
            # Create a simplified version
            simplified = {
                'method': req['method'],
                'url': req['url'],
                'path': req['path'],
                'status_code': req['status_code'],
                'headers': req['headers'],
                'query_params': req['query_params'],
            }

            # Add body samples if available
            if 'request_json' in req:
                simplified['request_sample'] = req['request_json']
            if 'response_json' in req:
                simplified['response_sample'] = req['response_json']

            export_data[host].append(simplified)

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print()
    print(f"Detailed analysis saved to: {output_file}")
    print()
    print("Next steps:")
    print("1. Review the analysis above to identify CamperContact API endpoints")
    print("2. Check the JSON file for request/response samples")
    print("3. Document the API in api_documentation.md")
    print("4. Test endpoints with curl or Postman")
    print("5. Build the scraper using the discovered API")


if __name__ == '__main__':
    main()
