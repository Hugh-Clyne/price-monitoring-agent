import os
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


#Dir paths
CURR_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(CURR_DIR, '..'))

#Helper Functions

def safe_get(url):
    """
    Helper function to perform a GET request with error handling and timeouts.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=(3, 5))
        return response
    except requests.Timeout:
        print(f"Timeout while fetching: {url}")
        return None
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return None

def is_valid_url(url):
    """
    Validates if the provided URL is a well-formed HTTP or HTTPS URL.
    """
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        return True, clean_url
    return False, None

def shopify_check_from_html(html):
    html = html.lower()
    return 'cdn.shopify.com' in html or 'shopify.theme' in html

def extract_data_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    script_tags = soup.find_all('script', type='application/ld+json')

    for tag in script_tags:
        try:
            if not tag.string:
                continue

            data = json.loads(tag.string)

            items = data if isinstance(data, list) else [data]

            for item in items:
                if not isinstance(item, dict):
                    continue

                item_type = item.get('@type')

                if item_type == 'Product':
                    offers = item.get('offers', {})

                    if isinstance(offers, list) and offers:
                        offers = offers[0]

                    if isinstance(offers, dict):
                        price = offers.get('price')
                        currency = offers.get('priceCurrency')

                        if price and currency:
                            return {
                                "price": float(price),
                                "currency": currency.upper(),
                                "source": "json_ld"
                            }

                elif item_type == 'ProductGroup':
                    variants = item.get('hasVariant', [])

                    if isinstance(variants, dict):
                        variants = [variants]

                    for variant in variants:
                        offers = variant.get('offers', {})

                        if isinstance(offers, list) and offers:
                            offers = offers[0]

                        if isinstance(offers, dict):
                            price = offers.get('price')
                            currency = offers.get('priceCurrency')

                            if price and currency:
                                return {
                                    "price": float(price),
                                    "currency": currency.upper(),
                                    "source": "json_ld"
                                }

        except Exception as e:
            print(f"JSON-LD parse error: {e}")

    # Meta fallback
    meta_price = (
        soup.find('meta', property='og:price:amount') or
        soup.find('meta', property='product:price:amount')
    )
    meta_currency = (
        soup.find('meta', property='og:price:currency') or
        soup.find('meta', property='product:price:currency')
    )

    if meta_price and meta_currency:
        try:
            raw_price = meta_price.get("content", "").replace("$", "").replace(",", "").strip()
            raw_currency = meta_currency.get("content", "").strip().upper()

            return {
                "price": float(raw_price),
                "currency": raw_currency,
                "source": "meta_tag"
            }
        
        except (TypeError, ValueError):
            pass

    # Debug
    print("No product price found.")

    print("\n--- META TAGS ---")
    for meta in soup.find_all("meta"):
        prop = meta.get("property")
        name = meta.get("name")
        content = meta.get("content")

        if prop or name:
            if any(x in str(prop).lower() for x in ["price", "product"]) or \
               any(x in str(name).lower() for x in ["price", "product"]):
                print("property:", prop, "| name:", name, "| content:", content)

    print("\n--- JSON-LD TAGS ---")
    for i, tag in enumerate(script_tags):
        if tag.string:
            print(f"\nTAG {i+1}:")
            print(tag.string[:500])

    return None

#Testing
   
