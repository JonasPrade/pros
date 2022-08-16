from prosd import db
from prosd.models import RailwayPoint, RailwayStation

points = RailwayPoint.query.all()

for point in points:
    # # check if a station with that kuerzel already exists
    # station = RailwayStation.query.filter(RailwayStation.db_kuerzel == point.db_kuerzel).first()
    #
    # if not station:
    #     station = RailwayStation(
    #         name=point.name,
    #         db_kuerzel=point.db_kuerzel,
    #         type=point.type
    #     )
    #     db.session.add(station)
    #     db.session.commit()
    #     db.session.refresh(station)
    #
    # point.station_id = station.id
    # db.session.add(point)
    # db.session.commit()

    station = RailwayStation.query.filter(RailwayStation.db_kuerzel == point.db_kuerzel).scalar()

    if station.type is None:
        station.type = point.type
        db.session.add(station)
        db.session.commit()