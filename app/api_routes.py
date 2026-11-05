import os
import json
from datetime import datetime, timedelta
import requests
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from app.db import get_db, query_db, execute_db
from app.services.agoda_service import AgodaService
from app.services.weather_service import WeatherService
from app.services.places_service import PlacesService
from app.services.budget_service import BudgetService
from app.services.itinerary_service import ItineraryService


api_bp = Blueprint('api', __name__)

# Initialize services
agoda_service = AgodaService()
weather_service = WeatherService()
budget_service = BudgetService()
places_service = PlacesService()
itinerary_service = ItineraryService()

# ==========================================
# 1. CURRENCY DETECTION HELPER
# ==========================================
def get_destination_currency(destination):
    dest = (destination or '').lower().strip()
    india_keywords = [
        "india", "delhi", "mumbai", "jaipur", "goa", "kerala", "bangalore",
        "bengaluru", "kolkata", "chennai", "hyderabad", "agra", "varanasi",
        "rajasthan", "pune", "ahmedabad", "shimla", "manali", "amritsar",
        "rishikesh", "ladakh", "kashmir", "udaipur", "kota", "jodhpur"
    ]
    japan_keywords = ["japan", "tokyo", "kyoto", "osaka"]
    uk_keywords = ["uk", "united kingdom", "london", "edinburgh"]
    europe_keywords = ["europe", "france", "paris", "italy", "rome", "spain", "germany"]
    uae_keywords = ["dubai", "uae", "abu dhabi"]

    if any(k in dest for k in india_keywords):
        return "₹", 75.0, "INR"
    elif any(k in dest for k in japan_keywords):
        return "¥", 140.0, "JPY"
    elif any(k in dest for k in uk_keywords):
        return "£", 0.82, "GBP"
    elif any(k in dest for k in europe_keywords):
        return "€", 0.92, "EUR"
    elif any(k in dest for k in uae_keywords):
        return "AED ", 3.67, "AED"
    else:
        return "$", 1.0, "USD"


# ==========================================
# 2. USER AUTHENTICATION
# ==========================================
@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'message': 'Name, email, and password are required'}), 400

    try:
        existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing:
            return jsonify({'message': 'Email is already registered'}), 409

        pwd_hash = generate_password_hash(password)
        user_id = execute_db(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, pwd_hash)
        )

        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email

        return jsonify({
            'message': 'Registration successful',
            'user': {'id': user_id, 'name': name, 'email': email}
        }), 201
    except Exception as e:
        return jsonify({'message': f"Database error: {str(e)}"}), 500


@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    try:
        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'message': 'Invalid email or password'}), 401

        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']

        return jsonify({
            'message': 'Login successful',
            'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}
        }), 200
    except Exception as e:
        return jsonify({'message': f"Database error: {str(e)}"}), 500


@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

# ==========================================
# 3. TRIPS & ITINERARY CRUD (Resilient)
# ==========================================
@api_bp.route('/trips/generate', methods=['POST'])
def generate_and_save_trip():
    data = request.get_json() or {}
    dest = data.get('destination', '').strip()
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not dest or not start_date or not end_date:
        return jsonify({'message': 'Destination, start date, and end date required'}), 400

    start_loc = data.get('starting_location', 'Origin')
    travelers = int(data.get('travelers_count', 2))
    pace = data.get('pace', 'balanced')
    budget_tier = data.get('budget_tier', 'moderate')
    user_budget = data.get('estimated_budget')
    transport_pref = data.get('transport_pref', 'mixed')
    lodging_pref = data.get('lodging_pref', 'hotel')
    interests = data.get('interests', [])
    curr_sym, _, _ = get_destination_currency(dest)

    # 1. ALWAYS GENERATE COMPLETE INTELLIGENT PLAN FIRST
    plan = itinerary_service.generate_full_itinerary(
        destination=dest,
        starting_location=start_loc,
        start_date=start_date,
        end_date=end_date,
        travelers_count=travelers,
        budget_tier=budget_tier,
        estimated_budget=user_budget,
        pace=pace,
        transport_pref=transport_pref,
        lodging_pref=lodging_pref,
        interests=interests,
        currency_symbol=curr_sym
    )

    trip_id = 1

    # 2. OPTIONALLY PERSIST TO MYSQL (Graceful fallback if DB is offline)
    try:
        user_id = session.get('user_id')
        if not user_id:
            guest = query_db("SELECT id FROM users LIMIT 1", one=True)
            user_id = guest['id'] if guest else 1

        trip_sql = """
            INSERT INTO trips (
                user_id, title, destination, starting_location, start_date, end_date,
                travelers_count, companion_type, budget_tier, estimated_budget,
                pace, transport_pref, lodging_pref, interests, route_summary, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'saved')
        """
        trip_id = execute_db(trip_sql, (
            user_id, plan['title'], dest, start_loc,
            start_date, end_date, travelers,
            data.get('companion_type', 'duo'),
            budget_tier, plan['budget_summary']['total_trip_cost'], pace,
            transport_pref, lodging_pref, json.dumps(interests),
            plan['route_summary']
        ), commit=False)

        for day in plan['days']:
            day_sql = """
                INSERT INTO itinerary_days (trip_id, day_number, date, summary, walking_distance_km, travel_time_minutes, total_cost)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            day_id = execute_db(day_sql, (
                trip_id, day['day_number'], day['date'], day['summary'],
                day['walking_distance_km'], day['travel_time_minutes'], day['total_cost']
            ), commit=False)

            for idx, act in enumerate(day['activities']):
                act_sql = """
                    INSERT INTO activities (day_id, time_slot, title, description, duration_minutes, estimated_cost, location_name, category, distance_from_prev_km, order_index)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                execute_db(act_sql, (
                    day_id, act['time_slot'], act['title'], act['description'],
                    act['duration_minutes'], act['estimated_cost'], act['location_name'],
                    act['category'], act['distance_from_prev_km'], idx
                ), commit=False)

        conn = get_db()
        conn.commit()
    except Exception as db_err:
        print(f"[Database Note] Trip rendered in-memory (DB fallback active): {db_err}")

    plan['id'] = trip_id
    return jsonify({
        'trip_id': trip_id,
        'message': 'Trip successfully generated!',
        'plan': plan
    }), 201


@api_bp.route('/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    # Retrieve user request params if passed
    req_dest = request.args.get('dest', 'Goa')
    req_start = request.args.get('start') or datetime.now().strftime('%Y-%m-%d')
    req_end = request.args.get('end') or (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    req_travelers = int(request.args.get('travelers', 2))

    try:
        trip = query_db("SELECT * FROM trips WHERE id = %s", (trip_id,), one=True)
        if trip:
            curr_sym, _, _ = get_destination_currency(trip['destination'])
            trip['currency_symbol'] = curr_sym
            days = query_db("SELECT * FROM itinerary_days WHERE trip_id = %s ORDER BY day_number ASC", (trip_id,))
            for day in days:
                day['activities'] = query_db("SELECT * FROM activities WHERE day_id = %s ORDER BY order_index ASC", (day['id'],))
            trip['days'] = days
            trip['interests'] = json.loads(trip['interests']) if trip['interests'] else []
            return jsonify(trip), 200
    except Exception as e:
        print(f"[Database Query Fallback] {e}")

    # Seamless Fallback: Generate the requested destination immediately!
    curr_sym, _, _ = get_destination_currency(req_dest)
    live_plan = itinerary_service.generate_full_itinerary(
        destination=req_dest,
        starting_location="Origin",
        start_date=req_start,
        end_date=req_end,
        travelers_count=req_travelers,
        budget_tier="moderate",
        currency_symbol=curr_sym
    )
    live_plan['id'] = trip_id
    return jsonify(live_plan), 200


# ==========================================
# 4. AGODA RAPIDAPI HOTEL ENDPOINTS
# ==========================================
@api_bp.route('/hotels/search', methods=['GET'])
def search_hotels():
    destination = request.args.get('destination', 'Mumbai')
    check_in = request.args.get('check_in', datetime.now().strftime('%Y-%m-%d'))
    check_out = request.args.get('check_out', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    adults = int(request.args.get('adults', 2))
    rooms = int(request.args.get('rooms', 1))
    stay_type = request.args.get('stay_type', 'overnight')
    currency = request.args.get('currency', 'INR')

    results = agoda_service.search_hotels(
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        stay_type=stay_type,
        currency=currency
    )
    return jsonify(results), 200


@api_bp.route('/hotels/<hotel_id>/details', methods=['GET'])
def get_hotel_details(hotel_id):
    details = agoda_service.get_hotel_details(hotel_id)
    return jsonify(details), 200


@api_bp.route('/hotels/<hotel_id>/prices', methods=['GET'])
def get_hotel_room_prices(hotel_id):
    check_in = request.args.get('check_in', datetime.now().strftime('%Y-%m-%d'))
    check_out = request.args.get('check_out', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    adults = int(request.args.get('adults', 2))
    rooms = int(request.args.get('rooms', 1))
    currency = request.args.get('currency', 'INR')

    prices = agoda_service.get_room_prices(
        property_id=hotel_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        currency=currency
    )
    return jsonify(prices), 200


# ==========================================
# 5. WEATHER RAPIDAPI ENDPOINT
# ==========================================
@api_bp.route('/weather', methods=['GET'])
def get_destination_weather():
    destination = request.args.get('destination', 'Mumbai')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    weather_result = weather_service.get_destination_weather(
        destination=destination,
        start_date=start_date,
        end_date=end_date
    )
    return jsonify(weather_result), 200


# ==========================================
# 6. CURRENCY CONVERSION RAPIDAPI ENDPOINT
# ==========================================
@api_bp.route('/currency/convert', methods=['GET'])
def convert_currency_route():
    from_curr = request.args.get('from', 'USD')
    to_curr = request.args.get('to', 'INR')
    amount = float(request.args.get('amount', 1.0))

    result = currency_service.convert_currency(
        from_curr=from_curr,
        to_curr=to_curr,
        amount=amount
    )
    return jsonify(result), 200


# ==========================================
# 7. MAPS & PLACE-SEARCH RAPIDAPI ENDPOINT
# ==========================================
@api_bp.route('/places/search', methods=['GET'])
def search_places_route():
    destination = request.args.get('destination', 'Mumbai')
    query_type = request.args.get('type', 'attractions')
    interests = request.args.getlist('interests')
    limit = int(request.args.get('limit', 8))

    results = places_service.search_places(
        destination=destination,
        query_type=query_type,
        interests=interests,
        limit=limit
    )
    return jsonify(results), 200

# ==========================================
# 8. REALISTIC BUDGET CALCULATOR ENDPOINT
# ==========================================
@api_bp.route('/budget/calculate', methods=['POST'])
def calculate_budget_route():
    data = request.get_json() or {}
    travellers = int(data.get('travellers', 2))
    days = int(data.get('days', 2))
    nights = int(data.get('nights', max(0, days - 1)))
    user_budget = data.get('budget')
    tier = data.get('budget_tier', 'moderate')
    currency = data.get('currency', '₹')
    hotel_price = data.get('hotel_price')
    transport_pref = data.get('transport_pref', 'mixed')
    lodging_pref = data.get('lodging_pref', 'hotel')
    attractions = data.get('attractions', [])

    result = budget_service.calculate_trip_budget(
        num_travellers=travellers,
        num_days=days,
        num_nights=nights,
        user_total_budget=float(user_budget) if user_budget else None,
        budget_tier=tier,
        currency_symbol=currency,
        hotel_nightly_price=float(hotel_price) if hotel_price else None,
        lodging_pref=lodging_pref,
        transport_pref=transport_pref,
        attractions=attractions
    )
    return jsonify(result), 200