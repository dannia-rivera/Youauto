from flask import Flask, render_template, request

# Creates the Flask application
app = Flask(__name__)

# Sample data used for Milestone 1.
# This can later be replaced with a database.
services = {
    "gas": [
        {"name": "Shell", "address": "402 Dodge St"},
        {"name": "Casey's", "address": "456 Maple Ave"}
    ],
    "mechanic": [
        {"name": "Joe's Auto Repair", "address": "789 Center St"},
        {"name": "Precision Auto", "address": "101 First Ave"}
    ],
    "ev": [
        {"name": "Tesla Supercharger", "address": "Mall Parking Lot"},
        {"name": "ChargePoint Station", "address": "Downtown Garage"}
    ]
}

# Displays the main page of the application.
@app.route("/")
def home():
    return render_template("index.html")


# Finds the selected service and sends the matching
# locations to the results page.
@app.route("/search")
def search():

    service = request.args.get("service")

    if service in services:
        results = services[service]
    else:
        results = []

    return render_template(
        "results.html",
        service=service,
        results=results
    )


# Runs the application in development mode.
if __name__ == "__main__":
    app.run(debug=True)