import numpy as np
import pandas as pd
import logging

from prosd import db
from prosd.models import Netzzustandsbericht

COLUMN_NAMES = [
    "Kategorie",
    "Einheit",
    "all",
    "bridge",
    "tunnel",
    "support_structure",
    "tracks",
    "switches",
    "crossing",
    "interlocking",
    "catenary"
]

columns_ignore = [
    "Kategorie",
    "Einheit"
]

values_row = {
    "replacement_value": np.nan,
    "replacement_value_corrected": np.nan,
    "replacement_distribution": np.nan,
    "amount_portfolio": np.nan,
    "amount_portfolio_rated": np.nan,
    "note": np.nan,
    "note_1": np.nan,
    "note_2": np.nan,
    "note_3": np.nan,
    "note_4": np.nan,
    "note_5": np.nan,
    "note_6": np.nan,
    "count_1": np.nan,
    "count_2": np.nan,
    "count_3": np.nan,
    "count_4": np.nan,
    "count_5": np.nan,
    "count_6": np.nan,
    "backlog_condition": np.nan,
    "backlog_condition_urgent": np.nan,
    "backlog_condition_urgent_relative": np.nan,
    "backlog_age_relative": np.nan,
}


translate_row_names = {
    "Wiederbeschaffungswert": "replacement_value",
    "Bewerteter Wiederbeschaffungswert": "replacement_value_corrected",
    "Verteilung": "replacement_distribution",
    "Portfolio": "amount_portfolio",
    "Bewertetes Portfolio": "amount_portfolio_rated",
    "Einheit": "unit",
    "Zustansnote": "note",
    "Notenverteilung Note 1": "note_1",
    "Notenverteilung Note 2": "note_2",
    "Notenverteilung Note 3": "note_3",
    "Notenverteilung Note 4": "note_4",
    "Notenverteilung Note 5": "note_5",
    "Notenverteilung Note 6": "note_6",
    "Notenverteilung absolut Note 1": "count_1",
    "Notenverteilung absolut Note 2": "count_2",
    "Notenverteilung absolut Note 3": "count_3",
    "Notenverteilung absolut Note 4": "count_4",
    "Notenverteilung absolut Note 5": "count_5",
    "Notenverteilung absolut Note 6": "count_6",
    "Zustandsbasierter Nachholbedarf absolut": "backlog_condition",
    "Dringender Nachholbedarf": "backlog_condition_urgent",
    "Zustandsbasierter Nachholbedarf": "backlog_condition_urgent_relative",
    "Altersbasierter Nachholbedarf": "backlog_age_relative",
}

REMOVE_KEYS = [
    "count_1_all",
    "count_2_all",
    "count_3_all",
    "count_4_all",
    "count_5_all",
    "count_6_all",
]

INDEX_UNIT = 5


def read_file(filename):
    """
    Read the netzzustandsbericht file and return the gesamtnetz and hochleistungsnetz dataframes.
    :param filename:
    :return: gesamtnetz, hochleistungsnetz
    """
    gesamtnetz = pd.read_excel(filename, sheet_name='gesamtnetz', names=COLUMN_NAMES)
    hochleistungsnetz = pd.read_excel(filename, sheet_name='hochleistungsnetz', names=COLUMN_NAMES)

    return gesamtnetz, hochleistungsnetz


def import_to_db(dataframe, year, link, hlk=False):
    """
    Import the dataframe to the database model Netzzustandsbericht.
    :param dataframe:
    :return:
    """
    all_values = {
        "year": year,
        "link": link,
        "hlk": hlk
    }

    # iterate through dataframe rows
    # create for each row a dict as a copy from values_row. Change the key by adding the row name (use the row translate dict)
    # add all entrys from the values_row dict to the values dict
    for name, column in dataframe.items():
        if name in columns_ignore:
            continue

        values = values_row.copy()
        if hlk == True:
            values.pop("backlog_condition_urgent_relative")
            values.pop("backlog_age_relative")
        values = {key + "_" + name: value for key, value in values.items()}  # changes the keys depending to row name

        column_values = column.to_frame().T
        column_values = column_values.drop(column_values.columns[INDEX_UNIT], axis=1)
        column_values.columns = list(values.keys())

        for key, value in column_values.items():
            value = correct_values(value.iloc[0])
            values[key] = value

        all_values.update(values)

    # remove some key-values that are not needed
    var = {key: all_values.pop(key) for key in REMOVE_KEYS}
    if 'backlog_condition_urgent_relative_all' in all_values.keys():
        all_values['backlog_condition_urgent_value_all'] = all_values.pop('backlog_condition_urgent_relative_all')

    if "backlog_age_relative_all" in all_values.keys():
        all_values['backlog_age_value_all'] = all_values.pop('backlog_age_relative_all')

    # add the values to the bericht object
    bericht = Netzzustandsbericht(**all_values)

    db.session.add(bericht)
    db.session.commit()
    logging.info(f'Added budget for year {year} to database.')


def correct_values(value):
    if value == '-':
        return np.nan
    return value


if __name__ == "__main__":
    year = 2021
    link = 'https://www.dbinfrago.com/resource/blob/12645038/fb8f1fe8d9c1c1443e201fedf4893a35/Netzzustandsbericht-DB-Netz-AG-2021-data.pdf'
    filename = '../../../example_data/import/netzzustandsbericht/2021.xlsx'
    gesamt, hochleistung = read_file(filename)
    import_to_db(gesamt, year, link, hlk=False)
    import_to_db(hochleistung, year, link, hlk=True)

