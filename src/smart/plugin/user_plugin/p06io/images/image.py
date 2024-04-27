#!/usr/bin/env python3

__author__ = ["Jan Garrevoet"]

import os

import numpy
import PIL.Image
try:
    import fabio
    FABIO_SUPPORT = True
except ImportError:
    FABIO_SUPPORT = False


#########
# Image #
#########

class Image(object):
    """
    Class to handle reading and writing from and to various images types.
    """

    ############
    # __init__ #
    ############

    def __init__(self, verbosity=0):
        """
        Class to handle reading and writing from and to various images types.

        Parameters
        ----------
        verbosity : int, optional
            The verbosity level.
        """

        self.verbosity = verbosity

    ########
    # read #
    ########

    def read(self, file_path, transpose=False, device=None):
        """
        Reads an image.

        Parameters
        ----------
        file_path : str
            The path to the image file.


        transpose : bool, optional
            If True, image will be transposed.

        device : str, optional
            Device specific reading routing.
            Implemented: "pilatus"

        Returns
        -------
        numpy.ndarray
            The image as a numpy array.

        header : dict
            The header in case of device specific read.
        """

        file_ext = os.path.splitext(file_path)[1]
        if file_ext in [".edf", ".cbf"]:
            if FABIO_SUPPORT and device is None:
                tmp = fabio.open(file_path).data
            elif FABIO_SUPPORT:
                f_data = fabio.open(file_path)
                tmp = f_data.data
            else:
                raise IOError(
                    "Unable to read this file format. Try installing fabio."
                )
        else:
            tmp = numpy.asarray(PIL.Image.open(file_path))

        if transpose:
            tmp = tmp.transpose()

        if device is None:
            return tmp
        elif device == "pilatus":
            from datetime import datetime
            header = {}
            cbf_header = f_data.header["_array_data.header_contents"]

            for index, item in enumerate(cbf_header.split("\r\n")):
                item = item[2:]
                if item.startswith("Detector: "):
                    item = item.replace("Detector: ", "")
                    det_type, det_sn = item.split(",")
                    header["detector_type"] = det_type
                    header["detector_sn"] = det_sn

                elif index == 1:
                    header["acquisition_time"] = datetime.fromisoformat(item).timestamp()

                elif item.startswith("Pixel_size"):
                    item = item.replace("Pixel_size ", "")
                    header["pixel_size"] = item

                elif item.startswith("Silicon sensor, thickness"):
                    item = item.replace("Silicon sensor, thickness", "")
                    header["active_material"] = "Si"
                    header["active_material_thickness"] = float(item)

                elif item.startswith("Exposure_time "):
                    item = item.replace("Exposure_time ", "")
                    item = item.replace("s", "")
                    header["exposure_time"] = float(item)

                elif item.startswith("Exposure_period "):
                    item = item.replace("Exposure_period ", "")
                    item = item.replace("s", "")
                    header["exposure_period"] = float(item)

                elif item.startswith("Count_cutoff "):
                    item = item.replace("Count_cutoff ", "")
                    item = item.replace("counts", "")
                    header["count_cutoff"] = float(item)

                elif item.startswith("Threshold_setting: "):
                    item = item.replace("Threshold_setting: ", "")
                    item = item.replace("eV", "")
                    header["threshold"] = float(item)

            return tmp, header

    ########
    # save #
    ########

    def save(
            self, file_path, image, transpose=False, imagej=False,
            metadata={}):
        """
        Saves an image.

        Parameters
        ----------
        file_path : str
            The path to the image file.

        image : numpy.ndarray
            Image to be saved.

        transpose : boolean, optional
            If True, image will be transposed.

        imagej : boolean, optional
            Write the metadata in an ImageJ format.

        metadata : dict, optional
            Write metadata to the file, if the file format supports it.
        """

        if transpose:
            image = image.transpose()

        file_type = os.path.splitext(file_path)[1]
        supports_metadata = [".tiff", ".tif"]

        if len(metadata) != 0 and file_type not in supports_metadata:
            raise NotImplementedError(
                "Metadata is not supported by this file format"
            )

        # TIFF
        if file_type in [".tiff", ".tif"]:
            tiff_md = {}

            if imagej:
                description = "ImageJ=1.53t\n"
            else:
                description = ""

            for key, value in metadata.items():
                if imagej:
                    if key == "origin":
                        description += "xorigin={}\nyorigin={}\n".format(
                            -value["x"]*1/metadata["pixel_size"]["x"],
                            -value["y"]*1/metadata["pixel_size"]["y"],
                        )

                    elif key == "unit":
                        description += f"unit={value}\n"

                    elif key == "pixel_size":
                        tiff_md[282] = 1 / value["x"]
                        tiff_md[283] = 1 / value["y"]

                else:
                    if key == "description":
                        description = description

                    # Need to convert to mm.
                    # FIXME: not done yet.
                    if key == "pixel_size":
                        tiff_md[282] = 1 / value["x"]
                        tiff_md[283] = 1 / value["y"]

            # Now add the description
            if imagej:
                tiff_md[270] = description

            return PIL.Image.fromarray(image).save(
                file_path, tiffinfo=tiff_md
            )

        elif file_type in [".cbf"]:
            if FABIO_SUPPORT:
                img = fabio.cbfimage.CbfImage(data=image)
                img.write(file_path)
            else:
                raise IOError(
                    "Unable to write this file format. Try installing fabio."
                )

        # Other file formats
        else:
            return PIL.Image.fromarray(image).save(file_path)
