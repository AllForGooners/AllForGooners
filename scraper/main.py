import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client
import openai
from datetime import datetime
import time

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

def scrape_arsenal_news():
    """Scrape news from multiple Arsenal sources"""
    
    sources = [
        {
            'name': 'Arsenal.com',
            'url': 'https://www.arsenal.com/news',
            'selector': 'article.card'  # Adjust based on actual HTML structure
        },
        {
            'name': 'BBC Arsenal',
            'url': 'https://www.bbc.com/sport/football/teams/arsenal',
            'selector': 'div.gel-layout__item'
        }
    ]
    
    articles = []
    
    for source in sources:
        try:
            print(f"Scraping {source['name']}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(source['url'], headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article elements (you'll need to adjust selectors for each site)
            article_elements = soup.select(source['selector'])[:5]  # Get top 5 articles
            
            for element in article_elements:
                try:
                    # Extract title and URL (adjust selectors based on site structure)
                    title_elem = element.find('h2') or element.find('h3') or element.find('a')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Get URL
                    link_elem = element.find('a')
                    if not link_elem:
                        continue
                        
                    url = link_elem.get('href')
                    if url.startswith('/'):
                        # Relative URL, make it absolute
                        base_url = '/'.join(source['url'].split('/')[:3])
                        url = base_url + url
                    
                    # Skip if we already have this article
                    existing = supabase.table('articles').select('id').eq('url', url).execute()
                    if existing.data:
                        print(f"Article already exists: {title[:50]}...")
                        continue
                    
                    # Get article content
                    content = scrape_article_content(url)
                    
                    if content and len(content) > 100:  # Only process substantial articles
                        articles.append({
                            'title': title,
                            'url': url,
                            'content': content,
                            'source': source['name'],
                            'published_date': datetime.now().isoformat()
                        })
                        
                        print(f"Found new article: {title[:50]}...")
                        
                except Exception as e:
                    print(f"Error processing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping {source['name']}: {e}")
            continue
    
    return articles

def scrape_article_content(url):
    """Scrape the full content of an article"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Try to find main content (adjust selectors as needed)
        content_selectors = [
            'article',
            '.article-content',
            '.content',
            'main',
            '.post-content'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True, separator=' ')
                break
        
        # Fallback: get all paragraph text
        if not content:
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Clean up content
        content = ' '.join(content.split())  # Remove extra whitespace
        
        return content[:2000]  # Limit content length
        
    except Exception as e:
        print(f"Error scraping article content from {url}: {e}")
        return ""

def generate_summary(content, title):
    """Generate AI summary of the article"""
    try:
        prompt = f"""
        Please write a concise 2-3 sentence summary of this Arsenal news article.
        Focus on the key facts and main points.
        
        Title: {title}
        
        Content: {content[:1500]}  # Limit content to avoid token limits
        
        Summary:
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a football news summarizer. Write clear, concise summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Summary unavailable."

def save_articles(articles):
    """Save articles to Supabase database"""
    for article in articles:
        try:
            # Generate summary
            print(f"Generating summary for: {article['title'][:50]}...")
            article['summary'] = generate_summary(article['content'], article['title'])
            
            # Save to database
            result = supabase.table('articles').insert(article).execute()
            
            if result.data:
                print(f"✅ Saved: {article['title'][:50]}...")
            else:
                print(f"❌ Failed to save: {article['title'][:50]}...")
                
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error saving article '{article['title'][:50]}...': {e}")

def main():
    """Main function to run the scraper"""
    print("🚀 Starting Arsenal news scraper...")
    
    # Check if environment variables are set
    if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
        print("❌ Missing environment variables!")
        return
    
    try:
        # Scrape articles
        articles = scrape_arsenal_news()
        
        if articles:
            print(f"📰 Found {len(articles)} new articles")
            
            # Save articles with summaries
            save_articles(articles)
            
            print("✅ Scraping completed successfully!")
        else:
            print("📭 No new articles found")
            
    except Exception as e:
        print(f"❌ Error in main execution: {e}")

if __name__ == "__main__":
    main()
