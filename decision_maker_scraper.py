#!/usr/bin/env python3
"""
DECISION MAKER EMAIL SCRAPER
Finds executives, owners, managers from businesses
Uses Scout for social media + website scraping for contact pages
Targets: CEO, Owner, Manager, Director, Founder emails
"""

import re
import csv
import json
import time
import signal
import logging
import random
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except:
    os.system('pip3.11 install requests beautifulsoup4 -q')
    import requests
    from bs4 import BeautifulSoup

# Paths
OUTPUT_DIR = Path('/root/lead-system/outputs/decision_makers')
LOG_PATH = Path('/root/lead-system/logs/decision_maker_scraper.log')
SCOUT_PATH = Path('/root/scout-tool')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

running = True

# Decision maker titles to search
DECISION_MAKER_TITLES = [
    'ceo', 'owner', 'founder', 'director', 'manager', 'gerant', 'patron',
    'president', 'chef', 'head', 'principal', 'proprietor', 'partner',
    'executive', 'general manager', 'managing director'
]

# Decision maker email patterns
DECISION_MAKER_PATTERNS = [
    'ceo@', 'owner@', 'founder@', 'director@', 'manager@', 'gerant@',
    'patron@', 'president@', 'chef@', 'head@', 'office@', 'direction@',
    'contact@', 'info@', 'service@', 'reception@', 'booking@'
]

# Exclude personal emails
EXCLUDE = [
    'gmail', 'yahoo', 'hotmail', 'outlook', 'live', 'icloud', 'aol',
    'orange.fr', 'free.fr', 'wanadoo', 'sfr', 'bbox', 'laposte',
    '.png', '.jpg', '.gif', '.svg', '.css', '.js'
]

# Business websites with known decision makers
BUSINESS_SITES = {
    'FR': [
        'https://www.tourdargent.com', 'https://www.bocuse.fr', 'https://www.guysavoy.com',
        'https://www.lenotre.com', 'https://www.fauchon.com', 'https://www.brasserie-lipp.com',
        'https://www.maximparis.com', 'https://www.mere-poule.com', 'https://www.pharamond.com',
        'https://www.bouillon-chartier.com', 'https://www.les-deux-magots.com',
        'https://www.cafe-de-flore.com', 'https://www.aux-lyonnais.com',
        'https://www.restaurant-saint-regis.com', 'https://www.la-coupe-dor.com',
    ],
    'CH': [
        'https://www.kaufleuten.ch', 'https://www.zeughauskeller.ch',
        'https://www.swiss-chuchi.ch', 'https://www.hotel-adler.ch',
        'https://www.clouds.ch', 'https://www.walliserkanne.ch',
        'https://www.bauraulac.ch', 'https://www.parkhuus.ch',
        'https://www.hotel-storchen.ch', 'https://www.savoy-baurhenne.ch',
    ],
    'BE': [
        'https://www.commechezsoi.be', 'https://www.hofvancleve.com',
        'https://www.thejaneantwerp.com', 'https://www.louchebem.be',
        'https://www.rosengarten.be', 'https://www.leprogres.be',
        'https://www.aux-armes-de-bruxelles.be', 'https://www.brasserie-leon.be',
    ],
    'CA': [
        'https://www.toque.com', 'https://www.clubchasseetpeche.com',
        'https://www.europa-montreal.com', 'https://www.joebeef.com',
        'https://www.schwartzsdeli.com', 'https://www.maison-boulud.com',
        'https://www.monarque.ca', 'https://www.lemoulin.ca',
    ],
}


def signal_handler(sig, frame):
    global running
    running = False
    logger.info("Shutdown signal received")


def is_business_email(email):
    """Check if valid business email"""
    if not email or '@' not in email:
        return False
    email_lower = email.lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    return not any(ex in email_lower for ex in EXCLUDE)


def is_decision_maker_email(email):
    """Check if decision maker email pattern"""
    email_lower = email.lower()
    return any(p in email_lower for p in DECISION_MAKER_PATTERNS)


def extract_emails_from_page(html, url):
    """Extract business emails from page"""
    emails = set()
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    for match in re.findall(pattern, html):
        if is_business_email(match):
            emails.add(match.lower())
    
    # Find emails in mailto links
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        if 'mailto:' in a['href'].lower():
            email = a['href'].replace('mailto:', '').split('?')[0]
            if is_business_email(email):
                emails.add(email.lower())
    
    return list(emails)


def find_team_page(base_url):
    """Find team/about/staff pages"""
    paths = ['/team', '/about', '/about-us', '/a-propos', '/equipe', '/staff',
             '/management', '/leadership', '/founders', '/who-we-are',
             '/our-team', '/notre-equipe', '/kontakte', '/uber-uns']
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for path in paths:
        try:
            url = base_url.rstrip('/') + path
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return url, response.text
        except:
            continue
    
    return None, None


def scrape_for_decision_makers(url):
    """Scrape website for decision maker emails"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    all_emails = []
    
    try:
        # Scrape main page
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            emails = extract_emails_from_page(response.text, url)
            all_emails.extend(emails)
        
        # Find team/about pages
        team_url, team_html = find_team_page(url)
        if team_html:
            emails = extract_emails_from_page(team_html, team_url)
            all_emails.extend(emails)
            logger.info(f"Found team page: {team_url}")
        
        # Scrape contact page
        for path in ['/contact', '/contactez-nous', '/kontakt']:
            try:
                contact_url = url.rstrip('/') + path
                r = requests.get(contact_url, headers=headers, timeout=10)
                if r.status_code == 200:
                    emails = extract_emails_from_page(r.text, contact_url)
                    all_emails.extend(emails)
            except:
                continue
        
        # Filter for decision maker emails
        decision_emails = [e for e in set(all_emails) if is_decision_maker_email(e)]
        
        # If no decision maker emails, return all business emails with names
        if not decision_emails:
            decision_emails = list(set(all_emails))[:5]
        
        return decision_emails
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return []


def run_scout_scraper(platform, query):
    """Run Scout scraper for social media"""
    try:
        os.chdir(SCOUT_PATH)
        env = os.environ.copy()
        env['PYTHONPATH'] = str(SCOUT_PATH)
        
        # Run Scout CLI
        result = subprocess.run(
            ['python3.11', 'scout.py', '--platform', platform, '--query', query],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            cwd=str(SCOUT_PATH)
        )
        
        # Parse output for emails
        emails = []
        for line in result.stdout.split('\n'):
            if '@' in line and '.' in line:
                matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                for m in matches:
                    if is_business_email(m):
                        emails.append(m.lower())
        
        return emails
        
    except Exception as e:
        logger.error(f"Scout error: {e}")
        return []


def save_lead(email, source, country, company=''):
    """Save to CSV"""
    filepath = OUTPUT_DIR / f'decision_makers_{datetime.now().strftime("%Y%m%d")}.csv'
    
    file_exists = filepath.exists()
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['email', 'company', 'source', 'country', 'timestamp'])
        writer.writerow([email, company, source, country, datetime.now().isoformat()])
    
    logger.info(f"SAVED: {email} ({source})")


def main():
    global running
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    logger.info("DECISION MAKER EMAIL SCRAPER")
    logger.info("Targets: CEO, Owner, Director, Manager emails")
    logger.info("=" * 60)
    
    stats = {'scraped': 0, 'found': 0}
    
    for country, urls in BUSINESS_SITES.items():
        if not running:
            break
        
        for url in urls:
            if not running:
                break
            
            logger.info(f"Scraping: {url}")
            
            # Scrape website for decision maker emails
            emails = scrape_for_decision_makers(url)
            stats['scraped'] += 1
            
            for email in emails:
                if is_decision_maker_email(email):
                    logger.info(f"DECISION MAKER: {email}")
                    save_lead(email, 'website', country, url)
                    stats['found'] += 1
                else:
                    logger.info(f"BUSINESS EMAIL: {email}")
                    save_lead(email, 'website', country, url)
                    stats['found'] += 1
            
            time.sleep(random.uniform(2, 4))
    
    logger.info("=" * 60)
    logger.info(f"DONE: scraped={stats['scraped']}, found={stats['found']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
