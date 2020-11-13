"""
Amsterdam API description: https://api.data.amsterdam.nl/api/
"""

from io import BytesIO
import json
import requests
from PIL import Image
from osgeo import ogr, osr

def get_pano_id(mission_year, bbox):
    """
    Get panoramic image id's for a user defined bounding box region
    """
    pano_url = f"https://api.data.amsterdam.nl/panorama/panoramas/?tags=mission-{mission_year}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}&srid=28992"

    with requests.get(pano_url) as response:
        pano_data_all = json.loads(response.content)

    pano_data = pano_data_all['_embedded']['panoramas']

    pano_id = []
    for item in pano_data:
        pano_id.append(item['pano_id'])

    # Check for next page with data
    next_page = pano_data_all['_links']['next']['href']

    # Exit the while loop if there is no next page
    while next_page:
        with requests.get(next_page) as response:
            pano_data_all = json.loads(response.content)

        pano_data = pano_data_all['_embedded']['panoramas']

        # Append the panorama id's to the list
        for item in pano_data:
            pano_id.append(item['pano_id'])

        # Check for next page
        next_page = pano_data_all['_links']['next']['href']

    return pano_id

def get_pano_image(pano_id):
    """
    Get a panoramic image and its initial location coordinates
    and convert it from WGS84 (EPSG:4326) to Rijksdriehoek (EPSG:28992)
    """
    pano_url = f"https://api.data.amsterdam.nl/panorama/panoramas/{pano_id}/"
    with requests.get(pano_url) as response:
        pano_data = json.loads(response.content)

    geom = pano_data['geometry']['coordinates']

    # WGS84 to Rijksdriehoek (RD) conversion
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(geom[0], geom[1])
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    target = osr.SpatialReference()
    target.ImportFromEPSG(28992)
    transform = osr.CoordinateTransformation(source, target)
    point.Transform(transform)

    # Get image_url from API
    image_url = pano_data['_links']['equirectangular_medium']['href']

    return str(image_url), (point.GetX(), point.GetY())

def get_buildings_in_range(observer, radius):
    """
    For a panoramic image, get the buildings that are whitin a user defined range.
    """
    bag_url = f"https://api.data.amsterdam.nl/bag/pand/?locatie={observer[0]},{observer[1]},{radius}&detailed=!"
    with requests.get(bag_url) as response:
        bag_data = json.loads(response.content)['results']

    return bag_data

def get_building_polygons(pand_json):
    """ Get the polygon of a building """
    building_polygons = {}

    # Loop over json content
    for item in pand_json:
        pand_id = item['pandidentificatie']
        pand_polygon = item['geometrie']['coordinates'][0]

        # A polygon should have at least 3 vertices to be a valid polygon
        if(len(pand_polygon) > 2 and pand_id):
            # Verify counter-clockwise winding order
            # TODO (Removed this because it happens rarely and slows the process down)

            building_polygons[pand_id] = pand_polygon

    return building_polygons

def download_pano_image(pano_url):
    """ Download a panoramic image from the API """
    try:
        response = requests.get(pano_url)
        source_image = Image.open(BytesIO(response.content))
    except requests.exceptions.RequestException:
        print('HTTP Request failed. Aborting.')
        return

    return source_image
