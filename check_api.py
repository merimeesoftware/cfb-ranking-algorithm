import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('CFBD_API_KEY')
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API key found")

# Check teams endpoint
r = requests.get(
    'https://api.collegefootballdata.com/teams', 
    headers={'Authorization': f'Bearer {api_key}'}
)
print(f"\nTeams endpoint status: {r.status_code}")
if r.status_code == 200:
    team = r.json()[0]
    print("First team data:")
    print(json.dumps(team, indent=2))
else:
    print(f"Error: {r.text}")

# Check conferences endpoint  
r2 = requests.get(
    'https://api.collegefootballdata.com/conferences',
    headers={'Authorization': f'Bearer {api_key}'}
)
print(f"\nConferences endpoint status: {r2.status_code}")
if r2.status_code == 200:
    conf = r2.json()[0]
    print("First conference data:")
    print(json.dumps(conf, indent=2))
else:
    print(f"Error: {r2.text}")
