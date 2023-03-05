import nbformat
from traitlets.config import Config
from nbconvert.preprocessors import TagRemovePreprocessor
from nbconvert import LatexExporter

# url = 'http://localhost:8888/notebooks/scripts/masterarbeit/auswertung/auswertung.ipynb'
# response = urlopen(url).read().decode()
#
# notebook = nbformat.reads(response, as_version=4)

filepath_import = 'test_auswertung.ipynb'
filepath_save = '/Users/jonas/Library/CloudStorage/OneDrive-Persönlich/TU Berlin neu/Masterarbeit/Bericht/reports_scenarios/test.tex'

c = Config()

c.TagRemovePreprocessor.remove_cell_tags = ("remove_cell",)
c.TagRemovePreprocessor.remove_input_tags = ('remove_input',)
c.TagRemovePreprocessor.enabled = True

c.LatexExporter.preprocessors = ["nbconvert.preprocessors.TagRemovePreprocessor"]

exporter = LatexExporter(config=c)
exporter.register_preprocessor(TagRemovePreprocessor(config=c), True)

notebook = nbformat.read(filepath_import, as_version=4)
(body, ressources) = LatexExporter(config=c).from_notebook_node(notebook)

with open(filepath_save, 'w') as f:
    f.write(body)
