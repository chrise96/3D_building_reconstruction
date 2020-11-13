"""
The use of the functions in this python file are optional and can help
with generating a better LOD3 model.
"""
import os
from PIL import Image 

from src.geometry import euclidean_distance

def get_duplicate_buildings(root, nsmap):
    """
    The provided CityGML files often have duplicate buildings. We perform
    an extra step to remove duplicates. The duplicates are most of the time 
    parts of a complete building. Therefore, we filter for the largest area 
    size and keep that building in the CityGML file.
    
    This is an optional step.
    """
    # Get all pand ids in CityGML file
    building_citygml = []
    for pand_id in root.findall(".//bldg:Building/gml:name", namespaces=nsmap):
        building_citygml.append(pand_id.text)

    # Get all duplicate pand ids in CityGML file
    building_duplicates = set([x for x in building_citygml if building_citygml.count(x) > 1])

    # Get building with biggest area length
    unique_buildings = {}
    if building_duplicates is not None:
        for building in root.findall(".//bldg:Building", namespaces=nsmap):
            pand_id = building.find(".//gml:name", namespaces=nsmap)
            if pand_id.text in building_duplicates:
                # Get lowerCorner and upperCorner of a building
                lower_corner = building.find(".//gml:lowerCorner", namespaces=nsmap).text.split()
                upper_corner = building.find(".//gml:upperCorner", namespaces=nsmap).text.split()
                
                # Get building area length
                building_length = euclidean_distance(float(lower_corner[0]), float(lower_corner[1]),
                                                     float(upper_corner[0]), float(upper_corner[1]))
                
                building_uuid = building.attrib["{http://www.opengis.net/gml}id"]

                # Save the building uuid with the largest area length
                if pand_id.text not in unique_buildings:
                    # Add new pand_id
                    unique_buildings[pand_id.text] = {"building_uuid": building_uuid, "building_length": building_length}
                else:
                    # Update pand_id with larger area length and corresponding uuid
                    if building_length > unique_buildings[pand_id.text]["building_length"]:
                        unique_buildings[pand_id.text] = {"building_uuid": building_uuid, "building_length": building_length}

    # Return duplicate buildings
    return building_duplicates, unique_buildings

def crop_to_facade(height_data, images_path, cropped_images_path, image_height_irl):
    """
    Based on the previously calculated height of the facades in meter,
    we crop the texture images.
    
    This is an optional step to manually validate the quality of 
    the height calculation and the resulting cropped images.
    """
    for row in height_data:    
        filename = row["texture_filename"]

        facade_texture = os.path.join(images_path, filename + ".jpeg")

        # Check if file exists
        if os.path.isfile(facade_texture):
            # Get image info
            im = Image.open(facade_texture)
            image_width, image_height = im.size # Height is always the same value (900 px)

            facade_height = row["high_z"] - row["low_z"]

            # Get height of facade in pixels
            pixel_facade_height = int(image_height - (image_height / image_height_irl * facade_height))
            
            # Save the cropped image with settings (left, top, right, bottom)
            cropped = im.crop((0, pixel_facade_height, image_width, image_height))
            cropped.save(os.path.join(cropped_images_path, filename + ".jpeg"))
