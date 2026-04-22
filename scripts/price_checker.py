from db_manager import get_active_products, get_latest_price, add_price, add_notification
from site_parser import safe_get, extract_data_from_html
from notifier import send_price_alert

ALERT_EMAIL = "price.monitor.agent.hc@gmail.com"

def run_price_check_with_detection():
    products = get_active_products()

    for product in products:
        product_id = product["product_id"]
        product_name = product["product_name"]
        product_url = product["product_url"]

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

        old_price = old_price_row["price"] if old_price_row else None

        add_price(product_id, new_price, currency, source)

        if old_price is None:
            print(f"Initial price stored for {product_name}: {new_price}")
        elif new_price != old_price:
            change = new_price - old_price
            pct_change = (change / old_price) * 100 if old_price else 0
            direction = "increase" if change > 0 else "decrease"

            print(f"Price change detected for {product_name}: {old_price} -> {new_price}")

            subject = f"Price {direction} detected for {product_name}"
            body = (
                f"Product: {product_name}\n"
                f"Old Price: {old_price} {currency}\n"
                f"New Price: {new_price} {currency}\n"
                f"Change: {change:.2f} ({pct_change:.2f}%)\n"
                f"URL: {product_url}\n"
            )

            send_price_alert(
                to_email=ALERT_EMAIL,
                subject=subject,
                body=body
            )

            add_notification(
                product_id=product_id,
                old_price=old_price,
                new_price=new_price,
                percentage_change=pct_change,
                recipient_email=ALERT_EMAIL,
                subject=subject,
                body=body
            )
        else:
            print(f"No price change for {product_name}: {new_price}")

if __name__ == "__main__":
    run_price_check_with_detection()