import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_price_insight(product_name, old_price, new_price, pct_change, threshold):
    try:
        prompt = f"""
        You are a pricing intelligence assistant.

        Analyze this pricing event and provide a concise business summary in 2-3 sentences.

        Product: {product_name}
        Old price: ${old_price}
        New price: ${new_price}
        Percent change: {pct_change:.2f}%
        Alert threshold: {threshold:.2f}%

        Rules:
        - Classify significance as minor, moderate, or significant.
        - Do not invent specific causes.
        - If cause is unknown, use cautious wording such as:
          "may indicate promotional activity, seasonal pricing adjustments, or pricing strategy changes."
        - Focus on practical business impact.
        - Keep concise.

        Format:

        Significance:
        Possible explanation:
        Takeaway:
        """

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        return response.output_text.strip()

    except Exception as e:
        print(f"OpenAI insight generation failed: {e}")

        return (
            f"{product_name} price changed by "
            f"{pct_change:.2f}%. "
            f"This may reflect pricing adjustments or promotional activity."
        )