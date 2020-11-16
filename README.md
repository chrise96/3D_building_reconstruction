# Extraction of façade details from street-view panoramic images and integration in a 3D city model

In this repository, a method is presented to automatically enhance Level Of Detail 2 buildings in a 3D city model with window and door geometries, by using a panoramic image sequence. The figure below shows a schematic overview of the proposed method, a **three staged pipeline**. The first stage is based on identifying, rectifying and extracting the texture region of a building from a panoramic image sequence. In the next stage, the extracted façade texture images are used as input in a deep convolutional neural network for parsing façade details, such as windows and doors. In the third and final stage of the pipeline, the previously parsed window and door rectangles are aligned with the input LOD2 model to construct a LOD3 model. More on https://medium.com/@chrise96/a-deep-learning-approach-to-enhance-3d-city-models-caba7b2073d6. 

![](system-overview.png)


---

## Project Folder Structure

- [`stage_1`](./stage_1): Folder for the panoramic image and building analysis implementation
- [`stage_2`](./stage_2): Folder for the Faster/Mask R-CNN implementation
- [`stage_3`](./stage_3): Folder for the CityGML LOD2 to LOD3 implementation
- [`stage_1/src`](./stage_1/src): Folder for the source files specific to the stage
- [`stage_1/scripts`](./stage_1/scripts): Folder for the helper files


---

## Description of output files
- [`*.jpeg`](./stage_3/images/0363100012152551_8.426128.jpeg): Rectified façade images with the naming based on two values
    - A pand ID according to Key register Addresses and Buildings (BAG). For example: https://api.data.amsterdam.nl/bag/pand/0363100012061378/
    - A unique value, calculated using the distance in meters from the capture location of a panoramic image to the middlepoint of a façade.

- [`output_stage1.csv`](./stage_3/CSV/output_stage1.csv): A CSV file with a reference to the extracted rectified façade images. The CSV file contains the columns
    - `pand_id`: BAG pand ID.
    - `visible_point_one`: The bottom-left Rijksdriehoek coordinate of the façade (perspective of the camera/image).
    - `visible_point_two`: The bottom-right Rijksdriehoek coordinate of the façade (perspective of the camera/image).
    - `texture_filename`: The actual filename of the `*.jpeg` images.

- [`output_stage2.csv`](./stage_3/CSV/output_stage2.csv): The CSV file contains the columns
    - `bboxes_window`: A list of predicted windows, given via four pixel values: xleft, ybottom, xright, ytop.
    - `bboxes_door`:  A list of predicted doors, given via four pixel values: xleft, ybottom, xright, ytop.
    - `texture_filename`: The actual filename of the `*.jpeg` images.


---

## Dataset
For this project, the City of Amsterdam annotated over 980 high-quality segmentation mask images for training the network. Regions in Amsterdam North and West are considered with diverse architectural style buildings, to ensure the robustness and the generalization of the network. The images were manually annotated with three classes (i.e. door, window, sky) by outlining their masks and adding corresponding class labels. The dataset is available here: **TODO**


---

## Installation
Clone this repository:

```
git clone https://github.com/chrise96/3D_building_reconstruction.git
```
Install all dependencies:

```
pip install -r requirements.txt
```


---

## Design choices
- The accuracy of the GNSS/INS sensor values is an important factor that significantly affects the quality of the 
determined texture region of a building. Pose (location and orientation) optimization techniques can be used in future work to further 
improve the quality of façade texture images during the extraction process. For now, validate the quality of the extracted facade texture images, manually remove invalid ones and run:

      cd stage_1
      python3 -m scripts.filter_images
- The system treat each wall as though it is 30 meters tall. Accordingly, the visual content is partly cut off when buildings are above 30 meter. Also, the system omits buildings with an area size of 400 m2 or larger, which is calculated using the building footprint data provided by BAG. Large buildings often impose badly distorted rectification results.
- An optional step is performed on invalid CityGML files to remove duplicate buildings and keep unique ones.


---

## Citation
If you use this code or data for your research, please cite the project:
 **TODO**
