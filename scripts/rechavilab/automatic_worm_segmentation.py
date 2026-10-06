"""
Batch automatic segmentation with micro-sam.

Input:
    A folder containing TIFF/PNG/JPG images.

Output:
    A folder containing one instance-segmentation TIFF per input image.

Mask convention:
    0 = background
    1 = object 1
    2 = object 2
    3 = object 3
    ...

Example:

    input/
        worm001.tif
        worm002.tif
        worm003.tif

    output/
        worm001_mask.tif
        worm002_mask.tif
        worm003_mask.tif
"""

from pathlib import Path

import numpy as np
import imageio.v3 as imageio
import torch

from micro_sam import util
from micro_sam.automatic_segmentation import (
    get_predictor_and_segmenter,
    automatic_instance_segmentation,
)


# ============================================================
# SETTINGS
# ============================================================

# Folder containing your original images
INPUT_FOLDER = Path(r"C:\data\RechaviLab\R1")

# Folder where masks will be written
OUTPUT_FOLDER = Path(r"C:\data\RechaviLab\R1\microsam_output")

# ------------------------------------------------------------
# Image formats to process
# ------------------------------------------------------------
# You can add/remove extensions here.
IMAGE_EXTENSIONS = {
    ".tif",
    ".tiff",
    # ".png",
    # ".jpg",
    # ".jpeg",
}

# ------------------------------------------------------------
# micro-sam model
# ------------------------------------------------------------
# Leave this as None to use the default micro-sam model.
#
# If you know which model you are currently using successfully,
# you can put it here, for example:
#
# MODEL_TYPE = "vit_b_lm"
#
MODEL_TYPE =  "vit_b_lm"

# ------------------------------------------------------------
# Segmentation mode
# ------------------------------------------------------------
#
# Options:
#     "apg" = Automatic Prompt Generation
#     "ais" = Automatic Instance Segmentation
#     "amg" = Automatic Mask Generation
#
# APG/AIS require a micro-sam model with the additional
# instance-segmentation decoder.
#
SEGMENTATION_MODE = "apg"

# ------------------------------------------------------------
# Device
# ------------------------------------------------------------
#
# "cpu" is intentional here because you said your current
# micro-sam setup works on CPU.
#
DEVICE = "cpu"

# ------------------------------------------------------------
# Skip images whose output already exists?
# ------------------------------------------------------------
#
# This is useful if you stop the script halfway through a
# large dataset and want to resume later.
#
SKIP_EXISTING = True


# ============================================================
# FUNCTIONS
# ============================================================

def get_image_files(folder):
    """Return all supported image files in the folder."""
    files = []

    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            image = imageio.imread(path)
            print(f"found image: {path.name}")
            print("  shape:", image.shape)
            print("  dtype:", image.dtype)
            print("  type:", type(image))
            # # RGB -> grayscale
            # if image.ndim == 3 and image.shape[-1] == 3:
            #     print("  Converting RGB to grayscale")
            #     image = (
            #             0.299 * image[..., 0]
            #             + 0.587 * image[..., 1]
            #             + 0.114 * image[..., 2]
            #     ).astype(np.uint8)

            print(f"  Image passed to micro-sam: {image.shape}")

            files.append(path)
    return sorted(files)


def make_output_path(input_path):
    """Create the output filename corresponding to an input."""
    return OUTPUT_FOLDER / f"{input_path.stem}_mask.tif"


def main():

    # --------------------------------------------------------
    # Check input folder
    # --------------------------------------------------------

    if not INPUT_FOLDER.exists():
        raise FileNotFoundError(
            f"Input folder does not exist:\n{INPUT_FOLDER.resolve()}"
        )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    image_files = get_image_files(INPUT_FOLDER)

    if not image_files:
        raise RuntimeError(
            f"No images found in:\n{INPUT_FOLDER.resolve()}\n\n"
            f"Supported extensions: {IMAGE_EXTENSIONS}"
        )

    print()
    print("=" * 60)
    print("micro-sam batch automatic segmentation")
    print("=" * 60)
    print(f"Input folder : {INPUT_FOLDER.resolve()}")
    print(f"Output folder: {OUTPUT_FOLDER.resolve()}")
    print(f"Images found : {len(image_files)}")
    print(f"Device       : {DEVICE}")
    print(f"Segmentation : {SEGMENTATION_MODE}")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Determine model
    # --------------------------------------------------------

    if MODEL_TYPE is None:
        model_type = util._DEFAULT_MODEL
    else:
        model_type = MODEL_TYPE

    print(f"Loading micro-sam model: {model_type}")
    print()

    # --------------------------------------------------------
    # Create predictor + automatic segmenter ONCE.
    #
    # This is important. We don't want to reload the model
    # for every image.
    # --------------------------------------------------------


    predictor, segmenter = get_predictor_and_segmenter(
        model_type=model_type,
        checkpoint=None,
        device=torch.device(DEVICE),
        segmentation_mode=SEGMENTATION_MODE,
        is_tiled=False,
        # tile_shape=(384, 384),
        # halo = (64, 64)
    )

    print("Model loaded.")
    print()

    # --------------------------------------------------------
    # Process images
    # --------------------------------------------------------

    total = len(image_files)

    for index, image_path in enumerate(image_files, start=1):

        output_path = make_output_path(image_path)

        print("-" * 60)
        print(f"[{index}/{total}] {image_path.name}")

        # ----------------------------------------------------
        # Skip already processed images
        # ----------------------------------------------------

        if SKIP_EXISTING and output_path.exists():
            print("  Output already exists -> skipping")
            continue

        # ----------------------------------------------------
        # Run micro-sam automatic segmentation
        # ----------------------------------------------------


        automatic_instance_segmentation(
            predictor=predictor,
            segmenter=segmenter,
            input_path=image_path,
            output_path=output_path,
            ndim=2,
            verbose=False,
        )

        # ------------------------------------------------
        # Read result so we can report how many objects
        # were detected.
        # ------------------------------------------------

        segmentation = imageio.imread(output_path)

        # Make sure this is an integer label image
        segmentation = np.asarray(segmentation)

        object_ids = np.unique(segmentation)
        object_ids = object_ids[object_ids != 0]

        print(f"  Objects detected: {len(object_ids)}")
        print(f"  Saved: {output_path.name}")

        # except Exception as e:
        #
        #     print(f"  ERROR processing {image_path.name}")
        #     print(f"  {type(e).__name__}: {e}")

    print()
    print("=" * 60)
    print("Finished.")
    print(f"Masks are in: {OUTPUT_FOLDER.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()