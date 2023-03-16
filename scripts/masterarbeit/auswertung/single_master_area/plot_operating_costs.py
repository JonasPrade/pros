import matplotlib.pyplot as plt
import numpy as np
from prosd.models import MasterArea

master_area_id = 4589
transport_mode = 'sgv'
operating_cost = MasterArea.query.get(master_area_id).get_operating_cost_categories_by_transport_mode
filepath = f"../../../../example_data/report_scenarios/operating_cost/{master_area_id}_transportmode_{transport_mode}"

example_cost = operating_cost[transport_mode]
operating_cost_categories = list(example_cost["electrification"].keys())
operating_cost_categories.remove('train_cost')
operating_cost_categories.remove('co2_emission')

operating_cost_categorie_values = {}
tractions = list(example_cost.keys())
for category in operating_cost_categories:
    operating_cost_categorie_values[category] = []
    for key, value in example_cost.items():
        operating_cost_categorie_values[category].append(value[category])

"""
Where the plot begins
"""
width = 0.5
bottom = np.zeros(len(example_cost))

fig, ax = plt.subplots(figsize=(9, 7), dpi=300)

for key, value in operating_cost_categorie_values.items():
    p = ax.bar(list(tractions), value, width, label=key, bottom=bottom)
    bottom += value

box = ax.get_position()
fig.autofmt_xdate(rotation=45)
ax.set_title(f"Zusammensetzung Betriebskosten für Untersuchungsgebiet {master_area_id}")
ax.legend(loc="upper right")
ax.set(ylabel='Tsd. € pro Jahr')
# plt.show()
plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.3,
        dpi=300
    )
