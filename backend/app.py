from flask import Flask, send_from_directory, request, jsonify
import os
import database

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
    age = data.get('age', '')
    sex = data.get('sex', '')
    region = data.get('region', '')
    reporter = data.get('reporter', '')

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

    case_id = database.save_case(
        drug = data.get('drug_name', ''),
        age = age,
        sex = sex,
        region = region,
        time_onset = time_to_onset,
        dechallenge = dechallenge,
        narrative = narrative,
        category = category,
        confidence = confidence,
        score = score
    )

    return jsonify({
        'case_id': case_id,
        'category': category,
        'confidence' : confidence,
        'score' : score,
        'patient':{
            'age': age,
            'sex': sex,
            'region': region,
            'reporter': reporter
        },
        'drug': data.get('drug_name', ''),
        'time_to_onset': data.get('time_to_onset', '')
    })

@app.route('/api/decision', methods=['POST'])
def decision():
    data = request.get_json()

    case_id = data.get('case_id', 0)
    assessor = data.get('assessor', 'N A')
    action = data.get('action', '')
    final_cat = data.get('final_cat', '')
    reasoning = data.get('reasoning', '')

    database.save_decision(case_id, assessor, action, final_cat, reasoning)

    return jsonify({
        'seccess': True,
        'message': 'Decision logged successfully'
    })
#debug ture -> server restart automatically, port 5000 -> run http://127.0.0.1:5000
if __name__ == '__main__':
    database.create_tables()
    app.run(debug=True, port=5000)

