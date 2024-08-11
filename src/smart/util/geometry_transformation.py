# -*- coding: utf-8 -*-
import os


import numpy as np
from scipy import ndimage
from PyQt5 import QtCore
import pyqtgraph as pg


class scale_pixel(pg.AxisItem):
    def __init__(self, scale, shift, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scale = scale
        self.shift = shift

    def tickStrings(self, values, scale, spacing):
        return [round(value * self.scale + self.shift, 3) for value in values]

    def attachToPlotItem(self, plotItem):
        """Add this axis to the given PlotItem
        :param plotItem: (PlotItem)
        """
        self.setParentItem(plotItem)
        viewBox = plotItem.getViewBox()
        self.linkToView(viewBox)
        self._oldAxis = plotItem.axes[self.orientation]["item"]
        self._oldAxis.hide()
        plotItem.axes[self.orientation]["item"] = self
        pos = plotItem.axes[self.orientation]["pos"]
        plotItem.layout.addItem(self, *pos)
        self.setZValue(-1000)


def registration_dft_stack(
    dset,
    z_axis=(2,),
    channel=(0,),
    channel_axis=(3,),
    scale=[1, 0],
    angle=[0, 0],
    tx=[0, 0],
    ty=[0, 0],
    iterations=100,
    display=True,
    quiet=False,
    simulation=False,
    progressbar="",
    display_window="",
):
    """
    Image registration of all slices in a zstack (3-4D) using a dft model. Imreg_dft is based on the code by Christoph Gohlke.

    Parameters
    ----------
    z_axis: tuple int, optional
            appoints the z axis of the array
    channel: tuple of ints, optional
            contains the indices of the channels in the channel_axis to use as a reference. If
            channel == (-1), the integrated channels are used.
    mode: string, optional
            determines what operations are allowed during registration:
            1) translation
            2) rotation
            3) scaling
            4) rigid: translation+rotation
            5) all: translation+rotation+scaling
    iterations: int, ioptional
            number of iterations in the dft algorithm (more == better registration, at a higher computational cost)
    display: boolean, optional
            enables user supervision through display
    quiet: boolean, optional
            enable additional info on stdout
    simulation: boolean, optional
            only produces a registration on selected channels. Does not actually change the data
    progressbar: variable (optional)
            this is a variable that can be linked to a progressbar
    display_window: pyqtgraph.imageview window
            window to connect in order to display images; works in conjunction with the display boolean
    Returns
    -------
            returns the registred stack (all channels have been registred)

    Notes
    -----
    none

    Examples
    --------
    >>>

    """
    # select the middle slice as a reference
    rank = len(dset.shape)
    if isinstance(z_axis, tuple):
        z_axis = z_axis[0]
    if not isinstance(channel_axis, tuple):
        channel_axis = channel_axis

    _z = dset.shape[z_axis] // 2
    if not quiet:
        QtCore.qDebug("Reference slice {} selected".format(_z))

    if display:
        if not display_window:
            win = pg.GraphicsWindow(title="Overlay registration")
            win.resize(800, 800)
            p1 = win.addPlot()
            # Item for displaying image data
            imv = pg.ImageItem()
            p1.addItem(imv)
            win.show()
            pg.QtGui.QApplication.processEvents()
            display_window = imv

    for k in range(_z, 0, -1):
        # // get channels summed
        reg_slice = [slice(None)] * rank
        ref_slice = [slice(None)] * rank
        ref_slice[z_axis] = k
        reg_slice[z_axis] = k - 1
        if z_axis > channel_axis[0]:
            channel_axis_alt = channel_axis
        else:
            channel_axis_alt = channel_axis - 1
        dset[reg_slice] = registration_dft_slice(
            im0=dset[ref_slice],
            im1=dset[reg_slice],
            channel=(0,),
            channel_axis=channel_axis_alt,
            scale=scale,
            angle=angle,
            tx=tx,
            ty=ty,
            iterations=iterations,
            display=display,
            quiet=quiet,
            simulation=simulation,
            progressbar="",
            display_window=display_window,
        )
        if progressbar:
            progressbar.setValue(_z - k / z_axis * 100)

    for k in range(_z, dset.shape[z_axis] - 1, 1):

        if progressbar:
            progressbar.setValue(k / z_axis * 100)
    if progressbar:
        progressbar.setValue(100)
    return dset


def transform_img_dict(dset, tdict, invertx=False, inverty=False):
    """
    reimplementation of transformation operation based on a dictionary of translation/scale/rotation vectors. Also enables invert

    image is 2D
    """
    if not tdict:
        raise ValueError("Error, no vector translation/scale/rotation dictionary found")
    if inverty:
        dset = np.flipud(dset)
    if invertx:
        dset = np.fliplr(dset)
    if "angle" in tdict:
        dset = ndimage.rotate(dset, tdict["angle"], reshape=False)
    if "tvec" in tdict:
        dset = np.roll(dset, shift=int(tdict["tvec"][0]), axis=0)
    if "tvec" in tdict:
        dset = np.roll(dset, shift=int(tdict["tvec"][1]), axis=1)
    return dset


def registration_dft_slice(
    im0,
    im1,
    scale=[1, 0],
    angle=[0, 0],
    tx=[0, 0],
    ty=[0, 0],
    iterations=100,
    display=True,
    progressbar="",
    display_window="",
    order=3,
    filter_pcorr=0,
    exponent="inf",
):
    """
    Self-contained worker algorithm for image registration of 2 multi-channel slices. Imreg_dft is based on the code by Christoph Gohlke.

    Parameters
    ----------


    mode: string, optional
            determines what operations are allowed during registration:
            1) translation
            2) rotation
            3) scaling
            4) rigid: translation+rotation
            5) all: translation+rotation+scaling
    iterations: int, ioptional
            number of iterations in the dft algorithm (more == better registration, at a higher computational cost)

    Returns
    -------
            returns the registred im1

    Notes
    -----
    none

    Examples
    --------
    >>>
    """
    import imreg_dft as ird
    from sklearn.preprocessing import normalize

    # // normalize images to be registred
    rank = len(im1.shape)
    if display:
        if not display_window:
            win = pg.GraphicsWindow(title="Overlay registration")
            win.resize(800, 800)
            p1 = win.addPlot()
            # Item for displaying image data
            imv = pg.ImageItem()
            p1.addItem(imv)
            win.show()
            pg.QtGui.QApplication.processEvents()

    im1_r = np.float32(normalize(im1))
    im0_r = np.float32(normalize(im0))

    # // get transformation
    # vector_dict = ird.similarity(im0_r, im1_r, numiter=int(iterations), constraints={'scale':scale,'angle':angle, 'tx':tx, 'ty':ty})
    vector_dict = ird.similarity(
        im0_r,
        im1_r,
        numiter=int(iterations),
        order=order,
        filter_pcorr=filter_pcorr,
        exponent=exponent,
    )
    # // apply transformation to each channel
    if display:
        im2_r = ird.imreg.transform_img_dict(
            im1_r, tdict=vector_dict, bgval=None, order=1, invert=False
        )
        if not display_window:
            imv.setImage(im2_r + im0_r)
            # win.setWindowTitle('Reference slice {}; Target slice {}'.format(k,k-1))
            pg.QtGui.QApplication.processEvents()
            pg.QtGui.QApplication.processEvents()
        else:
            display_window.setImage(im2_r + im0_r)
            pg.QtGui.QApplication.processEvents()
            pg.QtGui.QApplication.processEvents()
    return vector_dict


def apply_imreg_dft(vector_dict, target):
    """
    Apply dft transformation

    :param vector_dict:
    :param target:
    :return:
    """
    import imreg_dft as ird

    # // run through all channels and transform the arrays separately
    def registration_dft_worker(
        dset,
        _axis=(0, 1),
        tdict=vector_dict,
        bgval=None,
        order=1,
        invert=False,
        fast=False,
    ):
        # // fast transform compresses the result
        if fast:
            return ird.imreg.transform_img_dict(
                dset, tdict=tdict, bgval=bgval, order=order, invert=invert
            )
        else:
            return transform_img_dict(dset, tdict=tdict)

    return mp_worker(
        registration_dft_worker,
        dset=target,
        _axis=tuple([x for x in range(target.ndim) if x != 1]),
        tdict=vector_dict,
        bgval=None,
        order=1,
        invert=False,
    )


def _projection_registration_fft(image_stack, channel):
    """
    image registration using a projection deformation model

    image_stack is 4D array

    """
    # // half z
    _z = image_stack.shape[2] // 2
    # // template is the middle image:
    # // new stack
    # tform = model.Affine()
    tform = model.Homography()
    registrator = register.Register()

    win = pg.GraphicsWindow(title="Overlay registration")
    win.resize(800, 800)
    p1 = win.addPlot()
    # Item for displaying image data
    imv = pg.ImageItem()
    p1.addItem(imv)
    win.show()
    pg.QtGui.QApplication.processEvents()

    # Coerce the image data into RegisterData.
    # out_stack[:,:,_z]
    for k in range(_z, 1, -1):
        image = image_stack[:, :, k - 1, channel]
        template = image_stack[:, :, k, channel]
        image_med = np.mean(image) * 5
        template_med = np.mean(template) * 5
        m = np.mean(np.array([image_med, template_med]))
        image = np.clip(np.squeeze(image), image.min(), m)
        template = np.clip(np.squeeze(template), template.min(), m)
        image = register.RegisterData(image)
        template = register.RegisterData(template)
        step, search = registrator.register(
            image, template, model.Shift(), sampler=sampler.bilinear
        )
        step, search = registrator.register(
            image, template, tform, sampler=sampler.bilinear
        )
        for c in range(image_stack.shape[3]):
            image_stack[:, :, k - 1, c, 0] = sampler.bilinear(
                image_stack[:, :, k - 1, c, 0], tform(step.p, template.coords).tensor
            )
            if c == channel:
                imv.setImage(image_stack[:, :, k + 1, c, 0] + template.data)
                win.setWindowTitle("slice {}".format(k))
                pg.QtGui.QApplication.processEvents()

    for k in range(_z, image_stack.shape[2] - 1, 1):
        image = image_stack[:, :, k + 1, channel]
        template = image_stack[:, :, k, channel]
        image_med = np.mean(image) * 5
        template_med = np.mean(template) * 5
        m = np.mean(np.array([image_med, template_med]))
        image = np.clip(np.squeeze(image), image.min(), m)
        template = np.clip(np.squeeze(template), template.min(), m)
        image = register.RegisterData(image)
        template = register.RegisterData(template)
        step, search = registrator.register(
            image, template, model.Shift(), sampler=sampler.bilinear
        )
        step, search = registrator.register(
            image,
            template,
            tform,
            sampler=sampler.bilinear,
            p=np.array([0, 0, 0, 0, 0, 0, step.p[0], step.p[1]]),
        )
        for c in range(image_stack.shape[3]):
            image_stack[:, :, k + 1, c, 0] = sampler.bilinear(
                image_stack[:, :, k + 1, c, 0], tform(step.p, template.coords).tensor
            )
            if c == channel:
                imv.setImage(image_stack[:, :, k + 1, c, 0] + template.data)
                win.setWindowTitle("slice {}".format(k))
                pg.QtGui.QApplication.processEvents()
    return image_stack


def rotatePoint(centerPoint, point, angle):
    """

    :param centerPoint:
    :param point:
    :param angle:
    :return:
    Rotates a point around another centerPoint. Angle is in degrees.

    Rotation is counter-clockwise
    """

    import math

    angle = math.radians(angle)
    temp_point = point[0] - centerPoint[0], point[1] - centerPoint[1]
    temp_point = (
        temp_point[0] * math.cos(angle) - temp_point[1] * math.sin(angle),
        temp_point[0] * math.sin(angle) + temp_point[1] * math.cos(angle),
    )
    temp_point = temp_point[0] + centerPoint[0], temp_point[1] + centerPoint[1]
    return temp_point


def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        # parallel lines
        return None
    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def rotate_multiple_points(p, origin=(0, 0), degrees=0):
    """
    points=[(200, 300), (100, 300)]
    origin=(100,100)

    new_points = rotate(points, origin=origin, degrees=10)
    print(new_points)
    """

    angle = np.deg2rad(degrees)
    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    o = np.atleast_2d(origin)
    p = np.atleast_2d(p)
    return np.squeeze((R @ (p.T - o.T) + o.T).T)


def unit_vector(vector):
    """Returns the unit vector of the vector."""
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    v2_countercross_wrt_v1 = (v1_u[0] * v2_u[1] - v1_u[1] * v2_u[0]) < 0
    if v2_countercross_wrt_v1:
        return np.rad2deg(np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)))
    else:
        return -np.rad2deg(np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)))
