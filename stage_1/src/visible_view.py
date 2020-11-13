from skgeom import *

def generate_arrangement(observer, building_polygons):
    """ Create a 2D arrangement using skgeom """
    arr = arrangement.Arrangement()

    set_range = 60
    left_x = observer[0] - set_range
    left_y = observer[1] - set_range
    right_x = observer[0] + set_range
    right_y = observer[1] + set_range

    walls = [
        Segment2(Point2(left_x, left_y), Point2(left_x, right_y)),
        Segment2(Point2(left_x, right_y), Point2(right_x, right_y)),
        Segment2(Point2(right_x, right_y), Point2(right_x, left_y)),
        Segment2(Point2(right_x, left_y), Point2(left_x, left_y))
    ]

    for s in walls:
        arr.insert(s)

    for poly in building_polygons:
        building_edges = points_2_edges(poly)

        for s in building_edges:
            arr.insert(s)

    return arr

def points_2_edges(pts):
    """ Make edges """
    edges = []
    for i in range(1,len(pts)):
        e = Segment2(Point2(pts[i-1][0], pts[i-1][1]),
                     Point2(pts[i][0], pts[i][1]))
        edges.append(e)
    return edges

def get_visibility_polygon(arr, observer):
    """
    Compute the visibility from a specific point inside
    the arrangement
    """
    vs = TriangularExpansionVisibility(arr)
    q = Point2(observer[0], observer[1])
    face = arr.find(q)
    vx = vs.compute_visibility(q, face)

    ############### Draw Arrangement ###############
    # draw_arrangement(arr, vx, q)

    # Get all edges of Visibility Polygon
    allEdges = [v.point() for v in vx.vertices]

    return Polygon(allEdges)

def draw_arrangement(arr, vx, q, save_file=False):
    """
    Draw 2D arrangement with buildings and initial
    panoramic image location
    """
    from matplotlib import pyplot as plt

    plt.figure(figsize=(10, 10))
    plt.xlabel("X Position")
    plt.ylabel("Y Position")

    # Draw walls and buildings
    for he in arr.halfedges:
        plt.plot([he.curve().source().x(), he.curve().target().x()],
                     [he.curve().source().y(), he.curve().target().y()], "b")

    # Draw Visibility Polygon
    for he in vx.halfedges:
        plt.plot([he.curve().source().x(), he.curve().target().x()],
                     [he.curve().source().y(), he.curve().target().y()], "r:")

    plt.scatter(q.x(), q.y(), color="b")
    if save_file:
        plt.savefig("vispol.eps", format="eps")
    else:
        plt.show()

def point_in_visibility_polygon(building_poly, visibility_polygon):
    """ Check wether a given point is inside the visibility polygon """
    visible_points = []

    for x,y in building_poly:
        position = visibility_polygon.oriented_side(Point2(x, y))
        if position == Sign.ZERO or position == Sign.POSITIVE:
            visible_points.append([x, y])

    return visible_points
