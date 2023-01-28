### imports the railml of Deutschlandtakt to the db
import xml.etree.ElementTree as ET
import datetime
import logging

from prosd.models import Vehicle, Formation, TimetableCategory, RailMlOcp, RailwayStation, TimetableTrainPart, \
    TimetableOcp, TimetableTime, TimetableSection, TimetableTrain, TimetableTrainGroup
from prosd import db


def string_to_date(date_string):
    date = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()

    return date


def string_to_time(time_string):
    time = datetime.datetime.strptime(time_string, '%H:%M:%S.%f').time()

    return time


def string_to_duration(duration_string):
    try:
        t = datetime.datetime.strptime(duration_string, "PT%MM%SS")
    except ValueError:
        try:  # sometimes no seconds are given in this case try only the minutes
            t = datetime.datetime.strptime(duration_string, "PT%MM")
        except ValueError:
            try:
                t = datetime.datetime.strptime(duration_string, "PT%SS")
            except ValueError:
                try:
                    t = datetime.datetime.strptime(duration_string, "PT%HH%MM")
                except ValueError:
                    try:
                        t = datetime.datetime.strptime(duration_string, "PT%HH")
                    except ValueError:
                        logging.warning("Could not convert time data" + str(duration_string))

    duration = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    return duration


def create_vehicle(vehicle_railml):
    vehicle_dict = vehicle_railml.attrib
    vehicle_dict["brutto_weight"] = vehicle_dict.pop("bruttoWeight")
    if "engine" in vehicle_railml[0].tag:
        vehicle_dict["engine"] = True
        vehicle_dict["wagon"] = False

    if "wagon" in vehicle_railml[0].tag:
        vehicle_dict["engine"] = False
        vehicle_dict["wagon"] = True

    vehicle = Vehicle(**vehicle_dict)
    return vehicle


def add_vehicles(railstock):
    vehicles = railstock.find('{http://www.railml.org/schemas/2013}vehicles')

    objects = []
    for vehicle_railml in vehicles:
        vehicle = create_vehicle(vehicle_railml)
        objects.append(vehicle)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def create_formation(formation_railml):
    vehicles = []
    vehicles_railml = formation_railml[0]
    for vehicle_railml in vehicles_railml:
        vehicle = Vehicle.query.get(vehicle_railml.attrib["vehicleRef"])
        vehicles.append(vehicle)

    formation_dict = formation_railml.attrib
    formation_dict["vehicles"] = vehicles
    formation = Formation(**formation_railml.attrib)

    return formation


def formation_to_vehicle(railstock):
    formations = railstock.find('{http://www.railml.org/schemas/2013}formations')
    for formation_ml in formations:
        formation = Formation.query.get(formation_ml.attrib["id"])
        vehicle = []
        vehicles_ml = formation_ml.find('{http://www.railml.org/schemas/2013}trainOrder')
        for vehicle_ml in vehicles_ml:
            vehicle.append(Vehicle.query.get(vehicle_ml.attrib["vehicleRef"]))
        formation.vehicles = vehicle
        db.session.add(formation)
        db.session.commit()


def add_formations(railstock):
    formations = railstock.find('{http://www.railml.org/schemas/2013}formations')
    objects = []
    for formation_railml in formations:
        formation = create_formation(formation_railml)
        objects.append(formation)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def create_category(category_railml):
    category_dict = category_railml.attrib
    category = TimetableCategory(**category_dict)

    return category


def add_categories(timetable):
    timetable_categories = timetable.find('{http://www.railml.org/schemas/2013}categories')
    objects = []
    for categorie_railml in timetable_categories:
        category = create_category(categorie_railml)
        objects.append(category)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def add_ocps(infrastructure):
    ocps = infrastructure.find('{http://www.railml.org/schemas/2013}operationControlPoints')
    objects = []
    for ocp_ml in ocps:
        ocp = create_ocp(ocp_ml)
        objects.append(ocp)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def create_ocp(ocp_ml):
    ocp_dict = ocp_ml.attrib
    prop_operational = ocp_ml.find('{http://www.railml.org/schemas/2013}propOperational')
    if prop_operational is not None:
        ocp_dict["operational_type"] = prop_operational.attrib["operationalType"]
    else:
        ocp_dict["operational_type"] = None

    if ocp_dict["operational_type"] == 'station':
        station = RailwayStation.query.filter(RailwayStation.db_kuerzel == ocp_dict["code"]).scalar()
        if station:
            ocp_dict["station_id"] = station.id
        else:
            logging.warning("For " + str(ocp_dict) + " no station found")

    ocp = RailMlOcp(**ocp_dict)

    return ocp


def create_train_part(tp_rml):
    tp_dict = tp_rml.attrib

    formation = tp_rml.find('{http://www.railml.org/schemas/2013}formationTT')
    if formation is not None:
        tp_dict["formation_id"] = formation.attrib["formationRef"]
    else:
        logging.warning("no formation for " + str(tp_dict))

    opttp = tp_rml.find('{http://www.railml.org/schemas/2013}operatingPeriodRef')
    if opttp is not None:
        tp_dict["operating_period_id"] = opttp.attrib["ref"]

    tp_dict["category_id"] = tp_dict.pop("categoryRef")

    tt_ocps = []
    ocps_railml = tp_rml.find('{http://www.railml.org/schemas/2013}ocpsTT')
    if ocps_railml is not None:
        for ocp in ocps_railml:
            tt_ocp = create_tt_ocp(tt_ocp_rml=ocp)
            tt_ocps.append(tt_ocp)
    else:
        logging.warning("no ocps for " + str(tp_dict))

    tp_dict["timetable_ocps"] = tt_ocps
    tp = TimetableTrainPart(**tp_dict)

    return tp


def create_tt_ocp(tt_ocp_rml):
    ocp_dict = tt_ocp_rml.attrib
    # ocp_dict["train_part"] = train_part_id
    ocp_dict["sequence"] = int(ocp_dict["sequence"])
    ocp_dict["ocp_id"] = ocp_dict.pop("ocpRef")
    ocp_dict["ocp_type"] = ocp_dict.pop("ocpType")

    if "trackRef" in ocp_dict:
        ocp_dict.pop("trackRef")

    if "trackInfo" in ocp_dict:
        ocp_dict.pop("trackInfo")

    if "trainReverse" in ocp_dict:
        reverse = ocp_dict.pop("trainReverse")
        if reverse == 'true':
            ocp_dict["train_reverse"] = True
        else:
            ocp_dict["train_reverse"] = False

    if "remarks" in ocp_dict:
        ocp_dict.pop("remarks")

    times = tt_ocp_rml.findall('{http://www.railml.org/schemas/2013}times')
    time_objects = []
    for time in times:
        tt_time = create_tt_time(tt_time_rml=time)
        time_objects.append(tt_time)
    ocp_dict["times"] = time_objects

    section_rml = tt_ocp_rml.find('{http://www.railml.org/schemas/2013}sectionTT')
    if section_rml is not None:
        section = create_section(section_rml)
        ocp_dict["section"] = [section]

    tt_ocp = TimetableOcp(**ocp_dict)
    return tt_ocp


def create_tt_time(tt_time_rml):
    time_dict = tt_time_rml.attrib
    if "departure" in time_dict:
        time_dict["departure"] = string_to_time(time_dict["departure"])
    if "arrival" in time_dict:
        time_dict["arrival"] = string_to_time(time_dict["arrival"])

    if "arrivalDay" in time_dict:
        time_dict["arrival_day"] = int(time_dict.pop("arrivalDay"))

    if "departureDay" in time_dict:
        time_dict["departure_day"] = int(time_dict.pop("departureDay"))

    tt_time = TimetableTime(**time_dict)
    return tt_time


def create_section(section_rml):
    section_dict = section_rml.attrib
    section_dict["line"] = section_dict.pop("lineRef")

    track_ref = section_rml.find('{http://www.railml.org/schemas/2013}trackRef')
    if track_ref is not None:
        section_dict["track_id"] = track_ref.attrib["ref"]
        section_dict["direction"] = track_ref.attrib["dir"]

    minimal_run_time = section_rml.find('{http://www.railml.org/schemas/2013}runTimes')
    if minimal_run_time is not None:
        if "minimalTime" in minimal_run_time.attrib:
            section_dict["minimal_run_time"] = string_to_duration(minimal_run_time.attrib["minimalTime"])

    section = TimetableSection(**section_dict)

    return section


def add_train_parts(timetable, delete_old=False):
    if delete_old:
        db.session.query(TimetableTrainPart).delete()
        db.session.commit()

    timetable_train_parts = timetable.find('{http://www.railml.org/schemas/2013}trainParts')

    objects = []
    for tp_rml in timetable_train_parts:
        tp = create_train_part(tp_rml)
        objects.append(tp)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def add_ocp(timetable, overwrite=False):
    if overwrite:
        db.session.query(TimetableOcp).delete()
        db.session.commit()

    timetable_train_parts = timetable.find('{http://www.railml.org/schemas/2013}trainParts')

    for tp_rml in timetable_train_parts:
        tp_id = tp_rml.attrib["id"]
        tp = TimetableTrainPart.query.get(tp_id)
        ocps_railml = tp_rml.find('{http://www.railml.org/schemas/2013}ocpsTT')
        if ocps_railml is not None:
            for ocp in ocps_railml:
                tt_ocp = create_tt_ocp(tt_ocp_rml=ocp)
                tt_ocp.train_part = tp_id
                db.session.add(tt_ocp)
        else:
            logging.warning("no ocps for " + str(tp))

    db.session.commit()


def add_trains(timetable):
    timetable_trains = timetable.find('{http://www.railml.org/schemas/2013}trains')

    objects = []
    for train_ml in timetable_trains:
        train = create_train(train_ml)
        objects.append(train)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def create_train(train_ml):
    train_dict = train_ml.attrib

    if "trainNumber" in train_dict:
        train_dict["train_number"] = train_dict.pop("trainNumber")

    if "additionalTrainNumber" in train_dict:
        train_dict.pop("additionalTrainNumber")

    if "remarks" in train_dict:
        train_dict.pop("remarks")

    line_number = train_ml.find('{http://www.sma-partner.ch/schemas/2013/Viriato/Base}lineNumber')
    if line_number is not None:
        train_dict["line_number"] = line_number.text

    train_validity_name = train_ml.find('{http://www.sma-partner.ch/schemas/2013/Viriato/Base}trainValidityName')
    if train_validity_name is not None:
        train_dict["train_validity_name"] = train_validity_name.text

    train_part_sequence = train_ml.find('{http://www.railml.org/schemas/2013}trainPartSequence')
    if train_part_sequence is not None:
        train_part_ref = train_part_sequence.find('{http://www.railml.org/schemas/2013}trainPartRef')
        if train_part_ref is not None:
            train_dict["train_part_id"] = train_part_ref.attrib["ref"]

        speed_profile_ref = train_part_sequence.find('{http://www.railml.org/schemas/2013}speedProfileRef')
        if speed_profile_ref is not None:
            train_dict["speed_profile_ref"] = speed_profile_ref.attrib["ref"]

        brake_usage = train_part_sequence.find('{http://www.railml.org/schemas/2013}brakeUsage')
        if brake_usage is not None:
            train_dict["brake_type"] = brake_usage.attrib["brakeType"]
            if "airBrakeApplicationPosition" in brake_usage:
                train_dict["air_brake_application_position"] = brake_usage.attrib["airBrakeApplicationPosition"]
            if "regularBrakePercentage" in brake_usage:
                train_dict["regular_brake_percentage"] = brake_usage.attrib["regularBrakePercentage"]

    train = TimetableTrain(**train_dict)

    return train


def add_train_groups(timetable):
    train_groups = timetable.find('{http://www.railml.org/schemas/2013}trainGroups')

    objects = []
    for group_ml in train_groups:
        group = create_group(group_ml)
        objects.append(group)

    db.session.bulk_save_objects(objects)
    db.session.commit()


def create_group(group_ml):
    group_dict = group_ml.attrib
    group_dict["train_number"] = int(group_dict.pop("trainNumber"))

    trains = []
    for train in group_ml:
        train_id = train.attrib["ref"]
        sequence = train.attrib["sequence"]

        train = TimetableTrain.query.get(train_id)
        train.train_group_sequence = int(sequence)

        trains.append(train)

    group_dict["trains"] = trains

    group = TimetableTrainGroup(**group_dict)

    return group


def train_to_train_groups(timetable):
    train_groups = timetable.find('{http://www.railml.org/schemas/2013}trainGroups')
    update_trains = []
    for group in train_groups:
        train_group_id = TimetableTrainGroup.query.get(
            group.attrib["id"]
        ).id
        for train_ref in group:
            train = TimetableTrain.query.get(train_ref.attrib["ref"])
            train.train_group_id = train_group_id
            update_trains.append(train)

    db.session.bulk_save_objects(update_trains)
    db.session.commit()


if __name__ == "__main__":
    filename = '../../example_data/d-takt/dtakt.railml'
    tree = ET.parse(filename)
    root = tree.getroot()

    infrastructure = root[1]
    # add_ocps(infrastructure)

    # railstock
    railstock = root.find('{http://www.railml.org/schemas/2013}rollingstock')
    # add_vehicles(railstock)
    # formation_to_vehicle(railstock)
    # add_formations(railstock)

    # timetable
    timetable = root.find('{http://www.railml.org/schemas/2013}timetable')
    # add_categories(timetable)
    # add_train_parts(timetable, delete_old=True)
    # add_ocp(timetable, overwrite=True)
    # add_trains(timetable)
    # add_train_groups(timetable)
    # train_to_train_groups(timetable)
    print(timetable)
