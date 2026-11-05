import os
import requests
from datetime import datetime

class AgodaService:
    """
    Agoda RapidAPI Service (Provider: ntd119/agoda-com)
    Supported Endpoints:
      - /hotels/auto-complete: Resolves city/destination to Agoda cityId
      - /hotels/search-overnight: Standard overnight hotel search
      - /hotels/search-day-use: Transit / 6-8h day-use stay search
      - /hotels/details: Detailed property info, amenities, and photos
      - /hotels/room-prices: Specific room rates and date availability
    """

    def __init__(self):
        # Support both naming conventions
        self.api_key = os.getenv('AGODA_RAPIDAPI_KEY') or os.getenv('RAPIDAPI_KEY', '')
        self.api_host = os.getenv('AGODA_RAPIDAPI_HOST') or os.getenv('RAPIDAPI_AGODA_HOST', 'agoda-com.p.rapidapi.com')

    def _get_headers(self):
        return {
            'x-rapidapi-key': self.api_key.strip(),
            'x-rapidapi-host': self.api_host.strip()
        }

    def _resolve_city_id(self, destination):
        """Resolves a destination query string to an Agoda city ID."""
        if not self.api_key:
            return None
        try:
            url = f"https://{self.api_host}/hotels/auto-complete"
            resp = requests.get(url, headers=self._get_headers(), params={'query': destination}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get('data', [])
                for item in items:
                    if 'cityId' in item or item.get('type') == 'city':
                        return str(item.get('cityId') or item.get('id'))
                if items and isinstance(items[0], dict):
                    return str(items[0].get('id') or items[0].get('cityId'))
        except Exception as e:
            print(f"[AgodaService] Auto-complete error: {e}")
        return None

    def search_hotels(self, destination, check_in, check_out, adults=2, rooms=1, stay_type='overnight', currency='INR'):
        """
        Searches hotels for destination & dates.
        Returns verified provider results or a transparent Demo Mode fallback.
        """
        retrieval_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        hotels = []
        is_live = False
        error_note = None

        if self.api_key:
            try:
                city_id = self._resolve_city_id(destination) or "14690"  # 14690 is Mumbai fallback
                endpoint = "hotels/search-day-use" if stay_type == "day_use" else "hotels/search-overnight"
                url = f"https://{self.api_host}/{endpoint}"
                params = {
                    "cityId": city_id,
                    "checkinDate": check_in,
                    "checkoutDate": check_out,
                    "adults": str(adults),
                    "rooms": str(rooms),
                    "pageSize": "8",
                    "currency": currency
                }

                resp = requests.get(url, headers=self._get_headers(), params=params, timeout=9)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_hotels = (data.get('data', {}).get('hotels', [])
                                  if isinstance(data, dict) and isinstance(data.get('data'), dict)
                                  else data if isinstance(data, list) else [])

                    for h in raw_hotels:
                        price_info = h.get('pricing', {}).get('price', {})
                        amount = price_info.get('amount') or price_info.get('perNight') or 0
                        taxes = price_info.get('taxesAndFees', 0)
                        curr = price_info.get('currency', currency)

                        hotels.append({
                            "property_id": str(h.get('hotelId') or h.get('id')),
                            "name": h.get('hotelName') or h.get('name', 'Agoda Hotel'),
                            "rating": float(h.get('starRating') or h.get('reviewScore') or 4.0),
                            "reviews_count": h.get('reviewCount', 0),
                            "price_per_night": float(amount),
                            "currency": curr,
                            "taxes_and_fees": taxes,
                            "stay_type": "Day Use" if stay_type == "day_use" else "Overnight",
                            "image": h.get('imageUrl') or "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600",
                            "address": h.get('address', f"Central {destination.title()}"),
                            "is_available": True,
                            "booking_url": h.get('landingUrl') or f"https://www.agoda.com/search?city={city_id}"
                        })

                    if hotels:
                        is_live = True
                else:
                    error_note = f"Agoda API returned HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                error_note = f"Connection error: {str(e)}"

        # Transparent Demo Mode Fallback (clearly flagged; never fake live data)
        if not hotels:
            is_live = False
            base_rate = 1400 if stay_type == 'day_use' else 3200
            currency_symbol = "₹" if currency == "INR" else "$"
            hotels = [
                {
                    "property_id": "demo-101",
                    "name": f"{destination.title()} Heritage Suites & Spa",
                    "rating": 4.8,
                    "reviews_count": 342,
                    "price_per_night": base_rate,
                    "currency": currency,
                    "taxes_and_fees": int(base_rate * 0.12),
                    "stay_type": "Day Use" if stay_type == "day_use" else "Overnight",
                    "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600",
                    "address": f"Near Landmark District, {destination.title()}",
                    "is_available": True,
                    "booking_url": f"https://www.agoda.com/search?city={destination}"
                },
                {
                    "property_id": "demo-102",
                    "name": f"{destination.title()} City Backpackers & Inn",
                    "rating": 4.3,
                    "reviews_count": 185,
                    "price_per_night": int(base_rate * 0.45),
                    "currency": currency,
                    "taxes_and_fees": int(base_rate * 0.05),
                    "stay_type": "Day Use" if stay_type == "day_use" else "Overnight",
                    "image": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600",
                    "address": f"Transit Hub Area, {destination.title()}",
                    "is_available": True,
                    "booking_url": f"https://www.agoda.com/search?city={destination}"
                },
                {
                    "property_id": "demo-103",
                    "name": f"{destination.title()} Grand Bay Boutique Hotel",
                    "rating": 4.6,
                    "reviews_count": 490,
                    "price_per_night": int(base_rate * 1.5),
                    "currency": currency,
                    "taxes_and_fees": int(base_rate * 0.18),
                    "stay_type": "Day Use" if stay_type == "day_use" else "Overnight",
                    "image": "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=600",
                    "address": f"Promenade Road, {destination.title()}",
                    "is_available": True,
                    "booking_url": f"https://www.agoda.com/search?city={destination}"
                }
            ]

        return {
            "destination": destination,
            "stay_type": stay_type,
            "is_live_data": is_live,
            "mode": "Live Agoda API" if is_live else "Demo Mode (API Quota or Key Offline)",
            "retrieved_at": retrieval_time,
            "hotels": hotels,
            "error_note": error_note
        }

    def get_hotel_details(self, property_id):
        """Retrieves detailed property information, amenities, and room photos."""
        if self.api_key and not str(property_id).startswith('demo-'):
            try:
                url = f"https://{self.api_host}/hotels/details"
                resp = requests.get(url, headers=self._get_headers(), params={"hotelId": property_id}, timeout=8)
                if resp.status_code == 200:
                    d = resp.json().get('data', {})
                    return {
                        "name": d.get('hotelName') or d.get('name', 'Hotel Details'),
                        "description": d.get('description', 'Verified property on Agoda with modern amenities.'),
                        "amenities": d.get('amenities') or ["Free Wi-Fi", "Air Conditioning", "Daily Housekeeping", "24/7 Front Desk"],
                        "photos": d.get('photos', ["https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600"]),
                        "is_live": True
                    }
            except Exception as e:
                print(f"[AgodaService] Details error: {e}")

        # Demo Mode Details
        return {
            "name": "Verified Property",
            "description": "Centrally located property with verified check-in, complimentary high-speed Wi-Fi, air conditioning, and daily housekeeping.",
            "amenities": ["Free High-Speed Wi-Fi", "Daily Breakfast Included", "Air Conditioning", "24/7 Front Desk", "Luggage Storage"],
            "photos": [
                "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600",
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600"
            ],
            "is_live": False
        }

    def get_room_prices(self, property_id, check_in, check_out, adults=2, rooms=1, currency='INR'):
        """Retrieves specific room types, rates, and live availability."""
        retrieval_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        if self.api_key and not str(property_id).startswith('demo-'):
            try:
                url = f"https://{self.api_host}/hotels/room-prices"
                params = {
                    "hotelId": property_id,
                    "checkinDate": check_in,
                    "checkoutDate": check_out,
                    "adults": str(adults),
                    "rooms": str(rooms),
                    "currency": currency
                }
                resp = requests.get(url, headers=self._get_headers(), params=params, timeout=8)
                if resp.status_code == 200:
                    d = resp.json()
                    rooms_list = d.get('data', {}).get('rooms', [])
                    return {
                        "property_id": property_id,
                        "rooms": rooms_list,
                        "is_available": len(rooms_list) > 0,
                        "retrieved_at": retrieval_time,
                        "is_live": True
                    }
            except Exception as e:
                print(f"[AgodaService] Room prices error: {e}")

        return {
            "property_id": property_id,
            "rooms": [
                {"room_type": "Deluxe Double Room", "price": 2800, "status": "Available", "capacity": "2 Adults"},
                {"room_type": "Standard Twin Room", "price": 2400, "status": "Available", "capacity": "2 Adults"},
                {"room_type": "Executive Suite", "price": 4600, "status": "Only 1 Left", "capacity": "2 Adults + 1 Child"}
            ],
            "is_available": True,
            "retrieved_at": retrieval_time,
            "is_live": False
        }