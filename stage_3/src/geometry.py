import math

def line_magnitude(x1, y1, x2, y2):
    magnitude = math.sqrt(math.pow((x2 - x1), 2)+ math.pow((y2 - y1), 2))
    return magnitude

def distance_point_line(px, py, x1, y1, x2, y2):
    """
    Calculate the  minimum distance from a point and a line segment 
    (i.e. consecutive vertices in a polyline).
    
    Source: http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/source.vba

    """
    LineMag = line_magnitude(x1, y1, x2, y2)

    if LineMag < 0.00000001:
        distance = 9999
        return distance

    u1 = (((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1)))
    u = u1 / (LineMag * LineMag)

    if (u < 0.00001) or (u > 1):
        # Closest point does not fall within the line segment, 
        # take the shorter distance to an endpoint.
        ix = line_magnitude(px, py, x1, y1)
        iy = line_magnitude(px, py, x2, y2)
        if ix > iy:
            distance = iy
        else:
            distance = ix
    else:
        # Intersecting point is on the line, use the formula
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        distance = line_magnitude(px, py, ix, iy)

    return distance

def calculate_angle(line1, line2):
    """
    Calculate the angle (in degrees) between two linear lines 
    when lines are not joined.
    """
    # Use 1e-10 to prevent zero division error
    slope1 = (line1[1][1] - line1[0][1]) / (line1[1][0] - line1[0][0] + 1e-10)
    slope2 = (line2[1][1] - line2[0][1]) / (line2[1][0] - line2[0][0] + 1e-10)
    
    return abs(math.degrees(math.atan((slope2 - slope1) / (1 + (slope2 * slope1)))))

def euclidean_distance(x_1, y_1, x_2, y_2):
    """
    Calculate the Euclidean distance between two vectors
    """
    return math.sqrt(((x_1 - x_2)**2) + ((y_1 - y_2)**2))
