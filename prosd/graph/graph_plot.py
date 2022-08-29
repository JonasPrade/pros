from prosd import db
from prosd.models import RailwayLine, RailwayPoint
import geoplot
import geopandas
import sqlalchemy
import matplotlib.pyplot as plt

def postgis_to_geodataframe(sql_statement, name_coordinates):
    gdf = geopandas.GeoDataFrame.from_postgis(
        sql=sql_statement,
        con=db.engine,
        geom_col=name_coordinates,
        crs=("epsg:4326")
    )
    return gdf


def plot_with_geoplot(stations, lines):
    fig, ax = plt.subplots(figsize=(20, 10))
    stations = geoplot.pointplot(stations, ax=ax)
    geoplot.polyplot(lines, ax=stations)
    for idx, row in stations.iterrows():
        plt.annotate(text=row['name'], xy=[row['coordinates'].x, row['coordinates'].y])
    fig.show()


query = db.session.query(RailwayPoint)
sql_statement = query.statement.compile(dialect=sqlalchemy.dialects.postgresql.dialect())
stations = postgis_to_geodataframe(sql_statement=sql_statement, name_coordinates="coordinates")

query = db.session.query(RailwayLine)
sql_statement = query.statement.compile(dialect=sqlalchemy.dialects.postgresql.dialect())
lines = postgis_to_geodataframe(sql_statement=sql_statement, name_coordinates="coordinates")

plot_with_geoplot(stations = stations.head(20), lines = lines)

