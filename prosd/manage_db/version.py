"""
A class that creates a infrastrucutre state that differs from the railway by adding project_contents
"""

import pandas
import sqlalchemy

from prosd.models import RailwayLine, RailwayStation
from prosd import db


class Version:
    def __init__(self, scenario):
        self.scenario = scenario
        self.project_contents = scenario.project_contents
        self.infra = self._create_railway_df()
        self.load_changes()

    def load_changes(self):
        self._load_projects_to_version()

    def add_projectcontents_to_version_temporary(self, pc_list, update_infra=False, use_subprojects=False):
        if update_infra:  # if True, the project content changes are added to the self.infra dataframes
            for pc in pc_list:
                self.load_single_project_to_version(pc=pc, use_subprojects=use_subprojects)

    def prepare_commit_project_content(self, project_content):
        """
        commits a projectcontent to the database, if the project content does not exists.
        The problem is, that the projectcontent may bring some changed railway infrastructure data.
        This infrastructure data may not be updated in the database.
        :return:
        """
        # check if project_content exists:
        if sqlalchemy.inspect(project_content).persistent == True:
            return project_content

        # remove all changes to stations that the project_content may bring with.
        stations = project_content.railway_stations
        old_stations = []
        for station in stations:
            old_station = RailwayStation.query.get(station.id)
            old_stations.append(old_station)

        project_content.railway_stations = old_stations

        # remove all changes to railway_lines that the project_content may bring with
        lines = project_content.railway_lines
        old_lines = []
        for line in lines:
            old_line = RailwayLine.query.get(line.id)
            old_lines.append(old_line)

        project_content.railway_lines = old_lines

        return project_content

    def _create_railway_df(self):
        infra = dict()
        columns_rl_lines = ['railway_line_id', 'railway_line_model']
        railway_lines = RailwayLine.query.with_entities(RailwayLine.id, RailwayLine).order_by(RailwayLine.id).all()
        infra["railway_lines"] = pandas.DataFrame(
            railway_lines,
            columns=columns_rl_lines
        )

        infra["railway_stations"] = pandas.DataFrame(
            RailwayStation.query.with_entities(RailwayStation.id, RailwayStation).order_by(RailwayStation.id).all(),
            columns=["railway_station_id", "railway_station_model"]
        )
        return infra

    def _load_projects_to_version(self):
        for pc in self.project_contents:
            self.load_single_project_to_version(pc, use_subprojects=True)

    def load_single_project_to_version(self, pc, use_subprojects=True):
        if use_subprojects is True:
            sub_projects = pc.sub_project_contents
            if len(sub_projects) > 0:
                pc_list = sub_projects
            else:
                pc_list = [pc]
        else:
            pc_list = [pc]

        for pc in pc_list:
            for line in pc.railway_lines:
                # get the correct railwayline and remove that from the dataFrame
                rl_changed = self.get_railwayline_model(railwayline_id=line.id)
                if pc.elektrification is True:
                    rl_changed = self._add_electrification(railway_line=rl_changed)
                rl_changed = self._change_closing(project_content=pc, railway_line=rl_changed)
                # Here can be more changes added
                self._change_infrastructure_df(railway_line_changed=rl_changed)

            for station in pc.railway_stations:
                rs_changed = self.infra["railway_stations"][self.infra["railway_stations"].railway_station_id == station.id][
                    "railway_station_model"].iloc[0]
                self.infra["railway_stations"] = self.infra["railway_stations"][
                    self.infra["railway_stations"].railway_station_id != station.id]

                rs_changed = self._add_charging_station(project_content=pc, railway_station=rs_changed)
                db.session.expunge(rs_changed)
                # Here can be added some more

                rs_df = pandas.DataFrame([[station.id, rs_changed]], columns=['railway_station_id', 'railway_station_model'])
                self.infra["railway_stations"] = pandas.concat([self.infra["railway_stations"], rs_df])

    def _change_infrastructure_df(self, railway_line_changed):
        # remove the line_model from df and add the changed line
        railway_line_id = railway_line_changed.id
        if sqlalchemy.inspect(railway_line_changed).detached is False:
            db.session.expunge(railway_line_changed)
        self.infra["railway_lines"] = self.infra["railway_lines"][
            self.infra["railway_lines"].railway_line_id != railway_line_id]
        rl_df = pandas.DataFrame([[railway_line_id, railway_line_changed]], columns=['railway_line_id', 'railway_line_model'])
        self.infra["railway_lines"] = pandas.concat([self.infra["railway_lines"], rl_df])

    def get_railwayline_model(self, railwayline_id):
        """
        returns the railwaymodel (which can be modified and so differ from the railwayline_model in the database
        :param railwayline_id:
        :return:
        """
        railway_line = self.infra["railway_lines"].railway_line_model[self.infra["railway_lines"].railway_line_id == railwayline_id].iloc[0]

        return railway_line

    def get_railwayline_no_catenary(self):
        """
        returns the railwayline and the ids for all lines with no catenary
        :return:
        """
        railway_line_ids = []
        for index, row in self.infra["railway_lines"].iterrows():
            line = row.railway_line_model
            if line.catenary==False:
                railway_line_ids.append(line.id)

        return railway_line_ids

    def add_electrification_for_rw_lines(self, rw_lines):
        """

        :param rw_lines:
        :return:
        """
        for line_db in rw_lines:
            line_infra_version = self.get_railwayline_model(line_db.id)
            railway_line_changed = self._add_electrification(railway_line=line_infra_version)
            self._change_infrastructure_df(railway_line_changed=railway_line_changed)

    def remove_electrification_for_rw_lines(self, rw_lines):
        """
        remove electrification for rw_lines
        :param rw_lines: list of railway_lines
        :return:
        """
        for line_db in rw_lines:
            line_infra_version = self.get_railwayline_model(line_db.id)
            railway_line_changed = self._remove_electrification(railway_line=line_infra_version)
            self._change_infrastructure_df(railway_line_changed=railway_line_changed)

    def _add_electrification(self, railway_line):
        railway_line.electrified = True
        railway_line.catenary = True
        railway_line.voltage = 15
        railway_line.dc_ac = 'ac'

        return railway_line

    def _remove_electrification(self, railway_line):
        railway_line.electrified = False
        railway_line.catenary = False
        railway_line.voltage = None
        railway_line.dc_ac = None
        return railway_line

    def _change_closing(self, project_content, railway_line):
        if project_content.closure:
            railway_line.closed = True
        return railway_line

    def _add_charging_station(self, project_content, railway_station):
        if project_content.charging_station:
            railway_station.charging_station = True

        return railway_station
