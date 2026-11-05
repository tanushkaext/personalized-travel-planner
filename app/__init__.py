import os
from flask import Flask, render_template, session
from app.db import close_db
from app.api_routes import api_bp

def create_app():
    app = Flask(__name__)
    
    # REQUIRED for session cookies
    app.secret_key = os.getenv('SECRET_KEY', 'my-super-secret-travel-key-2026')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    app.teardown_appcontext(close_db)

    # Register REST API Blueprint under /api
    app.register_blueprint(api_bp, url_prefix='/api')

    # Page Routes
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/login")
    def login_view():
        return render_template("login.html")

    @app.route("/signup")
    def signup_view():
        return render_template("signup.html")

    @app.route("/plan")
    def plan_view():
        return render_template("planner.html")

    @app.route("/itinerary/<int:trip_id>")
    def itinerary_view(trip_id):
        return render_template("itinerary.html", trip_id=trip_id)

    @app.route("/my-trips")
    def my_trips_view():
        return render_template("my_trips.html")

    return app