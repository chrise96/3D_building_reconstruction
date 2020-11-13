"""
The geospatial location of a façade image is obtained during the first stage of the
proposed pipeline. In addition, the real height of a building façade is calculated
in this stage; this information is not provided by Key register Addresses and
Buildings (BAG). Note that the height of each extracted image is hard-coded and
corresponds to an actual height value of 30 meters. Each building in 3D Amsterdam
city model contains a building id identical to BAG. We use this given to match an
extracted façade image to the corresponding building in the 3D city model.
"""

import pandas as pd
import time
import os
from lxml import etree as ET
import math

from src.optional import *

# Paths
CITYGML_PATH = "CityGML/LOD2_120700-485100.gml"
CITYGML_OUTPUT_PATH = "CityGML/LOD2_120700-485100_filtered.gml"
CSV_PATH = "CSV/output_stage1.csv"
CSV_BBOX_PATH = "CSV/output_stage2.csv"
CSV_OUTPUT_PATH = "CSV/output_stage3.csv"
IMAGES_PATH = "images/"
CROPPED_IMAGES_PATH = "texture_cropped/"

# Namespaces of XML file
NSMAP = {
    "bldg": "http://www.opengis.net/citygml/building/2.0",
    "gml": "http://www.opengis.net/gml",
    "city": "http://www.opengis.net/citygml/2.0"
}

IMAGE_HEIGHT_IRL = 30 # Defined in stage 1
MIN_NAP = -5

DEBUG = False

def get_facade_height(root, df):
    """
    Get the "best" 3D wall surface candidate for a 2D texture image
    and calculate the lowest and highest point of the wall surface.

    The variable low_z is important for the bbox coordinate
    transformation step later.
    """
    height_data = []
    for buildingElement in root.findall(".//city:cityObjectMember", NSMAP):
        # Initialze variables
        low_z = None
        high_z = None
        shortest_distance = float("inf")
        height_dict = {}

        # Get pand_id in current element of XML
        pand_id = buildingElement.find(".//bldg:Building/gml:name", namespaces=NSMAP)
        if pand_id is not None:
            # Check if the pand_id is inside the dataframe
            df_row = df.loc[pand_id.text == df["pand_id"]]
            if not df_row.empty:
                # Take this point from the facade texture to compare with the 3D model later
                visible_point_one = eval(df_row["visible_point_one"].values[0]) # TODO dont use eval

                for surfaceElement in buildingElement.findall(".//bldg:WallSurface", NSMAP):
                    for polygon in surfaceElement.findall(".//gml:posList", NSMAP):
                        # Create a nested list of [x,y,z] out of the poslist content
                        poslist = [float(x) for x in polygon.text.split()]
                        xyz_poslist = [poslist[x:x+3] for x in range(0, len(poslist),3)]

                        # Sort on z axis
                        xyz_poslist.sort(key=lambda x: x[2])

                        # Get random point of a wall (lowest z value)
                        random_wall_point = xyz_poslist[0]

                        # Determine distance 2D texture image to a wallSurface of 3D model
                        distance_2d_3d = math.sqrt(((visible_point_one[0] - random_wall_point[0])**2) +
                                             ((visible_point_one[1] - random_wall_point[1])**2))

                        # A wall candidate must be 5 meter or higher
                        # And should not be located 5 meter above NAP
                        if((xyz_poslist[-1][2] - xyz_poslist[0][2]) > 5) and (xyz_poslist[0][2] < 5):
                            # Save the shortest distance, this our wall candidate for the facade texture
                            if distance_2d_3d < shortest_distance:
                                # Get the lowest and highest z value for this wall
                                low_z = round(xyz_poslist[0][2], 2)
                                high_z = round(xyz_poslist[-1][2], 2)

                                shortest_distance = distance_2d_3d

                # Check if high_z (or low_z) have new values
                if high_z is not None:
                    # Validating the max height of the facade possible on image
                    # And outlier removal
                    if high_z <= IMAGE_HEIGHT_IRL and low_z > MIN_NAP:
                        # Save the info
                        height_dict["pand_id"] = pand_id.text
                        height_dict["high_z"] = high_z
                        height_dict["low_z"] = low_z
                        height_dict["texture_filename"] = df_row["texture_filename"].values[0]

                        height_data.append(height_dict)
    return height_data

def main():
    # Check if input files can be found
    if not os.path.isfile(CITYGML_PATH):
        print("Input CityGML file not found. Aborting.")
        return

    if not os.path.isfile(CSV_PATH) or not os.path.isfile(CSV_BBOX_PATH):
        print("Input csv files not found. Aborting.")
        return      

    print("--- Start ---")

    # Start timer
    start_time = time.time()

    # Get the CityGML file
    parser = ET.XMLParser(remove_blank_text = True) # Remove spaces etc.
    tree = ET.parse(CITYGML_PATH, parser)
    root = tree.getroot()

    # Get the CSV file
    df = pd.read_csv(CSV_PATH, dtype={"pand_id": object})
    pand_ids = df["pand_id"].astype(str).values.tolist()

    # Optional step to remove duplicate pand ids from invalid CityGML file
    duplicate_pand_ids, unique_buildings = get_duplicate_buildings(root, NSMAP)

    print("Step 1: Remove buildings where windows and doors are not predicted in the previous stage")
    for pand_id in root.findall(".//bldg:Building/gml:name", namespaces=NSMAP):
        if pand_id.text not in pand_ids:
            # Remove not predicted buildings
            actual_element = pand_id.getparent().getparent()
            actual_element.getparent().remove(actual_element)
        elif pand_id.text in duplicate_pand_ids:
            building_uuid = pand_id.getparent().attrib["{http://www.opengis.net/gml}id"]
            if building_uuid != unique_buildings[pand_id.text]["building_uuid"]:
                # Remove duplicate buildings
                actual_element = pand_id.getparent().getparent()
                actual_element.getparent().remove(actual_element) 

    print("Step 2: Get height of facade using CityGML file")
    height_data = get_facade_height(root, df)

    # Set the DEBUG variable to true if you want to save cropped images
    if DEBUG:
        if not os.path.exists(CROPPED_IMAGES_PATH):
            os.makedirs(CROPPED_IMAGES_PATH)
        else:
            print("The 'texture_cropped' folder already exists.")

        print("Optional Step: Crop texture image to height value of facade")
        crop_to_facade(height_data, IMAGES_PATH, CROPPED_IMAGES_PATH, IMAGE_HEIGHT_IRL)
        print("Manually validate and remove the invalid cropped images in path.")

    print("Step 3: LOD2 to LOD3 syntax in the CityGML file")
    tag_lod2_multisurface = tree.findall(".//bldg:lod2MultiSurface", namespaces=NSMAP)
    for tags in tag_lod2_multisurface:
        tags.tag = "{http://www.opengis.net/citygml/building/2.0}lod3MultiSurface"
    tag_lod2_solid = tree.findall(".//bldg:lod2Solid", namespaces=NSMAP)
    for tags in tag_lod2_solid:
        tags.tag = "{http://www.opengis.net/citygml/building/2.0}lod3Solid"

    print("Step 4: Save the new CityGML and CSV file")
    # GML save
    tree.write(CITYGML_OUTPUT_PATH, pretty_print = True, xml_declaration = True, encoding="UTF-8")
    # CSV merge and save
    df_bbox = pd.read_csv(CSV_BBOX_PATH, dtype={"pand_id": object})
    df_height = pd.DataFrame(height_data)
    df_output = df_height.merge(df_bbox, on="texture_filename").merge(df, on="texture_filename")
    df_output.to_csv(CSV_OUTPUT_PATH, index=False)

    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()