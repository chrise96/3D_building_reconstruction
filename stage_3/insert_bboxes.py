"""
The detected rectangles in a two-dimensional image are given via four pixel values:
xleft, xright, ytop, ybottom. These values are transformed to three-dimensional
coordinates in order to integrate them in a building in the 3D model.
"""

import pandas as pd
import time
import os
from lxml import etree as ET
from PIL import Image
import collections

from src.geometry import *
from src.furthest_pair import *

CITYGML_PATH = "CityGML/LOD2_120700-485100_filtered.gml"
CITYGML_OUTPUT_PATH = "CityGML/LOD3_120700-485100.gml"
CSV_PATH = "CSV/output_stage3.csv"
CROPPED_IMAGES_PATH = "texture_cropped/"
IMAGES_PATH = "images/"

# Namespaces of XML file
NS_CITYGML = "http://www.opengis.net/citygml/2.0"
NS_GML = "http://www.opengis.net/gml"
NS_BLDG = "http://www.opengis.net/citygml/building/2.0"

NSMAP = {
    "city": NS_CITYGML,
    "gml": NS_GML,
    "bldg": NS_BLDG
}

# Extracted images are set to 30 meter as height, equal to 900 pixel height
IMAGE_HEIGHT_IRL = 30 # Defined in stage 1

DEBUG = False

def coordinate_transformation(bboxes_pixel, visible_point_left, visible_point_right, low_z, high_z, filename):
    """
    Transform the 2D bbox coordinates to 3D bbox coordinates.
    """

    # Get image info from original images
    im = Image.open(os.path.join(IMAGES_PATH, filename + ".jpeg"))
    image_width, image_height = im.size # Height is always 900 pixels

    # Calculate slope
    x_dist = visible_point_right[0] - visible_point_left[0]
    y_dist = visible_point_right[1] - visible_point_left[1]

    bboxes_real = []
    for bbox in bboxes_pixel:
        x0, y0, x1, y1 = bbox

        # Coordinate transformation
        fraction_of_total = x0 / image_width

        X0 = visible_point_left[0] + x_dist * fraction_of_total
        Y0 = visible_point_left[1] + y_dist * fraction_of_total

        fraction_of_total = x1 / image_width

        X1 = visible_point_left[0] + x_dist * fraction_of_total
        Y1 = visible_point_left[1] + y_dist * fraction_of_total

        Z0 = round(((image_height - y0) / image_height * IMAGE_HEIGHT_IRL) + low_z, 2)
        Z1 = round(((image_height - y1) / image_height * IMAGE_HEIGHT_IRL) + low_z, 2)

        # Validate height of bbox above facade (Better to do this in get_wall_to_insert())
        if Z0 < (low_z + high_z):
            bboxes_real.append([X0, X1, Y0, Y1, Z0, Z1])

    return bboxes_real

def get_outer_poslist_points(surface_element):
    """
    Get outer x-axis points of a wall surface polygon.
    """
    # Save the outer poslist points of the buildings
    outer_poslist_points = {}

    for polygon in surface_element.findall(".//gml:Polygon", NSMAP):
        # Get the unique id for a Polygon
        attribute_id = polygon.attrib["{%s}id" % NS_GML]

        # Get the coordinates of the Polygon
        poslist_string = polygon.find(".//gml:posList", NSMAP).text

        # Split the string that is seperated with a space to float list
        poslist_float = [float(x) for x in poslist_string.split()]

        # Create a nested list out of split_posList
        xyz_list = [poslist_float[x:x+3] for x in range(0, len(poslist_float),3)]

        # Search for two points with the largest distance in the list of visible polygon points
        furthest_pair = diameter(xyz_list[:-1])

        outer_poslist_points[attribute_id] = furthest_pair

    return outer_poslist_points

def get_wall_to_insert(outer_poslist_points, bboxes_window, wall_points):
    """
    For each bbox (window or door), we search for the wall
    candidate that best fits to it.
    """
    bbox_wall_match = collections.defaultdict(list)

    for bbox in bboxes_window:
        # Left below bbox coordinates
        random_bbox_point = [bbox[0], bbox[3]]
        # Initialize variables
        shortest_distance = float("inf")
        wall_id = 0

        for key, value in outer_poslist_points.items():
            angle_between_lines = calculate_angle(value, wall_points)
            # The angle between the wall and the bbox must be below 15 degrees.
            if angle_between_lines < 15:
                distance = distance_point_line(random_bbox_point[0], random_bbox_point[1],
                                             value[0][0], value[0][1], value[1][0], value[1][1])

                # Get the shortest distance from point to wall
                if distance < shortest_distance:
                    shortest_distance = distance
                    wall_id = key

        # Add key and bbox to dict or append bbox to existing key
        bbox_wall_match[wall_id].append(bbox)

    return bbox_wall_match

def get_poslist_order(bbox):
    """
    Create list of the bbox in posList order and convert it
    into a string with spaces (gml posList format)
    """
    poslist_order = [bbox[0], bbox[2], bbox[4], # Bottom left
                     bbox[1], bbox[3], bbox[4], # Bottom right
                     bbox[1], bbox[3], bbox[5], # Top right
                     bbox[0], bbox[2], bbox[5], # Top left
                     bbox[0], bbox[2], bbox[4]]

    # Convert list of floats into a string with spaces (gml posList format)
    return " ".join(str(item) for item in poslist_order)

def get_poslist_order_reversed(bbox):
    """
    Create list of the bbox in reversed posList order and
    convert it into a string with spaces (gml posList format)
    """
    poslist_order_reversed = [bbox[0], bbox[2], bbox[4], # Bottom left
                             bbox[0], bbox[2], bbox[5], # Top left
                             bbox[1], bbox[3], bbox[5], # Top right
                             bbox[1], bbox[3], bbox[4], # Bottom right
                             bbox[0], bbox[2], bbox[4]]

    return " ".join(str(item) for item in poslist_order_reversed)

def add_interior(bbox_list, polygon):
    """ Insert window or door bbox as interior polygon """
    for bbox in bbox_list:
        poslist_bbox = get_poslist_order(bbox)

        # Insert interior polygon of window or door
        a = ET.SubElement(polygon, "{%s}interior" % NS_GML)
        b = ET.SubElement(a, "{%s}LinearRing" % NS_GML)
        c = ET.SubElement(b, "{%s}posList" % NS_GML)
        c.attrib["srsDimension"] = "3"
        c.text = poslist_bbox

def add_opening(bbox_list, surface_element, facade_detail):
    """ Insert window or door bbox as Opening """
    for bbox in bbox_list:
        poslist_bbox_reversed = get_poslist_order_reversed(bbox)

        # Insert interior polygon of window or door
        a = ET.SubElement(surface_element, "{%s}opening" % NS_BLDG)
        b = ET.SubElement(a, "{%s}%s" % (NS_BLDG, facade_detail))
        c = ET.SubElement(b, "{%s}lod3MultiSurface" % NS_BLDG)
        d = ET.SubElement(c, "{%s}MultiSurface" % NS_GML)
        e = ET.SubElement(d, "{%s}surfaceMember" % NS_GML)
        f = ET.SubElement(e, "{%s}Polygon" % NS_GML)
        g = ET.SubElement(f, "{%s}exterior" % NS_GML)
        h = ET.SubElement(g, "{%s}LinearRing" % NS_GML)
        i = ET.SubElement(h, "{%s}posList" % NS_GML)
        i.text = poslist_bbox_reversed

def main():
    # Check if input files can be found
    if not os.path.isfile(CITYGML_PATH):
        print("Input CityGML file not found. Aborting.")
        return

    if not os.path.isfile(CSV_PATH):
        print("Input csv files not found. Aborting.")
        return

    print("--- Start ---")

    # Start timer
    start_time = time.time()

    # Get dataframe
    df = pd.read_csv(CSV_PATH, dtype={"pand_id": object})

    # Set the DEBUG variable to true if you manually validated the cropped images
    if DEBUG:
        files = []
        for filename in os.listdir(CROPPED_IMAGES_PATH):
            file = os.path.splitext(filename)[0]
            if filename.endswith(".jpeg"):
                files.append(file)

        df = df[df["texture_filename"].isin(files)].reset_index(drop=True)

    print("Step 5: Transform the 2D bbox coordinates to 3D bbox coordinates.")
    bbox_real_data = []
    for _, row in df.iterrows():
        new_data = {}
        new_data["texture_filename"] = row["texture_filename"]

        for keyword in ["bboxes_window", "bboxes_door"]:
            new_data[keyword + "_real"] = coordinate_transformation(eval(row[keyword]), eval(row["visible_point_one"]),
                                                                    eval(row["visible_point_two"]), row["low_z"],
                                                                    row["high_z"], new_data["texture_filename"])

        bbox_real_data.append(new_data)

    # Merge dataframes
    df_bbox_real = pd.DataFrame(bbox_real_data)
    df_output = df_bbox_real.merge(df) # TODO Reuse df and keep only specific columns

    # Get the CityGML file
    # All objects are passed by reference.
    # And since "tree" is an object, you're only passing the reference.
    parser = ET.XMLParser(remove_blank_text = True) # Remove spaces etc.
    tree = ET.parse(CITYGML_PATH, parser)
    root = tree.getroot()

    print("Step 6: Insert the windows and doors in the 3D buildings.")
    # TODO move to function, too long
    for building_element in root.findall(".//city:cityObjectMember", NSMAP):
        # Get pand_id in current element of XML
        pand_id = building_element.find(".//bldg:Building/gml:name", NSMAP)
        if pand_id is not None:
            # Check if the pand_id is inside the dataframe
            df_row = df_output.loc[pand_id.text == df_output['pand_id']]
            if not df_row.empty:
                # Left and right Rijksdriehoek coordinates found for the facade in the image
                wall_points = [eval(df_row["visible_point_one"].values[0]), eval(df_row["visible_point_two"].values[0])] # TODO Dont use eval

                for surface_element in building_element.findall(".//bldg:WallSurface", NSMAP):
                    # Loop polygon 1: Get outer x-axis points of a wall surface polygon
                    outer_poslist_points = get_outer_poslist_points(surface_element)

                    bboxes_window = df_row["bboxes_window_real"].values[0]
                    bboxes_door = df_row["bboxes_door_real"].values[0]
                    bboxes_merged = bboxes_window + bboxes_door

                    # Get wall id on where to insert window or door bbox
                    bbox_wall_match = get_wall_to_insert(outer_poslist_points, bboxes_merged, wall_points)

                    # Loop polygon 2: Insert window or door bbox as interior polygon
                    for polygon in surface_element.findall(".//gml:Polygon", NSMAP):

                        # Because multiple bboxes can occur for one UUID, we iterate over these values
                        for wall_id, bbox_list in bbox_wall_match.items():
                            if polygon.get("{%s}id" % NS_GML) == wall_id:
                                add_interior(bbox_list, polygon)

                    # Insert window or door bbox as Opening
                    add_opening(bboxes_window, surface_element, "Window")
                    add_opening(bboxes_door, surface_element, "Door")

    print("Step 7: Write final GML file with LOD3 buildings.")
    tree.write(CITYGML_OUTPUT_PATH, pretty_print = True, xml_declaration = True, encoding='UTF-8')

    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()
