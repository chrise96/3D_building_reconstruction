def orientation(p, q, r):
    """Return positive if p-q-r are clockwise, neg if ccw, zero if colinear."""
    return (q[1] - p[1]) * (r[0] - p[0]) - (q[0] - p[0]) * (r[1] - p[1])


def hulls(points):
    """Graham scan to find upper & lower convex hulls of a set of 2d points."""
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
    """Find all ways of sandwiching between parallel lines.
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
    """Given a list of 2d points, returns the pair that's farthest apart."""
    diam, pair = max([((p[0] - q[0])**2 + (p[1] - q[1])**2, [p, q])
                      for p, q in rotating_calipers(points)])
    return pair
