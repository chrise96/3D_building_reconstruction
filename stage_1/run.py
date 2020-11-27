"""
The first stage of the pipeline determines — within a captured panoramic image sequence — the
texture region for each building (pand_id) to be reconstructed.

There are three input sources used in this stage: BAG building footprint data, panoramic
images, and GNSS/INS sensor values. The initial GNSS/INS sensor specifies the camera’s
geospatial location and orientation information that correspond to each of the panoramic
images.

NOTE: Change the variables BBOX_REGION and MISSION_YEAR to your own settings!
"""

import os
import time
from multiprocessing import Process, Manager
from shapely.geometry import Point, Polygon
import pandas as pd
import numpy as np

# External Python files
from src.api_request import *
from src.extract_texture import export_line_to_texture
from src.visible_view import generate_arrangement, get_visibility_polygon, point_in_visibility_polygon
from src.array_math import get_midpoint, vector_length, vector
from src.furthest_pair import get_furthest_pair

# Multiprocessing options
NUM_CPUS = 5

# API options
BBOX_REGION = [122300.00,486628.78,122400.00,486475.48]
MISSION_YEAR = 2018 # API tag
SEARCH_RADIUS = 10 # Building search radius from an initial panoramic image location

# Texture options
TEXTURE_RESOLUTION = 30
IMAGE_HEIGHT_IRL = 30 # In meters, buildings above 30m are therefore partly cropped
CAMERA_HEIGHT = 2 # Height of the camera mounted on the car

# Validation options before rectification (strict settings)
MIN_DISTANCE = 1.7 # Min distance camera to building
MAX_DISTANCE = 9
MIN_BUILDING_AREA = 15
MAX_BUILDING_AREA = 400

IMAGES_OUTPUT = "texture_output/"
OUTPUT_NAME = "output_stage1"

def get_visible_building_edges(pano_ids, facade_data):
    """
    Estimation of buildings in range and identify visible building
    edges in 2D map.

    Function will be executed on different workers
    """
    for pano_id in pano_ids:
        # Get the panoramic image url and the location of the "observer"
        image_url, observer = get_pano_image(pano_id)

        # Get BAG "pand" information. Search radius in meters from point "near"
        pand_json = get_buildings_in_range(observer, SEARCH_RADIUS)

        # Get a dict of the buildings (footprint data) in range
        building_polygons = get_building_polygons(pand_json)

        # Validation checks on the GPS location and building polygons
        building_polygons = get_admissible_data(observer, building_polygons)

        if not building_polygons:
            #print("No admissible building polygons in range. Go to the next panorama")
            continue

        # Generate the outlines of the arrangement
        arr = generate_arrangement(observer, building_polygons.values())

        # Get the Visibility Polygon for point q
        visibility_polygon = get_visibility_polygon(arr, observer)

        # Get two most distant visible points of a builing
        get_facade_coordinates(building_polygons, visibility_polygon, observer, image_url, facade_data)

def extract_facade_texture(grouped_chunk):
    """
    Extract facade textures from panoramic images.

    Function will be executed on different workers
    """
    for group_name, df_group in grouped_chunk:
        # Get the panoramic image
        source_image = download_pano_image(group_name)
        if source_image is not None:
            # Iterate over the rows that are inside a group
            for _, row in df_group.iterrows():
                # Create the facade texture
                image_file = export_line_to_texture((row["visible_point_one"], row["visible_point_two"]),
                                                    TEXTURE_RESOLUTION, IMAGE_HEIGHT_IRL, CAMERA_HEIGHT,
                                                    source_image, row["observer"])
                # Save the facade texture
                filename = row["texture_filename"]
                image_file.save(f"{IMAGES_OUTPUT}{filename}.jpeg", "jpeg")

def get_admissible_data(observer, building_polygons):
    """
    Validate the GPS location of a panoramic image
    and the size of a building.
    """
    observer_point = Point(observer)

    admissible_building_polygons = {}
    for k, v in list(building_polygons.items()):
        building_poly = Polygon(v)

        # Check if point q is too close to a building
        if building_poly.exterior.distance(observer_point) < MIN_DISTANCE:
            print("GNSS/INS measurement error found! Too close to building.")
            return {}

        # Check if point q is inside a building (GNSS/INS error)
        if observer_point.intersects(building_poly):
            print("GNSS/INS measurement error found! Point inside building.")
            return {}

        # Check for building area sizes that we ignore (Too large: Bijenkorf, too small: mini snackbar)
        if MIN_BUILDING_AREA < building_poly.area < MAX_BUILDING_AREA:
            admissible_building_polygons[k] = v

    return admissible_building_polygons

def get_facade_coordinates(building_polygons, visibility_polygon, observer, image_url, facade_data):
    """ Get the two most distant visible points of a builing """
    for pand_id in building_polygons.keys():
        new_data = {}

        # Get all the points from this polygon that are in the visibility polygon
        visible_points = point_in_visibility_polygon(building_polygons[pand_id], visibility_polygon)

        # Check if there are two or more visible points for a building
        if len(visible_points) >= 2:
            # Get from a list of items the furthest pair where we keep the (winding) order of the list
            visible_points_left_right = get_furthest_pair(visible_points, observer)

            # Two validation checks

            # Calculate the distance between two points
            vector_facade = vector(visible_points_left_right[0], visible_points_left_right[1])
            facade_length = vector_length(vector_facade)

            # Validation 1. The length of a "normal" facade is at least more than 2 meters
            if facade_length < 2:
                # Go to next iteration of for loop, check for other buildings in same panorama
                break

            # Distance observer to middlepoint
            midpoint = get_midpoint(visible_points_left_right)
            vector_distance = vector(midpoint, observer)
            new_data["distance"] = round(vector_length(vector_distance), 6)

            # Validation 2. Errors are found in the rectification process when the distance is above 9
            if new_data["distance"] > MAX_DISTANCE:
                # Go to next iteration of for loop, check for other buildings in same panorama
                break

            # Fill dict after all the validation checks
            new_data["pand_id"] = str(pand_id)
            new_data["visible_point_one"] = tuple(visible_points_left_right[0]) # TODO why a tuple
            new_data["visible_point_two"] = tuple(visible_points_left_right[1])
            new_data["pano_image_url"] = image_url
            new_data["observer"] = observer
            # The distance value makes the filename unique
            new_data["texture_filename"] = str(pand_id) + "_" + str(new_data["distance"])

            facade_data.append(new_data)

def save_results(df):
    """ Save results of extracted facade textures """
    df_output = df[["pand_id", "visible_point_one", "visible_point_two", "texture_filename"]]
    compression_opts = dict(method="zip", archive_name=OUTPUT_NAME + ".csv")
    df_output.to_csv(OUTPUT_NAME + ".zip", index=False, compression=compression_opts)

def main():
    """
    Identify, rectify and extract the texture region of buildings
    from a panoramic image sequence.
    """

    # Create a directory, first check if it already exists
    if not os.path.exists(IMAGES_OUTPUT):
        os.makedirs(IMAGES_OUTPUT)
    else:
        print("The 'texture_output' folder already exists.")

    print("--- Start ---")

    # Start timer
    start_time = time.time()

    # Get the panoramas (from API)
    pano_ids = get_pano_id(MISSION_YEAR, BBOX_REGION)

    # Split the array into N chunks
    pano_id_chunk = np.array_split(pano_ids, NUM_CPUS)

    print("Step 1: Identify visible building edges in range of a panoramic image")

    facade_data = Manager().list()
    jobs = []
    for s in pano_id_chunk:
        j = Process(target=get_visible_building_edges, args=(s, facade_data))
        jobs.append(j)
        j.start()
    for j in jobs:
        j.join()

    print("Step 2: Drop duplicate facade textures")

    # Create pandas dataframe to easily manipulate the data
    df = pd.DataFrame(list(facade_data))

    # Drop duplicate facade rows, keep the ones with shortest distance.
    df = df.sort_values("distance", ascending=True).drop_duplicates(subset =
        ["visible_point_one", "visible_point_two"]).sort_index().reset_index(drop=True)

    # Group by image_url and later iterate over dataframe grouped by image_url
    df_group = df.groupby(["pano_image_url"]) # Unfortunately, no parallel apply function in pandas

    # Split the dataframe into N chunks (sub-dataframes)
    df_group_chunk = np.array_split(df_group, NUM_CPUS)

    print("Step 3: Extract facade textures from panoramic images")

    jobs = []
    for s in df_group_chunk:
        j = Process(target=extract_facade_texture, args=([s]))
        jobs.append(j)
        j.start()
    for j in jobs:
        j.join()

    print("Step 4: Save the results")
    save_results(df)

    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()
