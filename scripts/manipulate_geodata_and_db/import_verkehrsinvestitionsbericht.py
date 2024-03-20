import numpy
import pandas
import re
import logging
import sqlalchemy

from prosd import db
from prosd.models import Budget, FinVe

# SETTINGS
YEAR = 2020
DROP_FIRST_ROWS = 3
logging.basicConfig(level=logging.INFO)

IGNORE_COLUMNS_VALUES = [
    "Lfd. Nr.",
    "Nr. FinVe",
    "Nr.\nBedarfsplan Schiene",
    "Bezeichnung der Investitionsmaßnahme",
    "Aufnahme in EP oder Abschluss FinVe",
    "Gründe"
]
correct_header = {
    "voraussichtliche Gesamtausgaben": "Aufnahme in EP oder Abschluss FinVe",
    "Unnamed: 5": "ursprünglich",
    "Unnamed: 6": "Vorjahr",
    "Unnamed: 7": "aktuell",
    "Gesamtausgabenentwicklung": "Entwicklung zu Vorjahr absolut",
    "Unnamed: 9": "Entwicklung zu Vorjahr relativ",
    "Unnamed: 10": "Gründe",
    "Ausgaben": f"Verausgabt bis {YEAR-1}",
    "Unnamed: 12": f"Bewilligt {YEAR}",
    "Unnamed: 13": f"nach {YEAR} übertragene Ausgabereste",
    "Unnamed: 14": f"Veranschlagt {YEAR+1}",
    "Unnamed: 15": f"Vorbehalten {YEAR+2}"

}
translation = {
    "ursprünglich": "cost_estimate_original",
    "Vorjahr": "cost_estimate_last_year",
    "aktuell": "cost_estimate_actual",
    "Entwicklung zu Vorjahr absolut": "delta_previous_year",
    "Entwicklung zu Vorjahr relativ": "delta_previous_year_relativ",
    "Gründe": "delta_previous_year_reasons",
    f"Verausgabt bis {YEAR-1}": "spent_two_years_previous",
    f"Bewilligt {YEAR}": "allowed_previous_year",
    f"nach {YEAR} übertragene Ausgabereste": "spending_residues",
    f"Veranschlagt {YEAR+1}": "year_planned",
    f"Vorbehalten {YEAR+2}": "next_years"
}
row_templates = {
    "cost_estimate_original": None,
    "cost_estimate_last_year": None,
    "cost_estimate_actual": None,
    "delta_previous_year": None,
    "delta_previous_year_relativ": None,
    "delta_previous_year_reasons": None,
    "spent_two_years_previous": None,
    "allowed_previous_year": None,
    "spending_residues": None,
    "year_planned": None,
    "next_years": None
}

def create_category():
    categories_template = {
        "all": row_templates.copy(),
        "Kap. 1202, Titel 891 01": row_templates.copy(),
        "Kap. 1202, Titel 891 02": row_templates.copy(),
        "Kap. 1202, Titel 891 03": row_templates.copy(),
        "Kap. 1202, Titel 891 04": row_templates.copy(),
        "Kap. 1202, Titel 861 01": row_templates.copy(),
        "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐": row_templates.copy(),
        "Kap. 1210 (alt), Titel 891 72 (ZIP)": row_templates.copy(),
        "Kap. 1202, Titel 891 11 (zusätzl. Darstellg. LUFV)": row_templates.copy(),
        "Kap. 6091 (alt), Titel 891 21‐ ITF ‐": row_templates.copy(),
        "nachrichtlich: Beteiligung Dritter": row_templates.copy(),
        "nachrichtlich: Eigenmittel der EIU gemäß BUV": row_templates.copy()
    }
    return categories_template

translate_category_to_db = {
    "all": "",
    "Kap. 1202, Titel 891 01": "_891_01",
    "Kap. 1202, Titel 891 02": "_891_02",
    "Kap. 1202, Titel 891 03": "_891_03",
    "Kap. 1202, Titel 891 04": "_891_04",
    "Kap. 1202, Titel 861 01": "_861_01",
    "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐": "_891_91",
    "Kap. 1210 (alt), Titel 891 72 (ZIP)": "_891_72",
    "Kap. 1202, Titel 891 11 (zusätzl. Darstellg. LUFV)": "_891_11",
    "Kap. 6091 (alt), Titel 891 21‐ ITF ‐": "_891_21",
    "nachrichtlich: Beteiligung Dritter": "_third_parties",
    "nachrichtlich: Eigenmittel der EIU gemäß BUV": "_equity"
}
ignore_rows_investment_title = [
    "davon:",
    "Unterlagen entsprechend § 24 Abs. 4 BHO liegen noch nicht (vollständig) vor."
]
translate_category_corrector = {
    'Kap. 1210, Titel 891 72 (ZIP)': "Kap. 1210 (alt), Titel 891 72 (ZIP)",
    "Kap. 1202 (alt), Titel 891 91‐  IIP Schiene ‐ Kap. 6091 (alt),": "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐",
    'Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐ Kap. 6091 (alt)': "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐",
    'Kap. 1202 (alt), Titel 891 91- IIP Schiene -': "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐",
    "Kap. 1202 (alt), Titel 891 91-  IIP Schiene -": "Kap. 1202 (alt), Titel 891 91‐ IIP Schiene ‐",
    'Titel 891 21‐ ITF ‐': "Kap. 6091 (alt), Titel 891 21‐ ITF ‐",
    "Kap. 6091 (alt), Titel 891 21- ITF -": "Kap. 6091 (alt), Titel 891 21‐ ITF ‐",
    "nachrichtlich:\xa0Eigenmittel\xa0der\xa0EIU\xa0gemäß\xa0BUV": "nachrichtlich: Eigenmittel der EIU gemäß BUV"
}


class ExcelPreparationError(Exception):
    def __init__(self, message):
        super().__init__(message)


class KeyNotYetExisting(Exception):
    def __init__(self, message):
        super().__init__(message)


def translate_category_dict(categories):
    translated_categories = {}
    for category in categories:
        translated_categories[category] = categories[category].copy()
        values = translated_categories[category]
        for value in values:
            values[value+translate_category_to_db[category]] = values.pop(value)
    return translated_categories


def add_budget_category_to_db(budget, categories):
    for category in categories:
        for key, value in categories[category].items():
            if value is None:
                continue
            if hasattr(budget, key):
                setattr(budget, key, value)
    return budget


def create_name_finve(row):
    finve = row["Bezeichnung der Investitionsmaßnahme"].split("davon:")[0]
    finve = finve.replace('\n', '')
    finve = finve.replace("Unterlagen entsprechend § 24 Abs. 4 BHO liegen noch nicht (vollständig) vor.",'')
    return finve


def create_budget(row):
    lfd_nr = row["Lfd. Nr."]
    fin_ve = row["Nr. FinVe"]
    bedarfsplan_number = row["Nr.\nBedarfsplan Schiene"]

    # there are cases where this thre columns are in one cell
    if len(lfd_nr) > 5:
        elements = lfd_nr.split()
        lfd_nr = elements[0]
        fin_ve = int(elements[1])
        bedarfsplan_number = elements[2] + " " + elements[3]

    # clear the starting year
    if isinstance(row["Aufnahme in EP oder Abschluss FinVe"], str):
        if row["Aufnahme in EP oder Abschluss FinVe"][:4] == "vsl.":
            row["Aufnahme in EP oder Abschluss FinVe"] = int(row["Aufnahme in EP oder Abschluss FinVe"][4:])

    # clear the cost_estimate_original
    if row["ursprünglich"] == '‐' or row["ursprünglich"] == '‐':
        cost_estimate_original = None
    else:
        cost_estimate_original = row["ursprünglich"]

    budget = Budget(
        budget_year=YEAR,
        lfd_nr=lfd_nr,
        fin_ve=fin_ve,
        bedarfsplan_number=bedarfsplan_number,
        starting_year=row["Aufnahme in EP oder Abschluss FinVe"]
    )

    # check if reaseon exists and add
    if isinstance(row["Gründe"], str):
        budget.delta_previous_year_reasons = row["Gründe"]

    # check if finve exists -> if not create one
    finve_temporary = False
    if fin_ve == '‐':
        fin_ve = None

    finve = FinVe.query.get(fin_ve)

    # TODO: Add search for fitting lfd_nr -> dafür muss ich das in FinVe ergänzen

    if finve is None or fin_ve is numpy.nan or fin_ve is None:
        name_finve = create_name_finve(row)
        finve = FinVe.query.filter_by(name=name_finve).first()
        finve_temporary = True


    if finve is None:
        name_finve = create_name_finve(row)

        finve = FinVe(
            name=name_finve,
            starting_year=row["Aufnahme in EP oder Abschluss FinVe"],
            cost_estimate_original=cost_estimate_original,
            temporary_finve_number=finve_temporary
        )

        if fin_ve is not numpy.nan or fin_ve is not None:
            finve.id = fin_ve

        if str(finve.id) == 'nan':
            finve.id = None

        if str(finve.cost_estimate_original) == 'nan':
            finve.cost_estimate_original = None

        if str(finve.starting_year) == 'nan':
            finve.starting_year = None

        db.session.add(finve)
        db.session.commit()
        logging.info(f'Created new FinVe with id {finve.id} and name {finve.name} for budget {budget.lfd_nr}.')

    budget.fin_ve = finve.id

    categories = get_cash_values(row)
    budget = add_budget_category_to_db(budget, categories)
    return budget


def convert_german_number_to_int(number):
    if number == '‐' or number == '‐ ' or number == '-':
        return 0

    number = number.replace(".", "")
    number = number.replace(",", ".")

    # number negativ but wrong minus symbol
    if number[0] == '‐':
        number = number.replace('‐', '-')
        number = number.replace(' ','')

    # number is percent but with symbol
    if number[-1] == '%':
        number = number[:-1]
        number = float(number) / 100

    return int(number)


def clean_element_name(name):
    name = re.sub("  ", " ", name)  # removs double spaces
    name = name.strip()  # removes spaces at the beginning and end
    return name


def create_element_index(row):
    elements_index = {}
    index_cleaned = 0

    # check if row does not fit the template -> raise error
    if row["Bezeichnung der Investitionsmaßnahme"] is numpy.nan:
        raise ExcelPreparationError(f"Excel preparation error in row {row}")

    if "\n" in row["Bezeichnung der Investitionsmaßnahme"]:
        element_names = row["Bezeichnung der Investitionsmaßnahme"].split("\n")
        for index, name in enumerate(element_names):
            name = clean_element_name(name)
            if name in translate_category_corrector.keys():
                name = translate_category_corrector[name]
            if name not in translate_category_to_db.keys() and index !=0:
                continue
            if name not in translate_category_to_db.keys() and index == 0 and row["Lfd. Nr."] is numpy.nan:
                # in this case the is are annotation in a row not the first row of the budget which is irrelevant
                continue
            # some titles are spelled differently → gets corrected here
            elements_index[index_cleaned] = name
            index_cleaned += 1
    else:
        # some titles are spelled differently → gets corrected here
        if row["Bezeichnung der Investitionsmaßnahme"] in translate_category_corrector.keys():
            row["Bezeichnung der Investitionsmaßnahme"] = translate_category_corrector[row["Bezeichnung der Investitionsmaßnahme"]]
        element = clean_element_name(row["Bezeichnung der Investitionsmaßnahme"])
        elements_index[0] = element

    # overwrite first index, if the row is the first row of a budget row in the pdf
    if str(row["Lfd. Nr."]) != str(numpy.nan):
        elements_index[0] = "all"

    return elements_index


def get_cash_values(row):
    categories = create_category()

    elements_index = create_element_index(row)

    for index, value in row.items():
        if index in IGNORE_COLUMNS_VALUES:
            continue
        if isinstance(value, int) or isinstance(value, float):
            if value is numpy.nan:
                value = 0
            try:
                categories[elements_index[0]][translation[index]] = convert_german_number_to_int(str(value))
            except KeyError as e:
                raise KeyNotYetExisting(f"KeyError with {elements_index} and index 0 in row {row} with {e}")
        else:
            if value == '‐':
                categories[elements_index[0]][translation[index]] = 0
            else:
                values = value.split("\n")
                for number_index, number in enumerate(values):
                    try:
                        categories[elements_index[number_index]][translation[index]] = convert_german_number_to_int(str(number))
                    except KeyError as e:
                        raise KeyNotYetExisting(f"KeyError with {elements_index} and {number_index} in row {row} with {e}")
    categories = translate_category_dict(categories)
    return categories


def update_budget(budget, row, title_investment):

    if row["Bezeichnung der Investitionsmaßnahme"] is numpy.nan:
        # check how many investment titles are expected in that row
        if isinstance(row["aktuell"], str):
            count_titles = len(row["aktuell"].split('\n'))
        if isinstance(row["aktuell"], int):
            count_titles = 1
        if isinstance(row["aktuell"], float):
            count_titles = 1

        for index, title in enumerate(title_investment):
            title = clean_element_name(title)
            if title not in translate_category_to_db.keys():
                continue
            else:
                if count_titles == 1:
                    row["Bezeichnung der Investitionsmaßnahme"] = title
                if count_titles > 1:
                    row["Bezeichnung der Investitionsmaßnahme"] = "\n".join(title_investment[index:index+count_titles])
                break

        # remove all the used title from list
        title_investment = title_investment[index+1:]
    categories = get_cash_values(row)
    budget = add_budget_category_to_db(budget, categories)
    return budget, title_investment


def add_all_budgets(filename):
    df = pandas.read_excel(filename)

    # prepare dataframe
    df = df.rename(columns=correct_header)
    df = df.iloc[DROP_FIRST_ROWS:]

    # iterate through columns and pop out project for further processing
    budget = None
    finished_budgets = []
    title_investment = None  # needed for some correction of transfer pdf to excel

    for index, row in df.iterrows():
        if str(row["Lfd. Nr."]) != str(numpy.nan):
            if isinstance(budget, Budget):  # previos budget is finished
                try:
                    db.session.add(budget)
                    db.session.commit()
                except sqlalchemy.exc.IntegrityError as e:
                    logging.info(f"UniqueViolation for {budget.lfd_nr}, {budget.budget_year}. continued with next budget.")
                    db.session.rollback()
                finished_budgets.append(budget)

            title_investment = row["Bezeichnung der Investitionsmaßnahme"].split("\n")
            if row["ursprünglich"] is numpy.nan:
                # there are no investment volumes in this row. This is expected in a row below.
                # to trigger the correct behavior in update_budget, we add the key "all" to the list at first position, because "all investments" are in the next row of a budget
                title_investment.insert(0, "all")
                logging.debug(f"no investment volumes for lfd. nr. {row['Lfd. Nr.']}")
            budget = create_budget(row)

        else:
            # there are cases where there is an empty row with only the investment title 'davon'
            if row["Bezeichnung der Investitionsmaßnahme"] in ignore_rows_investment_title:
                continue
            budget, title_investment = update_budget(budget, row, title_investment)

    # db.session.add_all(finished_budgets)
    # db.session.commit()

    # there is a last budget that is not added to db
    db.session.add(budget)
    db.session.commit()

if __name__ == "__main__":
    filename = f'../../example_data/import/verkehrsinvestitionsbericht/{YEAR}/{YEAR}_table1-1.xlsx'
    add_all_budgets(filename)