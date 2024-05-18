from flask import Flask, redirect, request, session, url_for, render_template
import requests
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Strava API credentials
client_id = '75238'
client_secret = '0ad2c3b5d522ef8f4dbbb89d4759efabea4f7ff6'
redirect_uri = 'http://localhost:5000/callback'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=read,activity:read_all")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    response = requests.post(
        'https://www.strava.com/oauth/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
    )
    response_data = response.json()
    session['access_token'] = response_data['access_token']
    return redirect(url_for('set_goal'))

@app.route('/set_goal', methods=['GET', 'POST'])
def set_goal():
    if request.method == 'POST':
        goal_type = request.form.get('goal_type')
        goal_value = float(request.form.get('goal_value'))
        unit = request.form.get('unit')
        activity_type = request.form.getlist('activity_type')

        if 'all' in activity_type:
            activity_type = ['all']

        session['goal_type'] = goal_type
        session['goal_value'] = goal_value
        session['unit'] = unit
        session['activity_type'] = activity_type
        
        return redirect(url_for('dashboard'))

    return render_template('set_goal.html')

def fetch_all_activities(access_token):
    activities = []
    page = 1
    start_of_year = datetime(datetime.now().year, 1, 1).timestamp()
    while True:
        response = requests.get(
            f'https://www.strava.com/api/v3/athlete/activities?page={page}&per_page=200&after={int(start_of_year)}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        data = response.json()
        if not data:
            break
        activities.extend(data)
        page += 1
    return activities

@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    goal_type = session.get('goal_type')
    goal_value = session.get('goal_value')
    unit = session.get('unit')
    activity_type = session.get('activity_type')

    activities = fetch_all_activities(access_token)

    if 'all' not in activity_type:
        filtered_activities = [activity for activity in activities if activity['type'] in activity_type]
    else:
        filtered_activities = activities

    today = datetime.now()
    start_of_year = datetime(today.year, 1, 1)
    total_weeks = (today - start_of_year).days // 7 + 1

    weekly_totals = [0] * total_weeks
    for activity in filtered_activities:
        activity_date = datetime.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        week_index = (activity_date - start_of_year).days // 7
        if goal_type == 'elevation':
            weekly_totals[week_index] += activity['total_elevation_gain']
        elif goal_type == 'distance':
            weekly_totals[week_index] += activity['distance']
        elif goal_type == 'time':
            weekly_totals[week_index] += activity['moving_time'] / 3600  # Convert seconds to hours

    if goal_type == 'distance':
        if unit == 'miles':
            weekly_totals = [total * 0.000621371 for total in weekly_totals]  # Convert meters to miles
        elif unit == 'kilometers':
            weekly_totals = [total / 1000 for total in weekly_totals]  # Convert meters to kilometers
    elif goal_type == 'time' and unit == 'days':
        weekly_totals = [total / 24 for total in weekly_totals]  # Convert hours to days
    elif goal_type == 'elevation' and unit == 'feet':
        weekly_totals = [total * 3.28084 for total in weekly_totals]  # Convert meters to feet

    total = sum(weekly_totals)
    days_passed = (today - start_of_year).days
    total_days = 365 if today.year % 4 else 366
    expected_progress = (days_passed / total_days) * goal_value

    # Calculate cumulative totals for actual data
    cumulative_actual = []
    cumulative_sum = 0
    for weekly_total in weekly_totals:
        cumulative_sum += weekly_total
        cumulative_actual.append(cumulative_sum)

    return render_template('dashboard.html', activities=filtered_activities, total=total, expected_progress=expected_progress, goal_value=goal_value, goal_type=goal_type, unit=unit, cumulative_actual=cumulative_actual)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)