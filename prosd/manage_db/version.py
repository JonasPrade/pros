"""
A class that creates a infrastrucutre state that differs from the railway by adding project_contents
"""

import os
import pandas
import sqlalchemy

from prosd.models import ProjectContent, RailwayLine, RailwayStation
from prosd import db


def _change_electrification(project_content, railway_line):
    if project_content.elektrification:
        railway_line.electrified = True
        railway_line.catenary = True
        railway_line.voltage = 15
        railway_line.dc_ac = 'ac'

    return railway_line


def _change_charging_station(project_content, railway_station):
    if project_content.charging_station:
        railway_station.charging_station = True

    return railway_station


class Version:
    def __init__(self, filepath_changes):
        self._columns = ["project_content"]
        if filepath_changes is not None:
            self._filepath_changes = os.path.join(filepath_changes)
        else:
            self._filepath_changes = None
        self.project_contents = self._load_changes_csv()
        self.infra = self._create_railway_df()

    def load_changes(self):
        self._load_projects_to_version()

    def _load_changes_csv(self):
        if self._filepath_changes is not None:
            csv = pandas.read_csv(self._filepath_changes, header=None)
            csv.columns = self._columns
        else:
            csv = None
        return csv

    def save_changes(self):
        self.project_contents.to_csv(
            path_or_buf=self._filepath_changes
        )

    def add_projectcontents_to_version(self, pc_list, update_infra=False):
        for pc in pc_list:
            pc = self._prepare_commit_project_content(pc)
            pc_df = pandas.DataFrame([pc.id], columns=self._columns)
            self.project_contents = pandas.concat([self.project_contents, pc_df])

            if update_infra:  # if True, the project content changes are added to the self.infra dataframes
                self.load_single_project_to_version(pc=pc)

        db.session.add_all(pc_list)
        db.session.commit()
        self.save_changes()

    def _prepare_commit_project_content(self, project_content):
        """
        commits a projectcontent to the database, if the project content does not exists.
        The problem is, that the projectcontent may bring some changed railway infrastructure data.
        This infrastructure data may not be updated in the database.
        :return:
        """
        # check if project_content exists:
        if sqlalchemy.inspect(project_content).persistent == True:
            return

        # remove all changes to stations that the project_content may bring with.
        stations = project_content.railway_stations
        old_stations = []
        for station in stations:
            old_station = RailwayStation.query.get(station.id)
            old_stations.append(old_station)

        project_content.railway_stations = old_stations

        # remove all changes to railway_lines that the project_content may bring with
        lines = project_content.projectcontent_railway_lines
        old_lines = []
        for line in lines:
            old_line = RailwayLine.query.get(line.id)
            old_lines.append(old_line)

        project_content.projectcontent_railway_lines = old_lines

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
        for index, pc_id in self.project_contents.iterrows():
            pc = ProjectContent.query.get(int(pc_id["project_content"]))
            self.load_single_project_to_version(pc)

    def load_single_project_to_version(self, pc):
        for line in pc.projectcontent_railway_lines:
            # get the correct railwayline and remove that from the dataFrame
            rl_changed = self.infra["railway_lines"][self.infra["railway_lines"].railway_line_id == line.id][
                "railway_line_model"].iloc[0]
            self.infra["railway_lines"] = self.infra["railway_lines"][
                self.infra["railway_lines"].railway_line_id != line.id]

            rl_changed = _change_electrification(project_content=pc, railway_line=rl_changed)
            db.session.expunge(rl_changed)
            # Here can be more changes added

            rl_df = pandas.DataFrame([[line.id, rl_changed]], columns=['railway_line_id', 'railway_line_model'])
            self.infra["railway_lines"] = pandas.concat([self.infra["railway_lines"], rl_df])

        for station in pc.railway_stations:
            rs_changed = self.infra["railway_stations"][self.infra["railway_stations"].railway_station_id == station.id][
                "railway_station_model"].iloc[0]
            self.infra["railway_stations"] = self.infra["railway_stations"][
                self.infra["railway_stations"].railway_station_id != station.id]

            rs_changed = _change_charging_station(project_content=pc, railway_station=rs_changed)
            db.session.expunge(rs_changed)
            # Here can be added some more

            rs_df = pandas.DataFrame([[station.id, rs_changed]], columns=['railway_station_id', 'railway_station_model'])
            self.infra["railway_stations"] = pandas.concat([self.infra["railway_stations"], rs_df])
