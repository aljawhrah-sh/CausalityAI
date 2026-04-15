from flask import Flask, send_from_directory
import os

app = Flask(__name__)

SCREENS = os.path.join(os.path.dirname(__file__), '..', 'screens')

#routing/mapping homepage url
@app.route('/')
def home():
    return send_from_directory(SCREENS, '00-login.html')

#filename ->whatever html inside screens gets in the function 
#http://127.0.0.1:5000/screens/any html file
@app.route('/screens/<filename>')
def serve_screen(filename):
    return send_from_directory(SCREENS, filename)

#debug ture -> server restart automatically, port 5000 -> run http://127.0.0.1:5000
if __name__ == '__main__':
    app.run(debug=True, port=5000)
