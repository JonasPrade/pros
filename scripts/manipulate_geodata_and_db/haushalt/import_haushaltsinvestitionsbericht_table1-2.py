import os
import pandas as pd
import numpy as np
import logging

import sqlalchemy.exc

from prosd import db
from prosd.models import FinVe, Budget, ProjectContent

YEAR = 2024
DROP_FIRST_ROWS = 3
EMPTY_COLUMN = 4
file_path = os.path.join(f'../../../example_data/import/haushaltsinvestitionsbericht/{YEAR}/{YEAR}_table1-2.xlsx')

signal_word_break_description = 'Gegenstand der Sammelvereinbarung ist die'
SAMMEL_FINVE = True
filepath_alias_csv = '../../../example_data/import/projectcontent_alias_names/pc_alias_name.csv'


logging.basicConfig(level=logging.INFO)

TRANSLATE_INDEX = {
    "all": "all",
    "Kap. 1202, Titel 891 01": "891_01",
    "Kap. 1202, Titel 891 01 ": "891_01",
    "Kap. 1202, Titel 891 02": "891_02",
    "Kap. 1202, Titel 891 03": "891_03",
    "Kap. 1202, Titel 891 04": "891_04",
    "Kap. 1202, Titel 861 01": "_861_01",
    "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐": "891_91",
    "Kap. 1210 (alt), Titel 891 72 (ZIP)": "891_72",
    "Kap. 1202, Titel 891 11 (zusätzl. Darstellg. LUFV)": "891_11",
    "Kap. 6091 (alt), Titel 891 21‐ ITF ‐": "891_21",
    "nachrichtlich: Beteiligung Dritter": "third_parties",
    "nachrichtlich: Eigenmittel der EIU gemäß BUV": "equity"
}


def convert_tablecontent_to_list(element):
    if isinstance(element, str):
        value_list = [item.replace("'", "").replace(" ", "").replace(".", "") for item in element.split("\n")]
    elif isinstance(element, float):
        value_list = [int(element)]
    return value_list


def fill_cost_template(row, finance_titels):
    columns = ["cost_estimate_actual", "spent_two_years_previous", "allowed_previous_year", "spending_residues", "year_planned", "next_years"]
    index_names = ["all", "third_parties", "equity", "891_01", "891_02", "891_03", "891_04", "891_91", "891_72", "891_11", "891_21", "861_01"]
    cost_df = pd.DataFrame(None, index=index_names, columns=columns)

    actual = convert_tablecontent_to_list(row["aktuell"])
    verausgabt_col = convert_tablecontent_to_list(row[f"Verausgabt bis {YEAR - 1}"])
    bewilligt_col = convert_tablecontent_to_list(row[f"Bewilligt {YEAR}"])
    ausgabereste_col = convert_tablecontent_to_list(row[f"nach {YEAR} übertragene Ausgabereste"])
    veranschlagt_col = convert_tablecontent_to_list(row[f"Veranschlagt {YEAR + 1}"])
    vorbehalten_col = convert_tablecontent_to_list(row[f"Vorbehalten {YEAR + 2}"])

    for i, element_origin_name in enumerate(finance_titels):
        element = TRANSLATE_INDEX[element_origin_name]
        cost_df.at[element, "cost_estimate_actual"] = actual[i]
        cost_df.at[element, "spent_two_years_previous"] = verausgabt_col[i]
        cost_df.at[element, "allowed_previous_year"] = bewilligt_col[i]
        cost_df.at[element, "spending_residues"] = ausgabereste_col[i]
        cost_df.at[element, "year_planned"] = veranschlagt_col[i]
        cost_df.at[element, "next_years"] = vorbehalten_col[i]

    # some values are not existing -> fill with 0
    cost_df.replace("‐", 0, inplace=True)

    return cost_df


def cost_df_to_budget(cost_df, budget):
    for column in cost_df.columns:
        for index in cost_df.index:
            # Überspringe den "all" Index bei der Zuordnung
            if index == "all":
                attribute_name = f"{column}"
            else:
                attribute_name = f"{column}_{index}"

            # Überprüfen, ob das Attribut im Budget existiert
            if hasattr(budget, attribute_name):
                # Wert zuweisen, falls vorhanden
                value = None if pd.isna(cost_df.at[index, column]) else int(cost_df.at[index, column])
                setattr(budget, attribute_name, value)
            else:
                if column == "spending_residues" and index == "third_parties":
                    continue
                if column == "spending_residues" and index == "equity":
                    continue
                raise ValueError(f"Attribute {attribute_name} not found in Budget model")

    return budget


def read_pc_alias_names():
    """
    Reads the project content alias names from a CSV file and returns a dictionary mapping alias names to project content IDs.
    """
    pc_alias_names = {}
    df = pd.read_csv(filepath_alias_csv)
    for _, row in df.iterrows():
        alias_name = row['alias_name']
        pc_name = row['project_content_id']
        pc_alias_names[alias_name] = pc_name
    return pc_alias_names


def read_and_prepare_data():
    """
    Reads and preprocesses the data from an Excel file.
    Drops the first few rows and an empty column, renames the columns, and combines rows with the same 'lfd_nr'.
    Returns a DataFrame with the processed data.
    """
    df = pd.read_excel(file_path)
    df = df.drop(df.index[:DROP_FIRST_ROWS])
    df = df.drop(df.columns[EMPTY_COLUMN], axis=1)
    df.columns = [
        "lfd_nr", "finve_nr", "bedarfsplan_schiene", "bezeichnung",
        "Aufnahme in EP oder Abschluss FinVe", "ursprünglich",
        "Vorjahr", "aktuell", "Entwicklung zu Vorjahr absolut",
        "Entwicklung zu Vorjahr relativ", "Gründe",
        f"Verausgabt bis {YEAR-1}", f"Bewilligt {YEAR}",
        f"nach {YEAR} übertragene Ausgabereste", f"Veranschlagt {YEAR+1}",
        f"Vorbehalten {YEAR+2}"
    ]
    df = df.fillna('')
    result = []
    current_row = None
    for _, row in df.iterrows():
        if row['lfd_nr']:
            if current_row is not None:
                result.append(current_row)
            current_row = row.copy()
        else:
            for col in df.columns[1:]:
                if isinstance(current_row[col], (int, float)) or isinstance(row[col], (int, float)):
                    if row[col] == '':
                        continue
                    add_value = row[col] if row[col] != '' else 0
                    current_row[col] = str(current_row[col]) + '\n' + str(add_value)
                else:
                    current_row[col] += '\n' + row[col]
    if current_row is not None:
        result.append(current_row)
    return pd.DataFrame(result)


def create_finve(row, finve_id):
    """
    Creates a FinVe object from a row of data and adds it to the database.
    Commits the transaction and returns the created FinVe object.
    """
    name = row['bezeichnung'].split('\n')[0]
    starting_year = row["Aufnahme in EP oder Abschluss FinVe"]
    cost_estimate_original = row["ursprünglich"]
    finve = FinVe(
        id=int(finve_id),
        name=name,
        starting_year=starting_year,
        cost_estimate_original=cost_estimate_original,
        temporary_finve_number=False
    )
    db.session.add(finve)
    db.session.commit()
    return finve


def create_budget(row, finve):
    """
    Creates a Budget object from a row of data and a FinVe object.
    Reads project content alias names and associates them with the budget.
    Raises an exception if any project content alias names are not found.
    Returns the created Budget object.
    """
    bezeichnung = row["bezeichnung"].split('\n')
    name = bezeichnung.pop(0)
    finance_titels = []
    for index, element in enumerate(bezeichnung):
        if signal_word_break_description in element:
            break
        element = element.replace(" Erläuterung:", "").replace('Erläuterung:', "")
        finance_titels.append(element)
    finance_titels.pop(0)
    finance_titels.insert(0, "all")
    finance_titels = [item for item in finance_titels if item != '']
    connected_projects = bezeichnung[index + 1:]
    budget_pc = []
    missing_projects = []

    if SAMMEL_FINVE is True:
        pc_alias_names = read_pc_alias_names()
        for pc_name in connected_projects:
            pc_name = pc_name.replace("‐   ", "")
            try:
                project = ProjectContent.query.filter(ProjectContent.name == pc_name).scalar()
            except sqlalchemy.exc.MultipleResultsFound as e:
                logging.info(f"Multiple Projects with name {pc_name} found (exact match). Looking for csv index")
                project = None
            if project is None:
                try:
                    project = ProjectContent.query.filter(ProjectContent.name.like(f"%{pc_name}%")).scalar()
                except sqlalchemy.exc.MultipleResultsFound as e:
                    logging.info(f"Multiple Projects with name {pc_name} found (LIKE Around). Looking for csv index")
                    project = None
            if project is None:
                pc_name_alternativ = pc_name.replace('‐', '%%')
                try:
                    project = ProjectContent.query.filter(ProjectContent.name.like(f"%{pc_name_alternativ}%")).scalar()
                except sqlalchemy.exc.MultipleResultsFound as e:
                    logging.info(f"Multiple Projects with name {pc_name} found (alternative names). Looking for csv index")
                    project = None
            if project is None:
                if pc_name in pc_alias_names.keys():
                    pc_id = pc_alias_names[pc_name]
                    project = ProjectContent.query.filter(ProjectContent.id == pc_id).scalar()
                else:
                    missing_projects.append(pc_name)
            if project:
                logging.info(f"Project with name {pc_name} found")
                budget_pc.append(project)

    if missing_projects:
        if len(missing_projects) == 1 and missing_projects[0] == '':
          missing_projects = []
        else:
            raise ValueError(f"Projects with the following names not found: {', '.join(missing_projects)}")

    # the budget has total cost and cost for specific bduget titels. In the row, this are separated by \n
    cost_df = fill_cost_template(row, finance_titels)

    budget = Budget(
        budget_year=YEAR,
        fin_ve=finve.id,
        sammel_finve=SAMMEL_FINVE,
        starting_year=int(row["Aufnahme in EP oder Abschluss FinVe"]),
        cost_estimate_original=int(row["ursprünglich"]),
        cost_estimate_last_year=(lambda x: None if pd.isna(x) else int(x) if str(x).isdigit() else None)(
            row["Vorjahr"]),
        delta_previous_year=(lambda x: None if pd.isna(x) else int(x) if str(x).isdigit() else None)(
            row["Entwicklung zu Vorjahr absolut"]),
        delta_previous_year_relativ=(lambda x: None if pd.isna(x) else int(x) if str(x).isdigit() else None)(
            row["Entwicklung zu Vorjahr relativ"]),
        delta_previous_year_reasons=row["Gründe"],
    )

    budget = cost_df_to_budget(cost_df, budget)

    finve_pc_current = finve.project_contents

    # compare finve_pc_current and budget_pc
    # if there are new project contents, add them to the finve
    for pc in budget_pc:
        if pc not in finve_pc_current:
            finve.project_contents.append(pc)
            logging.debug(f"Added project content {pc.name} to FinVe {finve.id}")
    db.session.commit()

    return budget


def add_finve_and_budget(result_df):
    """
    Iterates through the processed DataFrame and adds FinVe and Budget entries to the database.
    Commits the transactions for each entry.
    """
    for index, row in result_df.iterrows():
        finve_nr = row['lfd_nr']
        try:
            finve = FinVe.query.filter(FinVe.id == finve_nr).scalar()
        except sqlalchemy.exc.MultipleResultsFound as e:
            raise ValueError(f"Multiple FinVe with id {finve_nr} found")
        if finve is None:
            finve = create_finve(row, finve_nr)

        budget = Budget.query.filter(Budget.fin_ve == finve_nr, Budget.budget_year == YEAR).scalar()
        if budget is None:
            budget = create_budget(row, finve)
            db.session.add(budget)
        db.session.commit()


if __name__ == "__main__":
    result_df = read_and_prepare_data()
    add_finve_and_budget(result_df)