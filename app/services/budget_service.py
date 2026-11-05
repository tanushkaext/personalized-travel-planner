import math
from datetime import datetime

class BudgetService:
    """
    Realistic Travel Budget Calculator
    Computes accurate, itemized travel expenses for all travellers:
      - Accommodation based on nights, nightly rate, and required room count (ceil(travellers / 2))
      - Food expenses based on traveller count, days, and dining tier
      - Local transit based on commute mode and group size
      - Sightseeing ticket entry fees from verified places
      - 10% contingency buffer for miscellaneous expenses
      - Clear budget evaluation: Within Budget, Near Limit, or Over Budget with actionable advice
    """

    def calculate_trip_budget(
        self,
        num_travellers=2,
        num_days=2,
        num_nights=1,
        user_total_budget=None,
        budget_tier='moderate',
        currency_symbol='₹',
        hotel_nightly_price=None,
        lodging_pref='hotel',
        transport_pref='mixed',
        attractions=None,
        contingency_percent=10.0
    ):
        travellers = max(1, int(num_travellers))
        days = max(1, int(num_days))
        nights = max(0, int(num_nights))
        tier = (budget_tier or 'moderate').lower()

        # 1. ACCOMMODATION CALCULATION
        # Rooms needed: 2 adults per standard room
        rooms_needed = math.ceil(travellers / 2)

        if hotel_nightly_price is None:
            # Benchmark nightly rate by tier and destination currency
            is_inr = (currency_symbol == '₹')
            tier_rates = {
                'budget': 1600 if is_inr else 45,
                'moderate': 3200 if is_inr else 95,
                'premium': 6500 if is_inr else 180,
                'luxury': 12000 if is_inr else 350
            }
            nightly_rate = tier_rates.get(tier, 3200 if is_inr else 95)
        else:
            nightly_rate = float(hotel_nightly_price)

        # For single day trip (0 nights), use a transit day-use fee
        if nights == 0:
            total_accommodation = round((nightly_rate * 0.5) * rooms_needed)
        else:
            total_accommodation = round(nightly_rate * nights * rooms_needed)

        # 2. FOOD & DINING CALCULATION
        is_inr = (currency_symbol == '₹')
        daily_food_per_person = {
            'budget': 500 if is_inr else 18,
            'moderate': 1000 if is_inr else 38,
            'premium': 1800 if is_inr else 70,
            'luxury': 3200 if is_inr else 130
        }.get(tier, 1000 if is_inr else 38)

        total_food = round(daily_food_per_person * travellers * days)

        # 3. LOCAL TRANSPORT CALCULATION
        # Estimates based on transit mode and group capacity
        cabs_needed = math.ceil(travellers / 4)
        if transport_pref == 'public':
            daily_transit = (150 if is_inr else 5) * travellers
        elif transport_pref in ['taxi', 'taxi_cab', 'cab']:
            daily_transit = (1200 if is_inr else 40) * cabs_needed
        elif transport_pref == 'rental':
            daily_transit = (2000 if is_inr else 65) * cabs_needed
        else:  # mixed (metro + auto-rickshaw/taxis)
            daily_transit = ((300 if is_inr else 12) * travellers) + (350 if is_inr else 15)

        total_transport = round(daily_transit * days)

        # 4. ATTRACTIONS & SIGHTSEEING TICKET ENTRY FEES
        total_attraction_fees = 0
        attraction_items = []

        if attractions and isinstance(attractions, list):
            for a in attractions:
                fee = float(a.get('estimated_ticket_inr', 0) if is_inr else a.get('estimated_ticket_usd', 0))
                total_attraction_fees += (fee * travellers)
                attraction_items.append({
                    "title": a.get('title', 'Attraction'),
                    "ticket_per_person": fee,
                    "total_for_group": fee * travellers,
                    "is_free": (fee == 0)
                })
        else:
            # Default representative heritage entrance fee
            default_entry = 250 if is_inr else 10
            total_attraction_fees = round(default_entry * travellers * min(days * 2, 4))

        # 5. CONTINGENCY BUFFER (10%)
        subtotal = total_accommodation + total_food + total_transport + total_attraction_fees
        contingency_amount = round(subtotal * (contingency_percent / 100.0))
        total_trip_cost = subtotal + contingency_amount
        cost_per_person = round(total_trip_cost / travellers)

        # 6. BUDGET STATUS & RECOMMENDATIONS
        budget_status = "unspecified"
        status_color = "secondary"
        status_message = "Trip budget estimated successfully."
        diff_amount = 0
        recommendations = []

        if user_total_budget is not None and float(user_total_budget) > 0:
            budget = float(user_total_budget)
            diff_amount = round(budget - total_trip_cost)

            if total_trip_cost <= (budget * 0.90):
                budget_status = "within_budget"
                status_color = "success"
                status_message = f"Comfortably within budget! You have {currency_symbol}{int(diff_amount):,} in surplus reserve."
            elif total_trip_cost <= budget:
                budget_status = "near_limit"
                status_color = "warning"
                status_message = f"Approaching budget limit. Remaining buffer: {currency_symbol}{int(diff_amount):,}."
            else:
                budget_status = "over_budget"
                status_color = "danger"
                excess = abs(diff_amount)
                status_message = f"Trip exceeds your budget by {currency_symbol}{int(excess):,}."
                recommendations = [
                    f"Switch accommodation from {tier.title()} to standard/budget to save up to {currency_symbol}{int(total_accommodation * 0.35):,}.",
                    "Choose local public transit or metro passes over private cabs.",
                    "Enjoy free historic promenades and bazaars rather than ticketed premium activities."
                ]

        return {
            "summary": {
                "travellers_count": travellers,
                "days_count": days,
                "nights_count": nights,
                "rooms_needed": rooms_needed,
                "total_trip_cost": total_trip_cost,
                "cost_per_person": cost_per_person,
                "currency_symbol": currency_symbol,
                "user_total_budget": user_total_budget,
                "budget_difference": diff_amount,
                "budget_status": budget_status,
                "status_color": status_color,
                "status_message": status_message,
                "recommendations": recommendations
            },
            "itemized_breakdown": {
                "accommodation": {
                    "total": total_accommodation,
                    "nightly_rate": nightly_rate,
                    "nights": nights,
                    "rooms": rooms_needed,
                    "label": f"{rooms_needed} room(s) × {nights} night(s) @ {currency_symbol}{int(nightly_rate):,}/night"
                },
                "food_and_dining": {
                    "total": total_food,
                    "per_person_per_day": daily_food_per_person,
                    "label": f"{currency_symbol}{daily_food_per_person}/day × {travellers} people × {days} days"
                },
                "local_transport": {
                    "total": total_transport,
                    "mode": transport_pref,
                    "label": f"Local {transport_pref.replace('_', ' ')} for {days} days"
                },
                "attractions": {
                    "total": total_attraction_fees,
                    "items": attraction_items,
                    "label": "Heritage entry tickets & sightseeing"
                },
                "contingency": {
                    "total": contingency_amount,
                    "percentage": contingency_percent,
                    "label": f"{int(contingency_percent)}% Emergency & Buffer Fund"
                }
            }
        }