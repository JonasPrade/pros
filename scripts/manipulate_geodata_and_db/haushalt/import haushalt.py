import xml.etree.ElementTree as ET

RELEVANT_EP = [
    12,
    60
]

file_path = '../../../example_data/import/haushalt/haushalt_2024.xml'

tree = ET.parse(file_path)
root = tree.getroot()

sections = root.findall('.//einzelplan')

for einzelplan in sections:
    einzelplan_name = einzelplan.find('text').text
    if int(einzelplan.attrib["nr"]) not in RELEVANT_EP:
        continue

    chapters = einzelplan.findall('kapitel')
    for chapter in chapters:
        chapter_name = chapter.find('text').text
        budgets = chapter.findall('einnahmen-ausgaben-art')
        for budget in budgets:
            budget_name = budget.find('text').text


