import numpy as np
from pyproj import Geod

def sind(deg):
    """ Sine function with degree as input

    :param deg: Degree
    :type deg: float
    :return: Sine value
    :rtype: float
    """
    rad = np.radians(deg)
    return np.sin(rad)


def cosd(deg):
    """ Cosine function with degree as input

    :param deg: Degree
    :type deg: float
    :return: Cosine value
    :rtype: float
    """
    rad = np.radians(deg)
    return np.cos(rad)


def tand(deg):
    """ Tangent function with degree as input

    :param deg: Degree
    :type deg: float
    :return: Tangent value
    :rtype: float
    """
    rad = np.radians(deg)
    return np.tan(rad)


def cotd(deg):
    """ Cotangent function with degree as input

    :param deg: Degree
    :type deg: float
    :return: Cotangent value
    :rtype: float
    """
    rad = np.radians(deg)
    return np.cos(rad) / np.sin(rad)


def asind(x):
    """ Inverse sine function with degree as output

    :param x: Sine value
    :type x: float
    :return: Degree
    :rtype: float
    """
    rad = np.arcsin(x)
    return np.degrees(rad)


def acosd(x):
    """ Inverse cosine function with degree as output

    :param x: Cosine value
    :type x: float
    :return: Degree 
    :rtype: float
    """
    rad = np.arccos(x)
    return np.degrees(rad)


def atand(x):
    """ Inverse tangent function with degree as output

    :param x: Tangent value
    :type x: float
    :return: Degree
    :rtype: float
    """
    rad = np.arctan(x)
    return np.degrees(rad)


def km2deg(km):
    """ Convert km to degree

    :param km: Distance in km
    :type km: float
    :return: Distance in degree
    :rtype: float
    """
    radius = 6371
    circum = 2*np.pi*radius
    conv = circum / 360
    deg = km / conv
    return deg


def deg2km(deg):
    """ Convert degree to km

    :param deg: Distance in degree
    :type deg: float
    :return: Distance in km
    :rtype: float
    """
    radius = 6371
    circum = 2*np.pi*radius
    conv = circum / 360
    km = deg * conv
    return km


def rad2deg(rad):
    """ Convert radian to degree

    :param rad: Radian
    :type rad: float
    :return: Degree
    :rtype: float
    """
    deg = rad*(360/(2*np.pi))
    return deg


def skm2sdeg(skm):
    """ Convert s/km to s/degree

    :param skm: s/km
    :type skm: float
    :return: s/degree
    :rtype: float
    """
    sdeg = skm * deg2km(1)
    return sdeg


def sdeg2skm(sdeg):
    """ Convert s/degree to s/km

    :param sdeg: s/degree
    :type sdeg: float
    :return: s/km
    :rtype: float
    """
    skm = sdeg / deg2km(1)
    return skm


def srad2skm(srad):
    """ Convert s/rad to s/km

    :param srad: s/rad
    :type srad: float
    :return: s/km
    :rtype: float
    """
    sdeg = srad * ((2*np.pi)/360)
    return sdeg / deg2km(1)


def skm2srad(skm):
    """ Convert s/km to s/rad

    :param skm: s/km
    :type skm: float
    :return: s/rad
    :rtype: float
    """
    sdeg = skm * deg2km(1)
    return rad2deg(sdeg)


def latlon_from(lat0, lon0, azimuth, gcarc_dist, ellps="WGS84"):
    """
    Determine position with given position of initial point, azimuth and distance

    Accepted numeric scalar or array:
    - :class:`int`
    - :class:`float`
    - :class:`numpy.floating`
    - :class:`numpy.integer`
    - :class:`list`
    - :class:`tuple`
    - :class:`array.array`
    - :class:`numpy.ndarray`
    - :class:`xarray.DataArray`
    - :class:`pandas.Series`

    :param lat0: Latitude of original point
    :type lat0: float or array
    :param lon0: Longitude of original point
    :type lon0: float or array
    :param azimuth: Azimuth(s) in degree
    :type azimuth: float or array
    :param gcarc_dist: Distance(s) between initial and terminus point(s) in degree
    :type gcarc_dist: float or array
    :param ellps: Ellipsoids supported by ``pyproj``, defaults to "WGS84"
    :type ellps: :class:`str`, optional

    Returns
    -------
    scalar or array:
        Latitude(s) of terminus point(s)  
    scalar or array:
        Longitude(s) of terminus point(s)
    """

    def init_lalo(lat0, lon0, npts):
        if hasattr(lat0, "__iter__") and hasattr(lon0, "__iter__"):
            if len(lat0) != len(lon0):
                raise ValueError('lat0 and lon0 must be in the same length')
            elif len(lat0) != npts:
                raise ValueError('initial points must be in the same length as azimuths')
            else:
                lat1 = lat0
                lon1 = lon0
        elif np.isscalar(lat0) and np.isscalar(lon0):
            lat1 = np.ones(npts) * lat0
            lon1 = np.ones(npts) * lon0
        else:
            raise ValueError('lat0 and lon0 must be in the same length')
        return lat1, lon1

    if hasattr(azimuth, "__iter__") and hasattr(gcarc_dist, "__iter__"):
        if len(azimuth) == len(gcarc_dist):
            npts = len(azimuth)
            lat0, lon0 = init_lalo(lat0, lon0, npts)
        else:
            raise ValueError('azimuth and gcarc_dist must be in the same length')
    elif np.isscalar(azimuth) and np.isscalar(gcarc_dist):
        if hasattr(lat0, "__iter__") and hasattr(lon0, "__iter__"):
            if len(lat0) != len(lon0):
                raise ValueError('lat0 and lon0 must be in the same length')
            else:
                azimuth = np.ones_like(lat0)*azimuth
                gcarc_dist = np.ones_like(lat0)*gcarc_dist
        elif np.isscalar(lat0) and np.isscalar(lon0):
            pass
        else:
            raise ValueError('lat0 and lon0 must be in the same length')
    elif np.isscalar(azimuth) and hasattr(gcarc_dist, "__iter__"):
        npts = len(gcarc_dist)
        azimuth = np.ones(npts)*azimuth
        lat0, lon0 = init_lalo(lat0, lon0, npts)
    elif np.isscalar(gcarc_dist) and hasattr(azimuth, "__iter__"):
        npts = len(azimuth)
        gcarc_dist = np.ones(lat0, lon0, npts)*gcarc_dist
        lat0, lon0 = init_lalo(lat0, lon0, npts)
    g = Geod(ellps=ellps)
    lon, lat, _ = g.fwd(lon0, lat0, azimuth, deg2km(gcarc_dist)*1000)
    return lat, lon
