import geoalchemy2
import pyproj
import shapely

class PostgisBasics():
    """
    class that provides some basics funtions for postgis
    """

    def __init__(self, geometry, srid):
        """

        :param geometry: wkb
        :param srid:
        """
        self.geometry = shapely.wkb.loads(geometry.desc, hex=True)

        if srid == 4326:
            self.ellps = "WGS84"

    def length_in_meter(self):
        """
        calculates the length in meters of a geometry given
        :param srid: int
        :param geometry:
        :return:
        """
        geod = pyproj.Geod(ellps=self.ellps)
        length = geod.geometry_length(self.geometry)
        return length