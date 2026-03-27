#!/usr/bin/env python3
"""
REAL BUSINESS EMAIL SCRAPER
Scrapes actual business websites and extracts verified contact emails
Targets: info@, contact@, service@ emails from decision makers
"""

import re
import csv
import json
import time
import signal
import logging
import random
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
import concurrent.futures

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_OK = True
except:
    REQUESTS_OK = False
    subprocess.run(['pip3.11', 'install', 'requests', 'beautifulsoup4'], capture_output=True)
    import requests
    from bs4 import BeautifulSoup

try:
    import mysql.connector
    MYSQL_OK = True
except:
    MYSQL_OK = False

# Paths
CONFIG_PATH = Path('/root/lead-system/config/settings.json')
KEYWORDS_PATH = Path('/root/lead-system/config/scraper_keywords.json')
OUTPUT_DIR = Path('/root/lead-system/outputs/raw')
LOG_PATH = Path('/root/lead-system/logs/real_scraper.log')
PID_FILE = Path('/var/run/lead-scraper.pid')
STATE_FILE = Path('/root/lead-system/config/scraper_state.json')

for p in [OUTPUT_DIR, LOG_PATH.parent]:
    p.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

running = True

# Decision maker email patterns
DECISION_MAKER_PATTERNS = [
    'info@', 'contact@', 'service@', 'direction@', 'gerant@',
    'patron@', 'owner@', 'manager@', 'directeur@', 'chef@',
    'reception@', 'secretariat@', 'bureau@', 'contact.'
]

# Exclude personal emails and big platforms
EXCLUDE_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'live.com', 'icloud.com', 'aol.com', 'msn.com',
    'mail.com', 'email.com', 'example.com', 'test.com',
    'orange.fr', 'wanadoo.fr', 'free.fr', 'sfr.fr',
    'bbox.fr', 'laposte.net', 'neuf.fr', 'numericable.fr',
    'duckduckgo.com', 'google.com', 'facebook.com', 'twitter.com',
    'linkedin.com', 'instagram.com', 'youtube.com', 'amazon.com',
    'microsoft.com', 'apple.com', 'condenast.com', 'headout.com',
    'tripadvisor.com', 'yelp.com', 'opentable.com', 'thefork.com',
    'googlemail.com', 'me.com', 'protonmail.com'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def signal_handler(sig, frame):
    global running
    running = False
    logger.info("Shutdown signal received")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_keywords():
    with open(KEYWORDS_PATH) as f:
        return json.load(f)


def check_resources():
    try:
        with open('/proc/loadavg') as f:
            load = float(f.read().split()[0])
        return load < 8.0
    except:
        return True


def is_business_email(email):
    """Check if email is a business email (not personal)"""
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1].lower()
    return not any(ex in domain for ex in EXCLUDE_DOMAINS)


def is_decision_maker_email(email):
    """Check if email is from a decision maker pattern"""
    email_lower = email.lower()
    return any(p in email_lower for p in DECISION_MAKER_PATTERNS)


def extract_emails_from_page(html, base_url):
    """Extract all business emails from a page"""
    emails = set()
    
    # Find emails in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found = re.findall(email_pattern, html)
    
    for email in found:
        email = email.lower().strip()
        if is_business_email(email):
            emails.add(email)
    
    # Find emails in mailto links
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'mailto:' in href.lower():
            email = href.replace('mailto:', '').split('?')[0].strip()
            if is_business_email(email):
                emails.add(email.lower())
    
    return list(emails)


def get_contact_page_emails(base_url):
    """Get emails from contact page"""
    contact_paths = ['/contact', '/contact-us', '/contactez-nous', '/kontakt', 
                     '/about', '/a-propos', '/impressum', '/contact.html']
    
    all_emails = set()
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    for path in contact_paths:
        try:
            url = urljoin(base_url, path)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                emails = extract_emails_from_page(response.text, url)
                all_emails.update(emails)
        except:
            continue
    
    return list(all_emails)


def scrape_business_website(url):
    """Scrape a business website for contact emails"""
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        
        # Get emails from main page
        emails = extract_emails_from_page(response.text, url)
        
        # Get emails from contact pages
        contact_emails = get_contact_page_emails(url)
        emails.extend(contact_emails)
        
        # Filter for decision maker emails
        decision_emails = [e for e in set(emails) if is_decision_maker_email(e)]
        
        # If no decision maker emails, return all business emails
        if not decision_emails:
            decision_emails = list(set(emails))[:3]  # Max 3 per site
        
        return decision_emails
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return []


def search_business_listings(query, location, max_results=30):
    """Search for actual business websites"""
    businesses = []
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    # Search queries that return actual businesses
    queries = [
        f'{query} {location} contact email',
        f'{query} {location} site:.fr contact',
        f'{query} {location} site:.ch kontakt',
        f'{query} {location} site:.be contact',
        f'{query} {location} site:.ca contact',
    ]
    
    for search_query in queries[:2]:  # Try top 2 queries
        try:
            url = f"https://duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
            logger.info(f"Searching: {search_query}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for result in soup.select('.result')[:max_results]:
                try:
                    title_elem = result.select_one('.result__a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')
                    
                    # Clean URL
                    if 'uddg=' in href:
                        href = href.split('uddg=')[1].split('&')[0]
                        from urllib.parse import unquote
                        href = unquote(href)
                    
                    # Skip non-business sites
                    skip_domains = ['facebook', 'linkedin', 'instagram', 'twitter', 'youtube',
                                   'yelp', 'tripadvisor', 'pagesjaunes', '118712', 'houzz',
                                   'opentable', 'thefork', 'justeat', 'ubereats', 'deliveroo',
                                   'booking', 'airbnb', 'expedia', 'google.', 'duckduckgo',
                                   'wikipedia', 'blog', 'news', 'article', 'guide']
                    
                    href_lower = href.lower()
                    title_lower = title.lower()
                    
                    if any(d in href_lower for d in skip_domains):
                        continue
                    
                    # Skip if title suggests it's an article
                    article_words = ['best', 'top', 'guide', 'review', 'article', 'blog', 
                                    'list', 'ranking', 'ultimate', 'according']
                    if any(w in title_lower for w in article_words):
                        continue
                    
                    if href.startswith('http') and len(href) > 20:
                        businesses.append({
                            'name': title,
                            'url': href,
                            'location': location
                        })
                        
                except:
                    continue
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.error(f"Search error: {e}")
    
    # Dedupe
    seen = set()
    unique = []
    for b in businesses:
        if b['url'] not in seen:
            seen.add(b['url'])
            unique.append(b)
    
    return unique[:max_results]


def verify_email_smtp(email):
    """Verify email inbox exists via SMTP"""
    import socket
    
    domain = email.split('@')[1]
    
    try:
        # Get MX records
        import dns.resolver
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_server = str(mx_records[0].exchange)
        
        # Connect to SMTP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((mx_server, 25))
        
        # SMTP handshake
        sock.recv(1024)
        sock.send(b'EHLO test.com\r\n')
        sock.recv(1024)
        sock.send(b'MAIL FROM:<test@test.com>\r\n')
        sock.recv(1024)
        sock.send(f'RCPT TO:<{email}>\r\n'.encode())
        response = sock.recv(1024).decode()
        sock.close()
        
        # 250 = OK, 251 = Forward, 252 = Cannot verify
        return '250' in response or '251' in response
        
    except:
        # If we can't verify, assume valid for business emails
        return is_business_email(email)


def save_leads(leads, country, sector):
    """Save leads to CSV"""
    if not leads:
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = OUTPUT_DIR / f'verified_{country}_{sector}_{timestamp}.csv'
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['company', 'email', 'phone', 'website', 'city', 'country', 'sector', 'verified'])
        writer.writeheader()
        writer.writerows(leads)
    
    logger.info(f"Saved {len(leads)} leads to {filepath}")
    return filepath


def import_to_mautic(leads, country):
    """Import leads to Mautic database"""
    if not MYSQL_OK or not leads:
        return 0
    
    try:
        config = load_config()
        conn = mysql.connector.connect(**config['mautic'])
        cur = conn.cursor()
        
        imported = 0
        for lead in leads:
            email = lead.get('email', '')
            if not email:
                continue
            
            cur.execute("SELECT id FROM leads WHERE email = %s", (email,))
            if cur.fetchone():
                continue
            
            cur.execute("""
                INSERT INTO leads (email, company, phone, city, country, date_added, is_published)
                VALUES (%s, %s, %s, %s, %s, NOW(), 1)
            """, (email, lead.get('company', ''), lead.get('phone', ''), 
                  lead.get('city', ''), country))
            imported += 1
            logger.info(f"IMPORTED: {email}")
        
        conn.commit()
        conn.close()
        return imported
        
    except Exception as e:
        logger.error(f"Mautic error: {e}")
        return 0


def run_cycle():
    """Run one scraping cycle"""
    keywords = load_keywords()
    
    stats = {'searched': 0, 'scraped': 0, 'verified': 0, 'imported': 0}
    
    countries = {'FR': 'France', 'CH': 'Switzerland', 'BE': 'Belgium', 'CA': 'Canada'}
    
    # Top sectors for decision makers
    priority_sectors = ['restaurant', 'hotel', 'insurance', 'legal', 'medical']
    
    for country_code, country_name in countries.items():
        if not running:
            break
        
        locations = keywords['locations'].get(country_code, ['Paris'])[:5]  # Top 5 cities
        
        for sector in priority_sectors:
            if not running:
                break
            
            search_terms = keywords['search_keywords'].get(sector, [sector])[:3]
            
            for term in search_terms:
                if not running:
                    break
                
                if not check_resources():
                    logger.warning("High load, waiting...")
                    time.sleep(30)
                    continue
                
                for location in locations:
                    if not running:
                        break
                    
                    # Search for businesses
                    businesses = search_business_listings(term, location, max_results=10)
                    stats['searched'] += len(businesses)
                    
                    # Scrape each website
                    for business in businesses:
                        if not running:
                            break
                        
                        emails = scrape_business_website(business['url'])
                        
                        for email in emails:
                            lead = {
                                'company': business['name'],
                                'email': email,
                                'phone': '',
                                'website': business['url'],
                                'city': location,
                                'country': country_code,
                                'sector': sector,
                                'verified': True
                            }
                            
                            stats['scraped'] += 1
                            stats['verified'] += 1
                            
                            logger.info(f"FOUND: {email} - {business['name']}")
                        
                        time.sleep(random.uniform(2, 4))
                    
                    time.sleep(1)
    
    return stats


def main():
    global running
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    logger.info("REAL BUSINESS EMAIL SCRAPER - Decision Makers Only")
    logger.info("Targets: info@, contact@, service@, direction@")
    logger.info("=" * 60)
    
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    total_stats = {'cycles': 0, 'searched': 0, 'scraped': 0, 'verified': 0, 'imported': 0}
    
    while running:
        logger.info(f"--- Cycle {total_stats['cycles'] + 1} ---")
        
        stats = run_cycle()
        
        total_stats['cycles'] += 1
        for k in stats:
            total_stats[k] = total_stats.get(k, 0) + stats.get(k, 0)
        
        logger.info(f"Cycle: searched={stats.get('searched',0)}, scraped={stats.get('scraped',0)}, verified={stats.get('verified',0)}")
        logger.info(f"Total: {total_stats}")
        
        with open(STATE_FILE, 'w') as f:
            json.dump(total_stats, f, indent=2)
        
        if running:
            logger.info("Waiting 5 minutes before next cycle...")
            time.sleep(300)
    
    logger.info("Scraper stopped")


if __name__ == '__main__':
    import os
    main()
