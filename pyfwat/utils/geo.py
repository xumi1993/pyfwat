import numpy as np

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
