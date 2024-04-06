import xml.etree.ElementTree as ET
from docx import Document
import logging

logging.basicConfig(level=logging.INFO)


def clean_text(text):
    text = text.replace('\u00AD', '')  # remove uic sonderzeichen
    text = text.replace('- ', '') # remove Silbentrennung
    text = text.replace('– ', ' –')  # replace en dash with space en dash space
    text = text.replace('Bahn reform', 'Bahnreform')  # replace Bahn reform with Bahnreform
    return text


def create_heading_element(parent, heading_text, level, page_number):
    heading = ET.SubElement(parent, "heading", level=str(level), page_number=page_number)
    heading.text = heading_text
    return heading


def adjust_current_path(current_path, level):
    while len(current_path) > level:
        current_path.pop()
    while len(current_path) < level:
        current_path.append(current_path[-1])


def handle_paragraph(para, current_parent):
    if para.style is None:
        if para.text == '':
            logging.debug(f"Para has no style: {para.text}. Continued.")
            return
        else:
            para.style = 'Normal'
            logging.debug(f"Para has no style: {para.text}. Set to Normal.")

    if para.style.startswith('Heading'):
        level = int(para.style.replace('Heading', ''))
        adjust_current_path(current_parent, level)
        heading_text = clean_text(para.text)
        page_number = para.page_number
        heading_element = create_heading_element(current_parent[-1], heading_text, level, page_number)
        current_parent.append(heading_element)

    elif any(para.style.startswith(style) for style in ['Normal', 'BodyText']):
        if para.text == '':
            return
        ET.SubElement(current_parent[-1], "paragraph").text = clean_text(para.text)

    elif para.style == 'ListParagraph':
        if para.text == '':
            return
        ET.SubElement(current_parent[-1], "list_item").text = clean_text(para.text)

    else:
        logging.debug(f"Unknown style: {para.style}")


def handle_table(table_word, current_parent):
    # TODO: remove empty rows (for example table 5)
    table = ET.SubElement(current_parent[-1], "table")
    for row in table_word.xpath('.//w:tr'):
        row_element = ET.SubElement(table, "row")
        for cell in row.xpath('.//w:tc'):
            cell_element = ET.SubElement(row_element, "cell")
            for para in cell.xpath('.//w:p'):
                para_element = ET.SubElement(cell_element, "paragraph")
                para_element.text = clean_text(para.text)


def word_to_xml(word_path, xml_path):
    doc = Document(word_path)
    root = ET.Element('document')
    current_parent = [root]

    for block in doc.element.body:
        if block.tag.endswith('p'):
            handle_paragraph(block, current_parent)
        elif block.tag.endswith('tbl'):
            handle_table(block, current_parent)
        else:
            logging.debug(f"Unknown block type: {block.tag}")

    tree = ET.ElementTree(root)
    ET.indent(tree, space= " ", level=0)
    tree.write(xml_path, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    year = 2021
    file = '../../example_data/import/verkehrsinvestitionsbericht/2021_rail.pdf'
    xml_path = '../../example_data/import/verkehrsinvestitionsbericht/2021_rail.xml'
    json_path = '../../example_data/import/verkehrsinvestitionsbericht/2021_rail.json'
    latex_path = '../../example_data/import/verkehrsinvestitionsbericht/2021_rail.tex'
    word_path = '../../example_data/import/verkehrsinvestitionsbericht/2021_rail.docx'
    word_to_xml(word_path, xml_path)
