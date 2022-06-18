import pandas
import geopandas
import geoalchemy2
import logging

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
        # TODO: Add a try and throw exception if a key misses - error key not found please check input dictionary and
        #  naming of input file
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
        shp_data = shp_data.rename(columns={"coord":"coordinates"})

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

    def projectdata_to_postgres(self):
        """
        takes some projectdata in .csv .xlsx or somewhat and takes at to the postgres DB
        :return:
        """
        pass



if __name__ == '__main__':
    Counties = prosd.models.Counties
    filepath_shp = '/Users/jonas/PycharmProjects/pros/example_data/counties/georef-germany-kreis-millesime.shp'
    column_names = {}

    DbInput = DBManager()

    DbInput.shp_to_counties(filepath_shp=filepath_shp, column_names=column_names, overwrite=True, model=Counties)


