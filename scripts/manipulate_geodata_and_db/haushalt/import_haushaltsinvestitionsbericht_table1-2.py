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


def read_pc_alias_names():
    pc_alias_names = {}
    # read csv to dataframe
    df = pd.read_csv(filepath_alias_csv)

    for _, row in df.iterrows():
        alias_name = row['alias_name']
        pc_name = row['project_content_id']
        pc_alias_names[alias_name] = pc_name

    return pc_alias_names


def create_finve(row, finve_id):
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
    bezeichnung = row["bezeichnung"].split('\n')
    name = bezeichnung.pop(0)

    finance_titels = []

    for index, element in enumerate(bezeichnung):
        # remove element from list
        if signal_word_break_description in element:
            break
        element = element.replace(" Erläuterung:", "")
        finance_titels.append(element)

    # remove first element, because this is called "davon:" which is irrelevant
    finance_titels.pop(0)
    # add element to beginn of list which is called "all"
    finance_titels.insert(0, "all")

    connected_projects = bezeichnung[index+1:]

    # search for the connected_projects
    budget_pc = []
    if SAMMEL_FINVE is True:
        pc_alias_names = read_pc_alias_names()
        for pc_name in connected_projects:
            pc_name = pc_name.replace("‐   ", "")
            # search for the project
            # first try if a project with the name exists

            project = ProjectContent.query.filter(ProjectContent.name == pc_name).scalar()

            if project is None:
                project = ProjectContent.query.filter(ProjectContent.name.like(f"%{pc_name}%")).scalar()

            if project is None:
                pc_name_alternativ = pc_name.replace('‐', '%%')
                try:
                    project = ProjectContent.query.filter(ProjectContent.name.like(f"%{pc_name_alternativ}%")).scalar()
                except sqlalchemy.exc.MultipleResultsFound as e:
                    logging.info(f"Multiple Projects with name {pc_name} found. Looking for csv index")
                    project = None

            if project is None:
                if pc_name in pc_alias_names.keys():
                    pc_id = pc_alias_names[pc_name]
                    project = ProjectContent.query.filter(ProjectContent.id == pc_id).scalar()
                else:
                    raise ValueError(f"Project with name {pc_name} not found")

            logging.info(f"Project with name {pc_name} found")

            # add the project to the finve
            budget_pc.append(project)

    budget = Budget(
        budget_year=YEAR,
        fin_ve=finve.id,
        sammel_finve=SAMMEL_FINVE,
    )

    return budget


# read the table as dataframe
df = pd.read_excel(file_path)

# drop the first three not needed rows
df = df.drop(df.index[:DROP_FIRST_ROWS])

# drop the empty column 4
df = df.drop(df.columns[EMPTY_COLUMN], axis=1)

# Replace column names
df.columns = [
    "lfd_nr", "finve_nr", "bedarfsplan_schiene", "bezeichnung",
    "Aufnahme in EP oder Abschluss FinVe", "ursprünglich",
    "Vorjahr", "aktuell", "Entwicklung zu Vorjahr absolut",
    "Entwicklung zu Vorjahr relativ", "Gründe",
    f"Verausgabt bis {YEAR-1}", f"Bewilligt {YEAR}",
    f"nach {YEAR} übertragene Ausgabereste", f"Veranschlagt {YEAR+1}",
    f"Vorbehalten {YEAR+2}"
]

# Replace NaN values with empty strings
df = df.fillna('')

result = []
current_row = None

for _, row in df.iterrows():
    if row['lfd_nr']:  # Check if lfd_nr is not empty
        if current_row is not None:
            result.append(current_row)
        current_row = row.copy()
    else:
        for col in df.columns[1:]:
            if isinstance(current_row[col], (int, float)) or isinstance(row[col], (int, float)):
                # Handle numeric values: if the row value is empty, treat it as zero
                if row[col] == '':
                    continue  # Skip concatenation if row[col] is an empty string
                current_row[col] += float(row[col]) if row[col] != '' else 0
            else:
                # Handle string values
                current_row[col] += ' ' + row[col]

if current_row is not None:
    result.append(current_row)

# Convert the result list into a DataFrame
result_df = pd.DataFrame(result)

for index, row in result_df.iterrows():
    finve_nr = row['lfd_nr']  # in this case here, there is only finve_nr

    # check if the finve exists
    finve = FinVe.query.filter(FinVe.id == finve_nr).scalar()
    if finve is None:
        finve = create_finve(row, finve_nr)

    # create the budget
    # check if budget for this finve and year already exists
    budget = Budget.query.filter(Budget.fin_ve == finve_nr, Budget.budget_year == YEAR).scalar()

    if budget is None:
        budget = create_budget(row, finve)
        db.session.add(budget)

    db.session.commit()





