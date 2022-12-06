"""
A class that creates a infrastrucutre state that differs from the railway by adding project_contents
"""

import os
import pandas

from prosd.models import ProjectContent, RailwayLine, RailwayStation


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

        self._filepath_changes = os.path.join(filepath_changes)
        self.project_contents = self._load_changes_csv()
        self.infra = self._create_railway_df()

    def load_changes(self):
        self._load_projects_to_version()

    def _load_changes_csv(self):
        csv = pandas.read_csv(self._filepath_changes, header=None)
        csv.columns = ["project_content"]
        return csv

    def _create_railway_df(self):
        infra = dict()
        columns_rl_lines = ['railway_line_id', 'railway_line_model']
        infra["railway_lines"] = pandas.DataFrame(
            RailwayLine.query.with_entities(RailwayLine.id, RailwayLine).order_by(RailwayLine.id).all(),
            columns=columns_rl_lines
        )
        infra["railway_stations"] = pandas.DataFrame(
            RailwayStation.query.with_entities(RailwayStation.id, RailwayStation).order_by(RailwayStation.id).all(),
            columns=["railway_station_id", "railway_station_model"]
        )
        return infra

    def _load_projects_to_version(self):
        for index, pc_id in self.project_contents.iterrows():
            self._load_single_project_to_version(pc_id)

    def _load_single_project_to_version(self, pc_id):
        pc = ProjectContent.query.get(int(pc_id["project_content"]))
        for line in pc.projectcontent_railway_lines:
            # get the correct railwayline and remove that from the dataFrame
            rl_changed = self.infra["railway_lines"][self.infra["railway_lines"].railway_line_id == line.id][
                "railway_line_model"].iloc[0]
            self.infra["railway_lines"] = self.infra["railway_lines"][
                self.infra["railway_lines"].railway_line_id != line.id]

            rl_changed = _change_electrification(project_content=pc, railway_line=rl_changed)
            # Here can be more changes added

            rl_df = pandas.DataFrame([[line.id, rl_changed]], columns=['railway_line_id', 'railway_line_model'])
            self.infra["railway_lines"] = pandas.concat([self.infra["railway_lines"], rl_df])

        for station in pc.railway_stations:
            rs_changed = self.infra["railway_stations"][self.infra["railway_stations"].railway_station_id == station.id][
                "railway_station_model"].iloc[0]
            self.infra["railway_stations"] = self.infra["railway_stations"][
                self.infra["railway_stations"].railway_station_id != station.id]

            rs_changed = _change_charging_station(project_content=pc, railway_station=rs_changed)
            # Here can be added some more

            rs_df = pandas.DataFrame([[station.id, rs_changed]], columns=['railway_station_id', 'railway_station_model'])
            self.infra["railway_stations"] = pandas.concat([self.infra["railway_stations"], rs_df])


