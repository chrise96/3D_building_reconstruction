"""
Code to determine the horizontal line segment of each facade, represented
by bottom-left and bottom-right Rijksdriehoek corner points.
"""

def get_furthest_pair(visible_points, observer):
    """
    We assume that the list of polygon points of a building is arranged
    in counter-clockwise order. The order is important to determine the
    left-to-right order used to extract a texture from a panoramic image.

    In this function, we get the furthest in the list while keeping the order
    of the list. However, in some lists the start and end value are the same
    and we have to perform an extra calculation.

    If there are two visible_points we directly return.
    """
    if len(visible_points) > 2:
        # Build a dict mapping values to indices
        list_order = {tuple(v):i for i, v in enumerate(visible_points)}

        # Are the start and end values the same
        if visible_points[0] == visible_points[-1]:
            # Determine the direction of the observer from the line segment
            # Lies the observer to the Right of Line Segment or to the Left of Line Segment.
            cross_product = direction_of_observer(visible_points[:-1], observer)

            # Search for two points with the largest distance in the list of visible polygon points
            furthest_pair = diameter(visible_points[:-1])

            # Sort list according to list in function direction_of_observer(...)
            visible_points = sorted(furthest_pair, key=lambda k: [k[1], k[0]])

            # Observer is on the right of line segment if cross product is positive
            if cross_product > 0:
                # Reverse the two points
                return [visible_points[-1], visible_points[0]]
        else:
            # Search for two points with the largest distance in the list of visible polygon points
            furthest_pair = diameter(visible_points)

            # Sort list according to original list, with uneven length
            visible_points = sorted(furthest_pair, key=lambda v: list_order[tuple(v)])

    return visible_points

def direction_of_observer(visible_points, observer):
    """
    Determine direction of point from line segment

    Code is inspired by geeksforgeeks.org/direction-point-line-segment/
    """

    # A at the left side and B at the right, sort list on y-axis.
    visible_points = sorted(visible_points , key=lambda k: [k[1], k[0]])

    # Select two points from the sorted list
    aX = visible_points[0][0]
    aY = visible_points[0][1]
    bX = visible_points[-1][0]
    bY = visible_points[-1][1]

    # Subtracting co-ordinates of point A from B and P, to make A as origin
    bX = bX - aX
    bY = bY - aY
    pX = observer[0] - aX
    pY = observer[1] - aY

    # Determine the cross product
    cross_product = (bX * pY) - (bY * pX)

    return cross_product

def orientation(p, q, r):
    """ Return positive if p-q-r are clockwise, neg if ccw, zero if colinear """
    return (q[1] - p[1]) * (r[0] - p[0]) - (q[0] - p[0]) * (r[1] - p[1])

def hulls(points):
    """ Graham scan to find upper & lower convex hulls of a set of 2d points """
    U = []
    L = []
    points.sort()
    for p in points:
        while len(U) > 1 and orientation(U[-2], U[-1], p) <= 0:
            U.pop()
        while len(L) > 1 and orientation(L[-2], L[-1], p) >= 0:
            L.pop()
        U.append(p)
        L.append(p)
    return U, L

def rotating_calipers(points):
    """
    Find all ways of sandwiching between parallel lines.
    Given a list of 2d points, finds all ways of sandwiching the points
    between two parallel lines that touch one point each, and
    yields the sequence of pairs of points touched by each pair of lines.
    """
    U, L = hulls(points)
    i = 0
    j = len(L) - 1
    while i < len(U) - 1 or j > 0:
        yield U[i], L[j]

        # if all the way through one side of hull, advance the other side
        if i == len(U) - 1:
            j -= 1
        elif j == 0:
            i += 1
        # still points left on both lists, compare slopes of next hull edges
        # being careful to avoid divide-by-zero in slope calculation
        elif (U[i + 1][1] - U[i][1]) * (L[j][0] - L[j - 1][0]) > \
                (L[j][1] - L[j - 1][1]) * (U[i + 1][0] - U[i][0]):
            i += 1
        else:
            j -= 1

def diameter(points):
    """ Given a list of 2d points, returns the pair that's furthest apart """
    _, pair = max([((p[0] - q[0])**2 + (p[1] - q[1])**2, [p, q])
                      for p, q in rotating_calipers(points)])
    return pair
