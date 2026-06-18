from flask import flask

app = Flask(__name__)

@app.route("/") #homepage users see when they open YouAuto
def home():
  return """
  <h1>YouAuto<h1>
  <p>Find gas stations, mechanics, and EV charging nearby.</p>

  <h2>Search Services</h2>

  <ul>
      <li>Gas Stations</li>
      <li>Mechanics</li>
      <li>Ev Charging</li>
      <li>Auto Parts Stores</li>
  </ul>

  <p>This is the first version of YouAuto</p>
  """

#starts the local development server so the website can be viewed in browser
if __name__ == "__main__":
  app.run(debug=True)
