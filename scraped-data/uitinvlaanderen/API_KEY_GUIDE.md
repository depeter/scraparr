# Getting a UiTdatabank API Key

## Overview

The UiTdatabank Search API requires authentication via an API key. This guide explains how to obtain one.

## Steps to Get an API Key

### Option 1: Publiq Developer Portal (Recommended)

1. **Visit the Developer Portal**
   - Go to: https://docs.publiq.be
   - Or: https://www.publiq.be

2. **Register for an Account**
   - Click on "Register" or "Sign Up"
   - Fill in your details
   - Verify your email address

3. **Request API Access**
   - Navigate to the API documentation section
   - Look for "Get API Key" or "Request Access"
   - Fill out the API access request form
   - Explain your use case (personal project, research, etc.)

4. **Receive Your API Key**
   - After approval (usually 1-2 business days), you'll receive:
     - API key (x-api-key)
     - API documentation
     - Rate limits and usage guidelines

### Option 2: UiTdatabank Platform

1. **Visit UiTdatabank**
   - Go to: https://www.uitdatabank.be

2. **Contact Support**
   - Look for contact information or support email
   - Request API access for the Search API
   - Provide details about your project

3. **Documentation**
   - Once approved, you'll get access to:
     - Full API documentation
     - Example code
     - Support channels

## API Key Information

### What You'll Receive

- **API Key Format**: Usually a long alphanumeric string
- **Authentication Method**: X-Api-Key header
- **Rate Limits**: Typically 100-1000 requests per minute (check your specific limits)
- **Access Level**: Read-only access to public event data

### API Endpoints

Once you have your key, you can access:

- **Search Endpoint**: `https://search.uitdatabank.be/offers/`
- **Event Details**: `https://search.uitdatabank.be/offers/{event-id}`
- **Places**: `https://search.uitdatabank.be/places/`
- **Organizers**: `https://search.uitdatabank.be/organizers/`

## Using Your API Key

### Environment Variable (Recommended)

```bash
export UITDATABANK_API_KEY="your-api-key-here"
```

### In Python Code

```python
import os
from scraper import UiTinVlaanderenScraper

# From environment variable
api_key = os.getenv('UITDATABANK_API_KEY')
scraper = UiTinVlaanderenScraper(api_key=api_key)

# Or directly (not recommended for production)
scraper = UiTinVlaanderenScraper(api_key="your-api-key-here")
```

### In Shell Scripts

```bash
#!/bin/bash
export UITDATABANK_API_KEY="your-api-key-here"
python scraper.py
```

## Testing Your API Key

Once you have your key, test it:

```bash
# Using curl
curl -H "X-Api-Key: your-api-key-here" \
     "https://search.uitdatabank.be/offers/?limit=1"
```

Expected response:
```json
{
  "@context": "http://www.w3.org/ns/hydra/context.jsonld",
  "@type": "PagedCollection",
  "itemsPerPage": 1,
  "totalItems": 12345,
  "member": [...]
}
```

## Troubleshooting

### 401 Unauthorized

```json
{
  "title": "Unauthorized",
  "status": 401,
  "detail": "No x-api-key header or apiKey parameter found"
}
```

**Solutions:**
- Make sure you're including the API key in the request
- Check the header name is exactly `X-Api-Key`
- Verify your API key is correct

### 403 Forbidden

**Solutions:**
- Your API key may have expired
- You may have exceeded rate limits
- Contact support to verify your API access

### 429 Too Many Requests

**Solutions:**
- You've exceeded the rate limit
- Implement rate limiting in your code (use `rate_limit_delay` parameter)
- Wait before making more requests

## Rate Limiting Best Practices

1. **Use Delays Between Requests**
   ```python
   scraper = UiTinVlaanderenScraper(
       api_key=api_key,
       rate_limit_delay=0.5  # 0.5 seconds between requests
   )
   ```

2. **Cache Results**
   - Save scraped data to avoid repeated requests
   - Use the `save_events()` method

3. **Be Respectful**
   - Don't scrape more data than you need
   - Use specific filters to reduce API calls
   - Consider batch processing during off-peak hours

## Alternative: No API Key?

If you can't get an API key or need a quick solution:

1. **Use the Web Scraper**
   - `web_scraper.py` doesn't require an API key
   - Note: Less reliable due to client-side rendering

2. **Request Access**
   - Most API providers are happy to provide access for legitimate use cases
   - Be clear about your intended use

3. **Public Data**
   - UiTdatabank provides public cultural data
   - Access is usually granted for non-commercial, research, or personal projects

## Resources

- **Publiq Documentation**: https://docs.publiq.be
- **UiTdatabank**: https://www.uitdatabank.be
- **API Support**: Check the Publiq website for contact information
- **Developer Community**: Look for Publiq developer forums or GitHub repositories

## Legal & Ethical Considerations

- Respect the API terms of service
- Don't abuse rate limits
- Attribute data properly if publishing
- Use data responsibly
- Don't resell or redistribute scraped data without permission

## Contact Information

If you need help getting an API key:

1. Visit https://www.publiq.be
2. Look for "Contact" or "Support" sections
3. Explain your use case clearly
4. Be patient - approval may take a few days
