from datetime import datetime, timedelta
from agent_layer import generate_price_insight

from db_manager import (
    get_active_products,
    get_latest_price,
    add_price,
    add_notification,
    get_all_monitoring_settings,
    update_last_checked,
)
from site_parser import safe_get, extract_data_from_html
from notifier import send_price_alert


def compute_next_check(frequency):
    """
    Returns the next scheduled check time based on frequency.
    """
    now = datetime.now()

    if frequency == "Daily":
        return now + timedelta(days=1)
    if frequency == "Weekly":
        return now + timedelta(weeks=1)
    if frequency == "Monthly":
        return now + timedelta(days=30)

    return now + timedelta(days=1)


def run_price_check_with_detection():
    products = get_active_products()
    settings_map = get_all_monitoring_settings()

    for product in products:
        product_id = product["product_id"]
        product_name = product["product_name"]
        product_url = product["product_url"]

        settings = settings_map.get(product_id)

        if not settings:
            print(f"[SKIP] No monitoring settings found for {product_name}")
            continue

        alert_email = settings["alert_email"]
        threshold = settings["alert_threshold_pct"]
        frequency = settings["check_frequency"]
        next_check = settings["next_check_at"]

        if next_check:
            try:
                next_check_dt = datetime.fromisoformat(next_check)
                if next_check_dt > datetime.now():
                    print(f"[SKIP] Not due yet for {product_name}")
                    continue
            except ValueError:
                print(f"[WARN] Invalid next_check_at for {product_name}, continuing.")

        old_price_row = get_latest_price(product_id)

        response = safe_get(product_url)
        if not response:
            print(f"[FAILED] Request failed for {product_name}")
            continue

        product_data = extract_data_from_html(response.text)
        if not product_data or product_data.get("price") is None:
            print(f"[FAILED] No price found for {product_name}")
            continue

        new_price = product_data["price"]
        currency = product_data.get("currency")
        source = product_data.get("source")

        old_price = old_price_row["price"] if old_price_row else None

        add_price(product_id, new_price, currency, source)

        next_check_at = compute_next_check(frequency)
        update_last_checked(product_id, next_check_at)

        if old_price is None:
            print(f"[INITIAL] Stored first price for {product_name}: {new_price} {currency}")
            continue

        if new_price == old_price:
            print(f"[NO CHANGE] {product_name}: {new_price} {currency}")
            continue

        change = new_price - old_price
        pct_change = (change / old_price) * 100 if old_price else 0

        if abs(pct_change) < threshold:
            print(f"[IGNORED] {product_name}: {pct_change:.2f}% below threshold ({threshold:.2f}%)")
            continue
        
        insight = generate_price_insight(
            product_name=product_name,
            old_price=old_price,
            new_price=new_price,
            pct_change=pct_change,
            threshold=threshold
        )

        direction = "increase" if change > 0 else "decrease"

        print(f"[CHANGE] {product_name}")
        print(f"  Old: {old_price} {currency}")
        print(f"  New: {new_price} {currency}")
        print(f"  Δ: {change:.2f} ({pct_change:.2f}%)")

        subject = f"Price {direction} detected for {product_name}"
        
        body = (
            f"Product: {product_name}\n"
            f"Old Price: {old_price} {currency}\n"
            f"New Price: {new_price} {currency}\n"
            f"Change: {change:.2f} ({pct_change:.2f}%)\n"
            f"Threshold: {threshold:.2f}%\n\n"
            f"Agent Insight:\n{insight}\n\n"
            f"URL: {product_url}\n"
        )

        send_price_alert(
            to_email=alert_email,
            subject=subject,
            body=body
        )

        add_notification(
            product_id=product_id,
            old_price=old_price,
            new_price=new_price,
            percentage_change=pct_change,
            recipient_email=alert_email,
            subject=subject,
            body=body
        )


if __name__ == "__main__":
    run_price_check_with_detection()