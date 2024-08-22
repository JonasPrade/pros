import os
import frontmatter
import logging
import marko
import yaml

from prosd.models import BksAction, BksCluster, BksHandlungsfeld
from prosd import db


TIER_2_HEADINGS = ["Text Beschleunigungskommission", "Vorschlag BKS Vorgehen"]


def extract_markdown(markdown_text):
    document = marko.parse(markdown_text)

    sections = {}
    current_heading = None
    parent_heading = None

    for element in document.children:
        if isinstance(element, marko.block.Heading):
            if element.level == 2:
                parent_heading = element.children[0].children
                if parent_heading in TIER_2_HEADINGS:
                    sections[parent_heading] = ""
                    current_heading = None
                else:
                    current_heading = None
            elif element.level == 3:
                current_heading = element.children[0].children
                if parent_heading:
                    combined_heading = f"{parent_heading} - {current_heading}"
                    sections[combined_heading] = ""

        elif parent_heading is not None:
            if isinstance(element, marko.block.BlankLine):
                continue
            if isinstance(element, marko.block.ThematicBreak):
                continue

            text = element.children[0].children
            if isinstance(text, list):
                text = text[0].children
            if isinstance(text, str):
                if text == '[[🗺️ Übersicht Maßnahmen Beschleunigungskommission Schiene]]':
                    continue
                if text == 'ref':
                    continue

                if parent_heading in TIER_2_HEADINGS:
                    sections[parent_heading] += text.replace('\x02', '')
                elif current_heading:
                    combined_heading = f"{parent_heading} - {current_heading}"
                    sections[combined_heading] += text.replace('\x02', '')

    sections.pop('Einschätzung/Kommentar', None)
    sections.pop('Zusammenhängende Maßnahmen', None)
    sections.pop('Erster Umsetzungsbericht', None)
    sections.pop('Zweiter Umsetzungsbericht', None)
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

                        if "Erster Umsetzungsbericht - Startpunkt" in sections.keys():
                            bks.review_1_start = sections["Erster Umsetzungsbericht - Startpunkt"]
                        else:
                            logging.info(f"bks action {title} has no text for Startpunkt")

                        if "Erster Umsetzungsbericht - Zurückgelegte Strecke" in sections.keys():
                            bks.review_1_done = sections["Erster Umsetzungsbericht - Zurückgelegte Strecke"]
                        else:
                            logging.info(f"bks action {title} has no text for Zurückgelegte Strecke")

                        if "Erster Umsetzungsbericht - Nächster Halt" in sections.keys():
                            bks.review_1_next = sections["Erster Umsetzungsbericht - Nächster Halt"]
                        else:
                            logging.info(f"bks action {title} has no text for Nächster Halt")

                        if "status_bks_1" in post.metadata.keys():
                            bks.review_1_status = post.metadata["status_bks_1"]
                        else:
                            logging.info(f"bks action {title} has no status_bks")

                        if "Zweiter Umsetzungsbericht - Startpunkt" in sections.keys():
                            bks.review_2_start = sections["Zweiter Umsetzungsbericht - Startpunkt"]
                        else:
                            logging.info(f"bks action {title} has no text for review_2_start")

                        if "Zweiter Umsetzungsbericht - Zurückgelegte Strecke" in sections.keys():
                            bks.review_2_done = sections["Zweiter Umsetzungsbericht - Zurückgelegte Strecke"]
                        else:
                            logging.info(f"bks action {title} has no text for review_2_done")

                        if "Zweiter Umsetzungsbericht - Nächster Halt" in sections.keys():
                            bks.review_2_next = sections["Zweiter Umsetzungsbericht - Nächster Halt"]
                        else:
                            logging.info(f"bks action {title} has no text for review_2_next")

                        if "status_bks_2" in post.metadata.keys():
                            bks.review_2_status = post.metadata["status_bks_2"]
                        else:
                            logging.info(f"bks action {title} has no text for review_2_start")

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
    logging.basicConfig(level=logging.INFO)
    folder = '/Users/jonas/NextcloudGastel/Büro Gastel/80 Obsidian Beschleunigungskommission Test/Beschleunigungskommission Schiene/notes'
    overwrite = True
    process_md_files(folder, overwrite)
