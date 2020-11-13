from numpy.core.umath import sqrt, square, arccos, arctan2, mod, pi

# Helper constants for readability
X, Y = 0, 1

def vector(from_2d, to_2d):
    return to_2d[X] - from_2d[X], to_2d[Y] - from_2d[Y]

def vector_length(vector_2d):
    return sqrt(vector_2d[X]**2 + vector_2d[Y]**2)

def get_midpoint(vertices):
    return ((vertices[0][X] + vertices[1][X]) / 2, (vertices[0][Y] + vertices[1][Y]) / 2)

def get_vector(to_point, from_point):
    """
    Calculate a 3D vector from from_point to to_point,
    also works on numpy 2D arrays of points


    :param to_point: 3d tuple of the point the vector will point to
    :param from_point: 3d tuple of the point the vector will point from
    :return: 3D tuple of the vector
    """

    return to_point[0] - from_point[0], \
           to_point[1] - from_point[1], \
           to_point[2] - from_point[2]


def get_cartesian_vector_from_rd(to_point, from_point):
    """
    Calculate a 3D vector from from_point to to_point,
    also works on numpy 2D arrays of points,
    reorders dimensions from rd to cartesian


    :param to_point: 3d tuple of the point the vector will point to
    :param from_point: 3d tuple of the point the vector will point from
    :return: 3D tuple of the reordered vector
    """

    return to_point[1] - from_point[1], \
           to_point[0] - from_point[0], \
           to_point[2] - from_point[2]


def cartesian2cylindrical(vector, source_width, source_height, r_is_1=True):
    """
    Calculates the location on a equirectangular plane of a vector,
    Will work with numpy's 2D arrays of points

    :param vector: 3d tuple of the point the vector
    :param source_width: width and
    :param source_height:     height of the equirectangular image
    :param r_is_1: boolean, denoting if vectors are normalized to 1 (default=True)
    :return: 3D tuple of the coordinates of the vector on the equirectangular plane
    """

    middle = source_width / 2

    x = vector[0]
    y = vector[1]
    z = vector[2]

    # Vectors are defined by (r, theta, phi) and is given in Cartesian coordinates by:
    r = 1 if r_is_1 else sqrt(square(x) + square(y) + square(z))
    theta = arccos(z / r)
    phi = arctan2(y, x)

    x1 = mod(middle + middle * phi / pi, source_width - 1)
    y1 = source_height * theta / pi

    return x1, y1
