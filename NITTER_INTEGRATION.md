# Nitter Integration Guide

## Overview

This document explains how the All For Gooners app integrates with a self-hosted Nitter instance to reliably scrape tweets from key football journalists. Nitter provides a stable and reliable way to access Twitter/X content without depending on brittle reverse-engineered libraries or official APIs that may have rate limits or require payment.

## Architecture

The integration follows this architecture:

1. **Nitter Instance**: A containerized Nitter + Redis setup deployed on Northflank
2. **RSS Feeds**: Nitter provides RSS feeds for Twitter accounts at `https://[nitter-url]/[username]/rss`
3. **NewsScraper**: Our `api/newscraper.py` module connects to these RSS feeds to extract tweets

## Configuration

To use the Nitter integration, set the following in your `.env` file:

```
NITTER_URL=https://your-nitter-instance-url
```

This URL should be the base URL of your Northflank Nitter deployment (without a trailing slash).

## Implementation Details

The Nitter integration includes:

1. **Health Checks**: The `check_nitter_status()` method verifies if the Nitter instance is accessible
2. **Retry Logic**: Failed requests to Nitter will be retried with exponential backoff
3. **Content Cleaning**: Tweet content is cleaned to remove HTML tags, fix formatting, etc.
4. **Error Handling**: The system gracefully degrades if Nitter is unavailable

## Testing

To verify the Nitter integration:

```bash
# Run the test script
python api/test_nitter_integration.py
```

The test script checks:
- If the Nitter instance is reachable
- If RSS feeds can be successfully scraped
- If tweets are properly parsed and cleaned

## Troubleshooting

Common issues and solutions:

1. **Connection failures**:
   - Check if the Nitter URL is correct in the `.env` file
   - Verify the Nitter instance is running on Northflank
   - Ensure your network can reach the Nitter instance

2. **Invalid RSS feeds**:
   - Verify that `/username/rss` endpoints are accessible
   - Check if Nitter is properly configured with Redis

3. **No tweets found**:
   - Check if the Twitter usernames in the scraper are correct
   - Verify the journalists are posting content
   - Check if Twitter has rate-limited or blocked the Nitter instance

## Maintenance

The Nitter instance may occasionally need maintenance:

1. **Clearing Redis cache**: If Nitter becomes slow or unresponsive
2. **Updating Nitter**: When new versions are released that fix bugs or improve stability
3. **Monitoring**: Watch for any unexpected issues with the Nitter deployment

## Future Improvements

Potential enhancements to the Nitter integration:

1. **Multiple Nitter instances**: Implement fallback to different instances if one is unavailable
2. **More journalists**: Expand the list of journalists whose tweets we scrape
3. **Analytics**: Track which journalists provide the most relevant content
4. **Content filtering**: Improve relevance filtering specific to tweets

## Additional Resources

- [Nitter GitHub Repository](https://github.com/zedeus/nitter)
- [RSS Feed Documentation](https://github.com/zedeus/nitter/wiki/RSS-Feeds)
- [Northflank Documentation](https://northflank.com/docs) 