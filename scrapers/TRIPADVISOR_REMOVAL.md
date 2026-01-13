# TripAdvisor Scraper - REMOVED

**Date Removed**: 2025-12-28

## Why TripAdvisor Was Removed

TripAdvisor is **impossible to scrape reliably** due to aggressive bot detection and anti-scraping measures:

### Technical Challenges
1. **Advanced Bot Detection**
   - Cloudflare protection
   - JavaScript challenges
   - Browser fingerprinting
   - IP-based blocking

2. **Rate Limiting**
   - Aggressive rate limits
   - IP bans after minimal requests
   - Requires rotating proxies (expensive)

3. **Dynamic Content**
   - Heavy JavaScript rendering required
   - GraphQL API with authentication tokens
   - Frequently changing HTML structure
   - CSRF tokens and session management

### Attempted Approaches (All Failed)
- ❌ Direct HTTP requests (blocked immediately)
- ❌ GraphQL API (requires authentication, tokens expire)
- ❌ Page scraping with delays (detected and blocked)
- ❌ Browser automation (detected and blocked)

### Better Alternatives

Instead of TripAdvisor, use:

1. **OpenStreetMap (Overpass API)** ✅
   - Free, no authentication
   - Comprehensive POI data
   - Actively maintained by community
   - Includes: museums, monuments, viewpoints, attractions, castles, etc.

2. **Wikidata (SPARQL endpoint)** ✅
   - Free, no authentication
   - Rich structured data
   - Wikipedia links, images, heritage status
   - 32+ POI categories

3. **Google Places API** (Paid but reliable)
   - Official API with pricing
   - Reliable, no bot detection
   - Good coverage, ratings, reviews
   - Costs money but works

### Conclusion

**Do NOT attempt to scrape TripAdvisor again.** Use OpenStreetMap and Wikidata for static POI data. They provide better coverage, are free, and have official APIs designed for this purpose.

If you need ratings/reviews in the future, consider:
- Google Places API (paid)
- Yelp API (paid)
- Facebook Places API
- Foursquare API

But for static tourist attractions, monuments, museums, viewpoints, etc., OpenStreetMap + Wikidata is the best solution.
