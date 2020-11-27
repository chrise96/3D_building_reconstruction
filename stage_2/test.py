# Some basic setup
# import some common libraries
from collections import defaultdict
import zipfile
import os
import numpy as np
import cv2
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# Setup detectron2 logger
import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()
# import some common detectron2 utilities
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

OUTPUT_NAME = "output_stage2"
DRAW_PREDICTIONS = False

def draw_bbox(myfile, bboxes, filename):
    """
    Plot bbox in original image
    """
    # Create figure and axes
    fig,ax = plt.subplots(figsize=(10, 10))
    plt.axis("off")

    for box in bboxes:
        # Create a Rectangle patch
        x0, y0, x1, y1 = box
        width = x1 - x0
        height = y1 - y0

        rect = mpl.patches.Rectangle((x0, y0), width, height, linewidth=1,
            edgecolor="r", facecolor="none")

        # Add the patch to the Axes
        ax.add_patch(rect)

    # Read image in grayscale mode
    original_img = np.array(Image.fromarray(myfile))
    # Display the image
    ax.imshow(original_img, cmap = plt.cm.gray)

    fig.savefig(f"output_images/{filename}.png", dpi=200, bbox_inches="tight", pad_inches=0)

def non_max_suppression(boxes, probs=None, overlap_thresh=0.15):
    """
    This is a Python version used to implement the Soft NMS algorithm.
    Original Paper：Soft-NMS--Improving Object Detection With One Line of Code
    """
    # If there are no boxes, return an empty list
    if len(boxes) == 0:
        return []

    # If the bounding boxes are integers, convert them to floats -- this
    # Is important since we"ll be doing a bunch of divisions
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    # Initialize the list of picked indexes
    pick = []

    # grab the coordinates of the bounding boxes
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    # Compute the area of the bounding boxes and grab the indexes to sort
    # (in the case that no probabilities are provided, simply sort on the
    # bottom-left y-coordinate)
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = y2

    # If probabilities are provided, sort on them instead
    if probs is not None:
        idxs = probs

    # Sort the indexes
    idxs = np.argsort(idxs)

    # Keep looping while some indexes still remain in the indexes list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the index value
        # to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # find the largest (x, y) coordinates for the start of the bounding
        # box and the smallest (x, y) coordinates for the end of the bounding
        # box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # compute the ratio of overlap
        overlap = (w * h) / area[idxs[:last]]

        # delete all indexes from the index list that have overlap greater
        # than the provided overlap threshold
        idxs = np.delete(idxs, np.concatenate(([last],
            np.where(overlap > overlap_thresh)[0])))

    # return only the bounding boxes that were picked
    return boxes[pick].astype("float")

def instances_to_dict(all_instances, filename, class_names):
    """
    Save the predicted bounding boxes to a dictionary
    """
    num_instances = len(all_instances)
    if num_instances == 0:
        return None

    classes = all_instances.pred_classes
    labels = [class_names[x] for x in classes]
    boxes = all_instances.pred_boxes.tensor.numpy()
    scores = all_instances.scores.numpy()

    predictions = defaultdict(list)
    predictions_temp = defaultdict(list)

    predictions["texture_filename"] = filename

    for i in range(num_instances):
        if labels[i] == "window":
            predictions_temp["bboxes_window"].append(boxes[i])
            predictions_temp["scores_window"].append(scores[i])
        elif labels[i] == "door":
            predictions_temp["bboxes_door"].append(boxes[i])
            predictions_temp["scores_door"].append(scores[i])

    # Non max suppression
    bboxes_window = non_max_suppression(np.array(predictions_temp["bboxes_window"]),
        predictions_temp["scores_window"])
    bboxes_door = non_max_suppression(np.array(predictions_temp["bboxes_door"]),
        predictions_temp["scores_door"])

    # bboxes rounded to 1 decimal
    predictions["bboxes_window"] = [[np.round(float(i), 1) for i in nested] for nested in bboxes_window]
    predictions["bboxes_door"] = [[np.round(float(i), 1) for i in nested] for nested in bboxes_door]

    return predictions

def main():
    """
    An example script on how to iterate over the images in a zip file
    and get predictions from Mask R-CNN.
    """
    class_names = ["sky", "window", "door"]
    cfg = get_cfg()
    cfg.merge_from_file(
        "detectron2/configs/COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    ) # Faster and BBOX only, train with: detectron2/configs/COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml
    cfg.OUTPUT_DIR = "model_output"
    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model.pth")
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(class_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7
    predictor = DefaultPredictor(cfg)

    # An example on how to use zipfile
    zip_file = zipfile.ZipFile("datasets/test/images.zip")

    rows_list = []
    for name in zip_file.namelist():
        if name.endswith(".jpeg"):
            filename = name.split("/")[-1].split(".jpeg")[0]

            # Open the images with the openCV reader because BGR order is used in Detectron2
            pic = zip_file.read(name)
            im = cv2.imdecode(np.frombuffer(pic, np.uint8), 1)

            if im is not None:
                outputs = predictor(im)

                all_instances = outputs["instances"].to("cpu")

                # Save the predicted bounding boxes to a dict
                predictions = instances_to_dict(all_instances, filename, class_names)

                if predictions is not None:
                    # Draw predictions
                    if DRAW_PREDICTIONS:
                        draw_bbox(im, predictions["bboxes_window"] + predictions["bboxes_door"], filename)

                    # Save the data to the list
                    rows_list.append(predictions)

    # Save this file
    df_output = pd.DataFrame(rows_list)
    compression_opts = dict(method="zip", archive_name = OUTPUT_NAME + ".csv")
    df_output.to_csv(OUTPUT_NAME + ".zip", index=False, compression=compression_opts)

if __name__ == "__main__":
    main()
