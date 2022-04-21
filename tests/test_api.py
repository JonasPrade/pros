import requests

HOST = "http://127.0.01:5000/"
api_test_get_url = 'project/2'
api_test_post_url = 'project/4'


# Test api GET
url = HOST + api_test_get_url
response = requests.get(url)
print(response.status_code)
print(response.json())

# Test api PUT
"""
url = HOST + api_test_post_url
data = {'project': {'description': 'Murrmonorail statt Murrbahn', 'name': 'Murrbahnmonorail', 'project_contents': [], 'project_groups': [{'description': None, 'id': 1, 'name': 'Monorail Etappe 1'}], 'project_railway_lines': [{'coordinates': '0102000020e610000002000000e874aef5150b2f41461fd6dcffa457419a9ed09eed063041b2c1bcc898a65741', 'direction': None, 'electrified': 'oberleitun', 'from_km': None, 'id': 4, 'length': None, 'mifcode': 'mono_2', 'number_tracks': None, 'streckennummer': 2, 'to_km': None, 'type_of_transport': None, 'vmax': None}], 'superior_project': None, 'superior_project_id': None}}
response = requests.post(url, json=data)
print(response.status_code)
"""



