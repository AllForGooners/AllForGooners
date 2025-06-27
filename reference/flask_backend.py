#!/usr/bin/env python3
"""
Arsenal Transfer News Backend API
Flask application that serves scraped transfer data and provides real-time updates

This backend integrates with the scraping system to provide a REST API
for the Arsenal transfer rumors website.

Author: Gemini Pro @ Cursor
Date: 2024-05-21
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from threading import Thread
import time

from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
from arsenal_scraper import main as run_all_scrapers, RUMORS_FILE, SOCIAL_MEDIA_FILE
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Global variables for caching
cached_data = {
    "rumors": [],
    "posts": []
}
last_scrape_time = None
scraping_in_progress = False

# Initialize scrapers
# news_scraper = ArsenalNewsScraper()


def load_cached_data():
    """Load data from JSON files into memory."""
    global cached_data, last_scrape_time
    
    # Load rumors
    try:
        if os.path.exists(RUMORS_FILE):
            with open(RUMORS_FILE, 'r', encoding='utf-8') as f:
                rumor_data = json.load(f)
                cached_data["rumors"] = rumor_data.get('rumors', [])
                last_scrape_time = rumor_data.get('last_updated')
                logger.info(f"Loaded {len(cached_data['rumors'])} cached rumors.")
    except Exception as e:
        logger.error(f"Error loading rumors cache: {e}")

    # Load social media posts
    try:
        if os.path.exists(SOCIAL_MEDIA_FILE):
            with open(SOCIAL_MEDIA_FILE, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
                cached_data["posts"] = post_data.get('posts', [])
                logger.info(f"Loaded {len(cached_data['posts'])} cached social posts.")
    except Exception as e:
        logger.error(f"Error loading social media cache: {e}")


def should_refresh_data() -> bool:
    """Check if data should be refreshed based on age"""
    if not last_scrape_time:
        return True
    
    try:
        last_update = datetime.fromisoformat(last_scrape_time.replace('Z', '+00:00'))
        time_diff = datetime.now(timezone.utc) - last_update
        return time_diff > timedelta(minutes=15)  # Refresh every 15 minutes
    except:
        return True


def trigger_scraping():
    """Run the scrapers in a background thread."""
    global scraping_in_progress
    if scraping_in_progress:
        logger.warning("Scraping is already in progress.")
        return

    def scraping_task():
        global scraping_in_progress, last_scrape_time
        logger.info("Starting background scraping task...")
        scraping_in_progress = True
        try:
            run_all_scrapers()
            load_cached_data() # Reload data after scraping
            last_scrape_time = datetime.now().isoformat()
        except Exception as e:
            logger.error(f"An error occurred during scraping task: {e}")
        finally:
            scraping_in_progress = False
            logger.info("Background scraping task finished.")

    thread = Thread(target=scraping_task)
    thread.start()


# API Routes

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/rumors', methods=['GET'])
def get_rumors():
    """Get all Arsenal transfer rumors and social media posts (Arsenal only)."""
    try:
        # Arsenal filter function
        def is_arsenal_related(item):
            title = item.get('title', '').lower()
            content = item.get('content', '').lower()
            source = (item.get('source', '') or '').lower()
            arsenal_sources = ['sky sports', 'the athletic', 'bbc sport', 'arsenal.com', 'espn']
            if 'arsenal' in title or '#afc' in title or 'arsenal' in content or '#afc' in content:
                return True
            for s in arsenal_sources:
                if s in source:
                    return True
            return False
        def is_arsenal_tweet(item):
            return 'arsenal' in item.get('content', '').lower() or '#afc' in item.get('content', '').lower()

        # Add type and filter rumors
        rumors = [dict(item, type='rumor') for item in cached_data["rumors"] if is_arsenal_related(item)]
        tweets = [dict(item, type='tweet') for item in cached_data["posts"] if is_arsenal_tweet(item)]
        all_items = rumors + tweets
        # Sort newest first
        all_items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({
            'status': 'success',
            'data': all_items,
            'last_updated': last_scrape_time,
            'scraping_status': 'in_progress' if scraping_in_progress else 'idle'
        })
    except Exception as e:
        logger.error(f"Error in /api/rumors: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/api/rumors/latest', methods=['GET'])
def get_latest_rumors():
    """Get latest transfer rumors"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limited_rumors = cached_data["rumors"][:limit]
        
        return jsonify({
            'success': True,
            'data': limited_rumors,
            'total': len(limited_rumors),
            'last_updated': last_scrape_time
        })
    except Exception as e:
        logger.error(f"Error in get_latest_rumors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/rumors/filter', methods=['GET'])
def filter_rumors():
    """Filter rumors by various criteria"""
    try:
        # Get filter parameters
        rumor_type = request.args.get('type')
        position = request.args.get('position')
        source = request.args.get('source')
        min_reliability = request.args.get('min_reliability', type=int)
        player_name = request.args.get('player')
        
        filtered_rumors = cached_data["rumors"].copy()
        
        # Apply filters
        if rumor_type:
            filtered_rumors = [r for r in filtered_rumors if r.get('rumor_type') == rumor_type]
        
        if position:
            filtered_rumors = [r for r in filtered_rumors if r.get('position', '').lower() == position.lower()]
        
        if source:
            filtered_rumors = [r for r in filtered_rumors if source.lower() in r.get('source', '').lower()]
        
        if min_reliability:
            filtered_rumors = [r for r in filtered_rumors if r.get('reliability_score', 0) >= min_reliability]
        
        if player_name:
            filtered_rumors = [r for r in filtered_rumors if player_name.lower() in r.get('player_name', '').lower()]
        
        return jsonify({
            'success': True,
            'data': filtered_rumors,
            'total': len(filtered_rumors),
            'filters_applied': {
                'type': rumor_type,
                'position': position,
                'source': source,
                'min_reliability': min_reliability,
                'player': player_name
            }
        })
        
    except Exception as e:
        logger.error(f"Error in filter_rumors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/social', methods=['GET'])
def get_social_media():
    """Get social media posts"""
    try:
        limit = request.args.get('limit', 20, type=int)
        limited_posts = cached_data["posts"][:limit]
        
        return jsonify({
            'success': True,
            'data': limited_posts,
            'total': len(limited_posts),
            'last_updated': last_scrape_time
        })
    except Exception as e:
        logger.error(f"Error in get_social_media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get various statistics about the data"""
    try:
        stats = {
            'total_rumors': len(cached_data["rumors"]),
            'total_social_posts': len(cached_data["posts"]),
            'last_updated': last_scrape_time,
            'scraping_status': 'in_progress' if scraping_in_progress else 'idle',
            'rumors_by_type': {},
            'rumors_by_source': {},
            'rumors_by_position': {},
            'average_reliability': 0
        }
        
        if cached_data["rumors"]:
            # Calculate distributions
            for rumor in cached_data["rumors"]:
                # By type
                rumor_type = rumor.get('rumor_type', 'unknown')
                stats['rumors_by_type'][rumor_type] = stats['rumors_by_type'].get(rumor_type, 0) + 1
                
                # By source
                source = rumor.get('source', 'unknown')
                stats['rumors_by_source'][source] = stats['rumors_by_source'].get(source, 0) + 1
                
                # By position
                position = rumor.get('position', 'unknown')
                if position:
                    stats['rumors_by_position'][position] = stats['rumors_by_position'].get(position, 0) + 1
            
            # Calculate average reliability
            reliabilities = [r.get('reliability_score', 0) for r in cached_data["rumors"]]
            stats['average_reliability'] = sum(reliabilities) / len(reliabilities) if reliabilities else 0
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/refresh', methods=['POST'])
def force_refresh():
    """Endpoint to manually trigger a data refresh."""
    if scraping_in_progress:
        return jsonify({
            'status': 'error',
            'message': 'Scraping already in progress.'
        }), 429 # Too Many Requests

    trigger_scraping()
    return jsonify({
        'status': 'success',
        'message': 'Scraping process initiated. Data will be updated shortly.'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'Please check the API documentation at /'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'Please try again later'
    }), 500


@app.errorhandler(429)
def rate_limit_error(error):
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': 'Too many requests, please try again later'
    }), 429


# Application startup

def initialize_app():
    """Initializes the application state."""
    os.makedirs(os.path.dirname(RUMORS_FILE), exist_ok=True)
    load_cached_data()
    if not cached_data["rumors"]:
        logger.info("No cached data found. Triggering initial scrape.")
        trigger_scraping()


if __name__ == '__main__':
    # Initialize the app
    initialize_app()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Arsenal Transfer API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
