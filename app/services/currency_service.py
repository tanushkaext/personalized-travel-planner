import os
import requests
from datetime import datetime

class CurrencyService:
    """
    RapidAPI Currency Conversion Service (Provider: principalapis)
    Endpoint: https://currency-conversion-and-exchange-rates.p.rapidapi.com/convert
    
    Capabilities:
      - Converts amounts between world currencies (USD, INR, EUR, GBP, JPY, AED, etc.).
      - Preserves original source amount and source currency for transparency.
      - Displays exchange rate, conversion timestamp, and bank rate disclaimer.
      - Never performs double conversion.
      - Transparent fallback if API key or quota is offline.
    """

    def __init__(self):
        self.api_key = os.getenv('CURRENCY_RAPIDAPI_KEY') or os.getenv('RAPIDAPI_KEY', '')
        self.api_host = os.getenv('CURRENCY_RAPIDAPI_HOST', 'currency-conversion-and-exchange-rates.p.rapidapi.com')

    def _get_headers(self):
        return {
            'x-rapidapi-key': self.api_key.strip(),
            'x-rapidapi-host': self.api_host.strip()
        }

    def convert_currency(self, from_curr='USD', to_curr='INR', amount=1.0):
        """
        Converts an amount from one currency to another using RapidAPI.
        """
        from_code = from_curr.upper().strip()
        to_code = to_curr.upper().strip()
        retrieval_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        disclaimer = "Estimated equivalent amount based on interbank rates; final transaction rates may differ at checkout."

        # Identical currencies: no conversion needed
        if from_code == to_code:
            return {
                "source_currency": from_code,
                "target_currency": to_code,
                "original_amount": round(float(amount), 2),
                "converted_amount": round(float(amount), 2),
                "exchange_rate": 1.0,
                "retrieved_at": retrieval_time,
                "disclaimer": disclaimer,
                "is_live": True,
                "mode": "Same Currency"
            }

        is_live = False
        rate = None
        converted = None
        error_note = None

        if self.api_key:
            try:
                url = f"https://{self.api_host}/convert"
                params = {
                    "from": from_code,
                    "to": to_code,
                    "amount": str(amount)
                }
                resp = requests.get(url, headers=self._get_headers(), params=params, timeout=7)
                if resp.status_code == 200:
                    data = resp.json()
                    # Extract result from API response
                    converted = (
                        data.get('result') or data.get('converted_amount') or
                        data.get('value') or data.get('data', {}).get('result')
                    )
                    rate = (
                        data.get('info', {}).get('rate') or
                        data.get('rate') or
                        (float(converted) / float(amount) if converted and amount else None)
                    )
                    if converted is not None:
                        is_live = True
                else:
                    error_note = f"RapidAPI HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                error_note = str(e)

        # Fallback Mode with realistic reference market rates
        if rate is None:
            reference_usd_rates = {
                'USD': 1.0,
                'INR': 83.5,
                'EUR': 0.92,
                'GBP': 0.79,
                'JPY': 152.0,
                'AED': 3.67,
                'SGD': 1.34,
                'AUD': 1.51,
                'CAD': 1.36,
                'THB': 36.5
            }
            from_usd = reference_usd_rates.get(from_code, 1.0)
            to_usd = reference_usd_rates.get(to_code, 1.0)
            rate = to_usd / from_usd
            converted = float(amount) * rate
            is_live = False

        return {
            "source_currency": from_code,
            "target_currency": to_code,
            "original_amount": round(float(amount), 2),
            "converted_amount": round(float(converted), 2),
            "exchange_rate": round(float(rate), 4),
            "retrieved_at": retrieval_time,
            "disclaimer": disclaimer,
            "is_live": is_live,
            "mode": "Live RapidAPI (principalapis)" if is_live else "Demo Mode (Reference Interbank Rate)",
            "error_note": error_note
        }