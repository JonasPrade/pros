import os
import frontmatter
import logging
import marko
import yaml

from prosd.models import BksAction, BksCluster, BksHandlungsfeld
from prosd import db

def extract_markdown(markdown_text):
    document = marko.parse(markdown_text)

    sections = {}

    current_heading = None

    for element in document.children:
        if isinstance(element, marko.block.Heading):
            current_heading = element.children[0].children
            sections[current_heading] = ""
        elif current_heading is not None:
            # some elements are not relevant for the text
            if isinstance(element, marko.block.BlankLine):
                continue
            if isinstance(element, marko.block.ThematicBreak):
                continue

            # extract the text
            text = element.children[0].children
            if isinstance(text, list):
                text = text[0].children
            if isinstance(text, str):
                if text == '[[🗺️ Übersicht Maßnahmen Beschleunigungskommission Schiene]]':
                    continue
                if text == 'ref':
                    continue
                sections[current_heading] += text.replace('\x02','')

    sections.pop('Einschätzung/Kommentar', None)
    sections.pop('Zusammenhängende Maßnahmen', None)
    sections.pop('Erster Umsetzungsbericht', None)
    return sections


def process_md_files(folder_path, overwrite=True):
    files_in_folder = os.listdir(folder_path)
    bks_actions = []

    if overwrite == True:
        BksAction.query.delete()
        db.session.commit()

    for file_name in files_in_folder:
        if file_name.endswith('md'):
            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, encoding="utf-8") as f:
                    post = frontmatter.load(f)
                    if "handlungsfeld" in post.metadata.keys():
                        title = post.metadata["titel"]
                        handlungsfeld = post.metadata["handlungsfeld"]
                        sections = extract_markdown(post.content)
                        bks = BksAction(
                            name=title,
                        )

                        if "Text Beschleunigungskommission" in sections.keys():
                            bks.report_text = sections["Text Beschleunigungskommission"]
                        else:
                            logging.info(f"bks action {title} has no text for Text Beschleunigungskommission")

                        if "Vorschlag BKS Vorgehen" in sections.keys():
                            bks.report_process = sections["Vorschlag BKS Vorgehen"]
                        else:
                            logging.info(f"bks action {title} has no text for Vorschlag BKS Vorgehen")

                        if "Startpunkt" in sections.keys():
                            bks.review_1_start = sections["Startpunkt"]
                        else:
                            logging.info(f"bks action {title} has no text for Startpunkt")

                        if "Zurückgelegte Strecke" in sections.keys():
                            bks.review_1_done = sections["Zurückgelegte Strecke"]
                        else:
                            logging.info(f"bks action {title} has no text for Zurückgelegte Strecke")

                        if "Nächster Halt" in sections.keys():
                            bks.review_1_next = sections["Nächster Halt"]
                        else:
                            logging.info(f"bks action {title} has no text for Nächster Halt")

                        if "status_bks" in post.metadata.keys():
                            bks.review_1_status = post.metadata["status_bks"]
                        else:
                            logging.info(f"bks action {title} has no status_bks")

                        cluster = BksCluster.query.filter(BksCluster.number.like(str(post.metadata["clusternummer"]))).first()
                        if cluster is None:
                            logging.warning(f"bks action {title} has no fitting cluster {post.metadata['clusternummer']}")
                        else:
                            bks.cluster = cluster

                        bks_actions.append(bks)

            except yaml.scanner.ScannerError as e:
                logging.warning(f"Error in file {file_name}: {e}")
            except yaml.reader.ReaderError as e:
                logging.warning(f"Error in file {file_name}: {e}")


    db.session.add_all(bks_actions)
    db.session.commit()

if __name__ == '__main__':
    folder = '/Users/jonas/NextcloudGastel/Büro Gastel/80 Obsidian Beschleunigungskommission Test/Beschleunigungskommission Schiene/notes'
    overwrite = True
    process_md_files(folder, overwrite)
