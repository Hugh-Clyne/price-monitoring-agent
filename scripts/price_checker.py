from db_manager import get_active_products, get_latest_price, add_price
from site_parser import safe_get, extract_data_from_html
from notifier import send_price_alert

def run_price_check_with_detection():
    products = get_active_products()
    for product_id, company_id, product_name, product_url in products:
        old_price_row = get_latest_price(product_id)

        response = safe_get(product_url)

        if not response:
            print(f"Request failed for {product_name}")
            continue

        product_data = extract_data_from_html(response.text)
        if not product_data or product_data.get("price") is None:
            print(f"No price found for {product_name}")
            continue

        new_price = product_data["price"]
        currency = product_data.get("currency")
        source = product_data.get("source")

        old_price = old_price_row[0] if old_price_row else None
        
        add_price(product_id, new_price, currency, source)

        if old_price is None:
            print(f"Initial price stored for {product_name}: {new_price}")
        elif new_price != old_price:
            change = new_price - old_price
            pct_change = (change/old_price) * 100 if old_price else 0
            print(f"Price change detected for {product_name}: {old_price} -> {new_price}")

            subject = f"Price change detected for {product_name}"
            body = (
                f"Product: {product_name}\n"
                f"Old Price: {old_price} {currency}\n"
                f"New Price: {new_price} {currency}\n"
                f"Change: {change:.2f} ({pct_change:.2f}%)\n"
                f"URL: {product_url}\n"
            )
            send_price_alert(to_email="price.monitor.agent.hc@gmail.com", subject=subject, body=body)
        else:
            print(f"No price change for {product_name}: {new_price}")

if __name__ == "__main__":
    run_price_check_with_detection()
