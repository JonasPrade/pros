import pandas
import geopandas
import geoalchemy2
import logging
from shapely.geometry.multipolygon import MultiPolygon
from shapely import wkt

import prosd.models
from prosd import db


class DBManager:
    def shp_to_counties(self, filepath_shp, column_names, model, model_state, overwrite=False):
        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp, encoding='utf-8')

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        states = model_state.query.all()
        states_dict = {}
        for state in states:
            states_dict[state.name] = state

        for index, row in shp_data.iterrows():
            state = states_dict[row.lan_name]
            county_input = model(
                code=row.krs_code,
                name=row.krs_name,
                type=row.krs_type,
                name_short=row.krs_name_sh,
                polygon=row.geo,
                state_id=state.id
            )
            db.session.add(county_input)
            db.session.commit()

        logging.info('finished import shp_to_counties')

    def shp_to_states(self, filepath_shp, model, overwrite=False):
        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp, encoding='utf-8')

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        states = model.query.all()
        for state in states:
            geo = shp_data[shp_data["GEN"]==state.name].geo.iloc[0]
            if wkt.loads(geo.data).geom_type == 'Polygon':
                geo=wkt.dumps(MultiPolygon([wkt.loads(geo.data)]))
            state.polygon = geo

        db.session.bulk_save_objects(states)
        db.session.commit()

        logging.info('finished import shp_to_counties')

    def shp_to_constituencies(self, filepath_shp, column_names, model, model_state, overwrite=False):
        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp, encoding='ISO-8859-1')

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        states = model_state.query.all()
        states_dict = {}
        for state in states:
            states_dict[state.name] = state

        for index, row in shp_data.iterrows():
            state = states_dict[row.LAND_NAME]
            county_input = model(
                id=row.WKR_NR,
                name=row.WKR_NAME.replace('\x96', '-'),
                polygon=row.geo,
                state_id=state.id
            )
            db.session.add(county_input)
            db.session.commit()

        logging.info('finished import shp_to_constituencies')

    def shp_to_railwaylines(self, filepath_shp, column_names, overwrite=False):
        """
        :param overwrite: if its True it will delete(!) all data of RailwayLines
        :param filepath_shp: str filepath
        :param column_names: dict which orders the imported columns of shapefile to names of sql
        gets an filepath to a .shp
        import .shp with geopandas
        geopandas to postgres
        Model exists -> use this (models.RailwayLine)
        :return:
        """

        if overwrite:
            db.session.query(prosd.models.RailwayLine).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp)

        # Changes title so they are same to SQLAlchemyModel. For that you have to input column_names dict
        column_names_reversed = {v: k for k, v in column_names.items()}
        columns_old = shp_data.columns
        columns_new = list()

        for column in columns_old:
            columns_new.append(column_names_reversed[column])
        shp_data.columns = columns_new

        # adding missing columns so all columns exists for model
        for column in column_names:
            if column in columns_new:
                continue
            else:
                shp_data[str(column)] = None

        # preparing coordinate
        shp_data['coord'] = shp_data['coordinates'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('coordinates', 1, inplace=True)
        shp_data = shp_data.rename(columns={"coord": "coordinates"})

        for index, row in shp_data.iterrows():
            railway_line_input = prosd.models.RailwayLine(
                mifcode=row.mifcode,
                streckennummer=row.streckennummer,
                direction=row.direction,
                length=row.length,
                from_km=row.from_km,
                to_km=row.to_km,
                electrified=row.electrified,
                number_tracks=row.number_tracks,
                vmax=row.vmax,
                type_of_transport=row.type_of_transport,
                coordinates=row.coordinates
            )
            # TODO bulk ad
            db.session.add(railway_line_input)
            db.session.commit()

        logging.info('added shp to RailwayLines')

    def shp_to_railwaypoints(self, filepath_shp, model, overwrite=False):
        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp, encoding='UTF-8')

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        objects = []
        for index, row in shp_data.iterrows():
            railway_point = model(
                mifcode=row.mifcode,
                route_number=row.streckennu,
                richtung=row.richtung,
                km_i=row.km_i,
                km_l=row.km_l,
                name=row.bezeichnun,
                type=row.art,
                db_kuerzel=row.kuerzel,
                coordinates=row.geo
            )
            objects.append(railway_point)

        db.session.add_all(objects)
        db.session.commit()

        logging.info('finished import shp_to_counties')

    def shp_to_tunnel(self, filepath_shp, model, overwrite=False):
        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp)

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        objects = []
        for index, row in shp_data.iterrows():
            railway_point = model(
                route_number_id=row.streckennu,
                richtung=row.richtung,
                von_km_i=row.von_km_i,
                bis_km_i=row.bis_km_i,
                von_km_l=row.von_km_l,
                bis_km_l=row.bis_km_l,
                length=row.laenge,
                name=row.bezeichnun,
                geometry=row.geo
            )
            objects.append(railway_point)

        db.session.add_all(objects)
        db.session.commit()

        logging.info('finished import shp_to_railwaylines')

    def shp_to_bridges(self, filepath_shp, overwrite=False):
        """
        import a shp-file to the Tabel Bridges
        :return:
        """
        model = prosd.models.RailwayBridge

        if overwrite:
            db.session.query(model).delete()
            db.session.commit()

        shp_data = geopandas.read_file(filepath_shp)

        shp_data['geo'] = shp_data['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        shp_data.drop('geometry', 1, inplace=True)

        objects = []
        for index, row in shp_data.iterrows():
            railway_point = model(
                route_number_id=row.streckennu,
                direction=row.richtung,
                von_km_i=row.von_km_i,
                bis_km_i=row.bis_km_i,
                von_km_l=row.von_km_l,
                bis_km_l=row.bis_km_l,
                length=row.laenge,
                geometry=row.geo
            )
            objects.append(railway_point)

        db.session.add_all(objects)
        db.session.commit()

        logging.info('finished import shp_to_railwaylines')


if __name__ == '__main__':
    States = prosd.models.States
    filepath_shp = ''
    DbInput = DBManager()

    DbInput.shp_to_states(
        filepath_shp=filepath_shp,
        model=States,
        overwrite=False
    )
