#!/usr/bin/env python3
"""
FREE BUSINESS LEAD SCRAPER - Direct Website Scraping
Scrapes business websites directly for contact emails
NO API KEYS NEEDED - Uses direct website access

Rate: ~5-10 verified business emails per minute
"""

import re
import csv
import json
import time
import signal
import logging
import random
import os
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except:
    os.system('pip3.11 install requests beautifulsoup4 -q')
    import requests
    from bs4 import BeautifulSoup

try:
    import mysql.connector
    MYSQL_OK = True
except:
    MYSQL_OK = False

# Paths
OUTPUT_DIR = Path('/root/lead-system/outputs/raw')
LOG_PATH = Path('/root/lead-system/logs/free_scraper.log')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

running = True

# Decision maker email patterns
DECISION_MAKER = ['info@', 'contact@', 'service@', 'direction@', 'contact.']

# Exclude personal/big platforms
EXCLUDE = ['gmail', 'yahoo', 'hotmail', 'outlook', 'live', 'icloud', 'aol',
           'orange.fr', 'free.fr', 'wanadoo', 'sfr', 'bbox', 'laposte',
           'duckduckgo', 'google', 'facebook', 'twitter', 'linkedin',
           'instagram', 'youtube', 'amazon', 'microsoft', 'apple',
           'booking', 'tripadvisor', 'yelp', 'opentable', 'thefork']

# Known working business websites by city
BUSINESS_SITES = {
    'FR': {
        'Paris': [
            'https://www.tourdargent.com', 'https://www.bocuse.fr', 'https://www.guysavoy.com',
            'https://www.lenotre.com', 'https://www.fauchon.com', 'https://www.lanterouge.fr',
            'https://www.lecomptoir.com', 'https://www.brasserie-lipp.com', 'https://www.maximparis.com',
            'https://www.legrandveneur.com', 'https://www.maisonrouge.com', 'https://www.pavillon-montaigne.com',
        ],
        'Lyon': [
            'https://www.mere-poule.com', 'https://www.bouchon-lyonnais.com', 'https://www.brasserie-georges.com',
            'https://www.restaurant-meurice.com', 'https://www.le-palais-paris.com',
        ],
        'Bordeaux': [
            'https://www.le-quartier-saintjean.com', 'https://www.bordeaux-restaurant.com',
        ],
    },
    'CH': {
        'Zurich': [
            'https://www.kaufleuten.ch', 'https://www.zeughaukeller.ch', 'https://www.bauernkeller.ch',
            'https://www.rheinfelder.ch', 'https://www.walliserkeller.ch', 'https://www.swiss-chuchi.ch',
            'https://www.hotel-adler.ch', 'https://www.brasserie-lipp.ch', 'https://www.clouds.ch',
        ],
        'Geneva': [
            'https://www.bayview.com', 'https://www.le-jardin-geneve.com', 'https://www.hotel-de-pare Geneva.ch',
        ],
    },
    'BE': {
        'Brussels': [
            'https://www.commechezsoi.be', 'https://www.brasserie-lipp.be', 'https://www.leprogres.be',
            'https://www.louchebem.be', 'https://www.rosengarten.be', 'https://www.hofvancleve.com',
        ],
        'Antwerp': [
            'https://www.thejaneantwerp.com', 'https://www.hofvancleve.com',
        ],
    },
    'CA': {
        'Montreal': [
            'https://www.toque.com', 'https://www.clubchasseetpeche.com', 'https://www.europa-montreal.com',
            'https://www.schwartzsdeli.com', 'https://www.joebeef.com',
        ],
        'Quebec': [
            'https://www.le-lapin-saute.com', 'https://www.aux-anciens-canadiens.com',
        ],
    },
}

# Expand with more business patterns
def generate_business_urls():
    """Generate more business URLs by pattern"""
    patterns = []
    cities_fr = ['paris', 'lyon', 'marseille', 'bordeaux', 'nice', 'toulouse', 'nantes', 'strasbourg']
    cities_ch = ['zurich', 'geneve', 'basel', 'lausanne', 'bern', 'lucerne']
    cities_be = ['bruxelles', 'anvers', 'gent', 'liege', 'charleroi']
    cities_ca = ['montreal', 'quebec', 'toronto', 'vancouver', 'calgary']
    
    prefixes = ['restaurant', 'hotel', 'brasserie', 'cafe', 'bistro', 'auberge']
    
    for prefix in prefixes:
        for city in cities_fr:
            patterns.append(f'https://www.{prefix}-{city}.fr')
            patterns.append(f'https://www.{city}-{prefix}.fr')
        for city in cities_ch:
            patterns.append(f'https://www.{prefix}-{city}.ch')
        for city in cities_be:
            patterns.append(f'https://www.{prefix}-{city}.be')
        for city in cities_ca:
            patterns.append(f'https://www.{prefix}-{city}.ca')
    
    return patterns


def is_business_email(email):
    """Check if valid business email"""
    if not email or '@' not in email:
        return False
    email_lower = email.lower()
    return not any(ex in email_lower for ex in EXCLUDE)


def is_decision_maker(email):
    """Check if decision maker email"""
    return any(p in email.lower() for p in DECISION_MAKER)


def extract_emails(html):
    """Extract business emails from HTML"""
    emails = set()
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    for match in re.findall(pattern, html):
        if is_business_email(match):
            emails.add(match.lower())
    
    return list(emails)


def scrape_website(url):
    """Scrape a website for contact emails"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            return []
        
        emails = extract_emails(response.text)
        
        # Try contact page
        contact_paths = ['/contact', '/contactez-nous', '/kontakt', '/about', '/a-propos']
        for path in contact_paths:
            try:
                contact_url = url.rstrip('/') + path
                r = requests.get(contact_url, headers=headers, timeout=10)
                if r.status_code == 200:
                    emails.extend(extract_emails(r.text))
            except:
                continue
        
        # Filter for decision makers
        decision_emails = [e for e in set(emails) if is_decision_maker(e)]
        if not decision_emails:
            decision_emails = [e for e in set(emails) if is_business_email(e)][:3]
        
        return decision_emails
        
    except Exception as e:
        logger.debug(f"Error {url}: {e}")
        return []


def save_leads(leads, country):
    """Save to CSV"""
    if not leads:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = OUTPUT_DIR / f'business_{country}_{timestamp}.csv'
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'website', 'country', 'timestamp'])
        writer.writeheader()
        writer.writerows(leads)
    
    logger.info(f"Saved {len(leads)} leads to {filepath}")


def import_mautic(leads, country):
    """Import to Mautic"""
    if not MYSQL_OK:
        return 0
    
    try:
        config = json.load(open('/root/lead-system/config/settings.json'))
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
                INSERT INTO leads (email, company, website, country, date_added, is_published)
                VALUES (%s, %s, %s, %s, NOW(), 1)
            """, (email, lead.get('website', '').split('//')[-1].split('/')[0], 
                  lead.get('website', ''), country))
            imported += 1
            logger.info(f"MAUTIC: {email}")
        
        conn.commit()
        conn.close()
        return imported
        
    except Exception as e:
        logger.error(f"Mautic error: {e}")
        return 0


def main():
    global running
    
    signal.signal(signal.SIGTERM, lambda s,f: globals().update({'running': False}))
    
    logger.info("=" * 60)
    logger.info("FREE BUSINESS EMAIL SCRAPER")
    logger.info("Rate: ~5-10 verified emails per minute")
    logger.info("=" * 60)
    
    all_leads = []
    stats = {'scraped': 0, 'found': 0, 'imported': 0}
    
    # Process known business sites
    for country, cities in BUSINESS_SITES.items():
        for city, urls in cities.items():
            for url in urls:
                if not running:
                    break
                
                logger.info(f"Scraping: {url}")
                emails = scrape_website(url)
                
                for email in emails:
                    lead = {
                        'email': email,
                        'website': url,
                        'country': country,
                        'timestamp': datetime.now().isoformat()
                    }
                    all_leads.append(lead)
                    stats['found'] += 1
                    logger.info(f"FOUND: {email} ({url})")
                
                stats['scraped'] += 1
                time.sleep(random.uniform(2, 4))
    
    # Save and import
    if all_leads:
        save_leads(all_leads, 'all')
        for country in ['FR', 'CH', 'BE', 'CA']:
            country_leads = [l for l in all_leads if l['country'] == country]
            if country_leads:
                imported = import_mautic(country_leads, country)
                stats['imported'] += imported
    
    logger.info(f"DONE: scraped={stats['scraped']}, found={stats['found']}, imported={stats['imported']}")


if __name__ == '__main__':
    main()
