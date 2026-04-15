from flask import Flask

app = Flask(__name__)

#routing/mapping homepage url
@app.route('/')
def home():
    return "CausalityAI server is running"

#debug ture -> server restart automatically, port 5000 -> run http://localhost:5000
if __name__ == '__main__':
    app.run(debug=True, port=5000)
    