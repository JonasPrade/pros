import pandas
import logging

from prosd import db
from prosd.models import RailwayStation, ProjectContent


def add_station_to_pc(db_kuerzel, pc_id):
    pc = ProjectContent.query.get(pc_id)
    station = RailwayStation.query.filter(RailwayStation.db_kuerzel == db_kuerzel).scalar()
    if station is None:
        logging.error(f"No station found for {db_kuerzel}. Project {pc_id} no added station")
    else:
        pc.railway_stations.append(station)
    return pc


def read_excel(filepath):
    df = pandas.read_excel(filepath, usecols='A:B')
    return df


filepath = '../../example_data/import/station_to_projects/dtakt_stations_2.xlsx'
df = read_excel(filepath)

pcs = []
for index, data in df.iterrows():
    try:
        pc = add_station_to_pc(db_kuerzel=data.iloc[1], pc_id=data.iloc[0])
        pcs.append(pc)
    except Exception as e:
        logging.error(f"Error at {data.iloc[0]}: {e}")

db.session.add_all(pcs)
db.session.commit()
