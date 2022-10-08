NAME_LAYER = 'railway_lines'

from prosd.models import TimetableTrainGroup

traingroup_id = "tg_NW20.1_N_x0020_20101_3607"
traingroup = TimetableTrainGroup.query.get(traingroup_id)

lines_of_path = traingroup.lines

layers = QgsProject.instance().mapLayersByName(NAME_LAYER)
layer = layers[0]


# categorie 1
value = lines_of_path
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





