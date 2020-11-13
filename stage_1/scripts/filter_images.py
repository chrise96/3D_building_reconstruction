"""
While the overall accuracy of the GNSS/INS sensor values are fairly high, it must 
be noted that faulty location values still occur. 

Validate the quality of the extracted facade texture images in the folder IMAGES_PATH
and manually remove invalid ones.

Run from the root of the "stage_1" folder, use: python3 -m scripts.filter_images
"""

import pandas as pd
import time
import os
import shutil

IMAGES_PATH = "texture_output/"
INPUT_NAME = "output_stage1.csv"
OUTPUT_NAME = "output_stage1_filtered"

def main():
    print("--- Start ---")

    # Start timer
    start_time = time.time()

    # Get the input csv with metadata of facade texture images
    df = pd.read_csv(INPUT_NAME, dtype={"pand_id": object})

    images = []
    for data in os.listdir(IMAGES_PATH):
        filename = os.path.splitext(data)[0]
        if filename.endswith(".jpeg"):
            images.append(filename)

    df_output = df[df["texture_filename"].isin(files)].reset_index()

    # Save the filtered file
    filtered_df = df_output[["pand_id", "visible_point_one", "visible_point_two", "texture_filename"]]
    compression_opts = dict(method="zip", archive_name=OUTPUT_NAME + ".csv")
    filtered_df.to_csv(OUTPUT_NAME + "facade_textures_filtered.csv", index=False, 
        compression=compression_opts)

    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()
