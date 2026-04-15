from flask import Flask, send_from_directory, request, jsonify
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

@app.route('/api/assess',methods=['POST'])
def assess():
    # we'll be using numbers as wieghts for scoring ex:score >= 6 -> certain (92%)
    #later on we will change these placeholders +1,-1, +3 into real patterns for the ML model

    data = request.get_json()

    dechallenge = data.get('dechallenge', 'unknown')
    rechallenge = data.get('rechallenge', 'unknown')
    time_to_onset = data.get('time_to_onset', '')
    alternative = data.get('alternative_cause', '')
    narrative = data.get('narrative', '')

    score = 0
    if dechallenge == 'positive':
        score += 3
    elif dechallenge == 'negative':
        score -= 1
    if rechallenge == 'positive':
        score += 3
    if time_to_onset:
        score +=1
    if alternative:
        score -= 1
    if narrative:
        score += 1
    if score >= 6:
        category = 'Certain'
        confidence = 92
    elif score >= 4:
        category = 'Probable / Likely'
        confidence = 78
    elif score >= 2:
        category = 'Possible'
        confidence = 61
    elif score >= 0:
        category = 'Unlikely'
        confidence = 45
    else:
        category = 'Unassessable'
        confidence = 20

    return jsonify({
        'category': category,
        'confidence' : confidence,
        'score' : score
    })

#debug ture -> server restart automatically, port 5000 -> run http://127.0.0.1:5000
if __name__ == '__main__':
    app.run(debug=True, port=5000)

