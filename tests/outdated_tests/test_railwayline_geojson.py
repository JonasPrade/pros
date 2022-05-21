import requests

HOST = "http://127.0.01:5000/"
url_projects = HOST + 'projects'

response = requests.get(url_projects)
answ = response.json()
print(answ['projects'][0]['project_railway_lines'][0]['coordinates'])