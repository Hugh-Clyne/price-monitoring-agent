import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_price_insight(product_name, old_price, new_price, pct_change, threshold):
    try:
        prompt = f"""
                    You are a pricing intelligence assistant.

                    Summarize this price change in 2-3 sentences.
                    Be concise and business-focused.

                    Product: {product_name}
                    Old price: {old_price}
                    New price: {new_price}
                    Percent change: {pct_change:.2f}%
                    Alert threshold: {threshold:.2f}%

                    Include:
                        - significance (minor/moderate/significant)
                        - likely reason
                        - practical takeaway
                """

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        return response.output_text.strip()

    except Exception as e:
        print(f"OpenAI insight generations failed: {e}")
        return (
            f"{product_name} changed by {pct_change:.2f}%. "
            "This may reflect a pricing adjustment or promotion."
        )