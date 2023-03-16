NAME_LAYER = 'railway_lines'

import json
import os
import sys

sys.path.append('/Users/jonas/Library/CloudStorage/OneDrive-Persönlich/TU Berlin neu/Masterarbeit/Code/pros')
import prosd

scenario_id = 4
traingroup_id = 'tg_100_x0020_G_x0020_2500_113810'

routes = RouteTraingroup.query.filter(
    RouteTraingroup.traingroup_id == traingroup_id,
    RouteTraingroup.master_scenario_id == scenario_id
)

lines = [route.railway_line_id for route in routes]

layers = QgsProject.instance().mapLayersByName(NAME_LAYER)
layer = layers[0]

# categorie 1
value = lines
label = 'path'
symbol = QgsSymbol.defaultSymbol(layer.geometryType())
layer_style = dict()
layer_style['color'] = 'red'
layer_style['width'] = 0.8
symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
print(symbol_layer)
symbol.changeSymbolLayer(0, symbol_layer)
category1 = QgsRendererCategory(value, symbol, label)

# cateorie 2
value = None
label = 'not path'
symbol = QgsSymbol.defaultSymbol(layer.geometryType())
layer_style = dict()
layer_style['color'] = 'grey'
layer_style['width'] = 0.2
symbol_layer = QgsSimpleLineSymbolLayer.create(layer_style)
symbol.changeSymbolLayer(0, symbol_layer)
category2 = QgsRendererCategory(value, symbol, label)

categories = [category1, category2]
renderer = QgsCategorizedSymbolRenderer('id', categories)
#renderer = QgsRuleBaseRenderer('id', categories)
layer.setRenderer(renderer)
layer.triggerRepaint()





