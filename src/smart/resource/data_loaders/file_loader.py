# -*- coding: utf-8 -*-
import os

import numpy as np
import csv
import sys
import os
import glob

# // increase the field limit
maxInt = sys.maxsize
decrement = True

while decrement:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.
    decrement = False
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)
        decrement = True

def load_tiff(path_str, mode=0, mono=False, dgroup='', node='', progressbar='', pos=[0, 0]):
    '''
	Generic loader for tiff files into HDF5

	Parameters
	----------
	path_str: string
		path of file or folder containing file
	mode: int, optional
		dimensionality of the data
	DTYPE: string, optional
		Determines how the array is imported. 3 types are available: signal, voi, reference, and mask
	dgroup: hdf5 group, optional
		the parent in which the output will be stored (create a new datagroup if it does not exist)
	node: hdf5 node, optional
		the dataset in which the output will be stored
	progressbar: QProgressBar, optional
		allows to attach a progressbar which is kept up-to-date on the progressbar

	Returns
	-------
	None

	Notes
	-----
	Writes a new Dataset

	Examples
	--------

	'''
    from tifffile import TiffFile
    if mode == 1:
        tif = TiffFile(path_str)
        arr = tif.asarray()
        if len(arr.shape) == 4:
            w = arr.shape[3]
            h = arr.shape[2]

            if arr.shape[0] < 5:
                image = np.zeros((1, arr.shape[0], arr.shape[1], arr.shape[2], arr.shape[3]))
                image[0] = arr
            else:
                image = np.zeros((1, arr.shape[1], arr.shape[0], arr.shape[2], arr.shape[3]))
                image[0] = np.transpose(arr, (1, 0, 2, 3))

        elif len(arr.shape) == 3:
            if arr.shape[2] < 5:
                w = arr.shape[1]
                h = arr.shape[0]
                if mono:
                    image = np.zeros((1, 1, 1, arr.shape[0], arr.shape[1]))
                    image[0, 0, 0] = np.sum(arr, axis=2)
                else:
                    image = np.zeros((1, arr.shape[2], 1, arr.shape[0], arr.shape[1]))
                    image[0, :, 0] = np.transpose(arr, (2, 0, 1))
            else:
                w = arr.shape[2]
                h = arr.shape[1]
                if mono:
                    image = np.zeros((1, 1, 1, arr.shape[1], arr.shape[2]))
                    image[0, 0, 0] = np.sum(arr, axis=0)
                else:
                    image = np.zeros((1, arr.shape[0], 1, arr.shape[1], arr.shape[2]))
                    image[0, :, 0] = arr


        elif len(arr.shape) == 2:
            image = np.zeros((1, 1, 1, arr.shape[0], arr.shape[1]))
            image[0, 0, 0] = arr
            w = arr.shape[1]
            h = arr.shape[0]

        new_node = dgroup.file.add_node(name="imported images 1",
                                                   attrs={"NodeType": "MultiplexedSignalTrace",
                                                          "Parent": dgroup.file.name})

        dset_node = init_write(data=image, node_object=new_node, _defaultName=node, _defaultSuffix="",
                               dgroup="Microscope Image", node=node, overwrite=True)
        dset_node.parent.attrs['NodeType'] = 'MultiplexedImage'
        dset_node.attrs["Outline"] = [pos[0] - w / 2, w / 2 + pos[0], pos[1] - h / 2, h / 2 + pos[1], 0, 1]
        tif.close()
    elif mode == 2:
        from tifffile import TiffFile
        import cv2
        import time
        os.chdir(path_str)
        sourcelist = glob.glob("*.tif") + glob.glob("*.tiff")
        if not sourcelist:
            print('No tiff files found.')
            return None
        sourcelist = sort_nicely(sourcelist)
        dat_shape = TiffFile(sourcelist[0]).asarray().shape
        dset_node = init_write(_shape=(1, len(sourcelist), 1, dat_shape[0], dat_shape[1]), _defaultName='TIFF_',
                               dgroup=dgroup, node=node)
        if progressbar:
            progressbar.setValue(0)
        for n, f in enumerate(sourcelist):
            # tif = TiffFile(f)
            # dset_node[:,:,n] = tif.asarray()
            # tif.close()

            # im = Image.open(f)
            # dset_node[:,:,n] = np.array(im)
            dset_node[0, n, 0, :, :] = cv2.imread(f, -1)
            if progressbar:
                progressbar.setValue(n / len(sourcelist) * 100)
    current_group = dset_node.parent
    current_group.node.channel_dict.check_size(dset_node.shape[1])
    return dset_node.parent


def load_align_xml(xml_path):
    """

    :param xml_path:
    :return:
    """
    from lxml import etree as ET
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for i, child in enumerate(root):
        if "Alignment" in child.tag:
            attrs = {}
            tag_list = [c.tag for c in root[i]]
            if "Rotation" in tag_list:
                attrs['Rotation'] = np.float64(root[i].find("Rotation").text)
            else:
                attrs['Rotation'] = 0
            if "Center" in tag_list:
                attrs['Center'] = np.array([np.float64(k) for k in root[i].find("Center").text.split(',')],
                                           dtype=np.float64)
            else:
                attrs['Center'] = [np.array([50000, 50000])]
            if "Size" in tag_list:
                attrs['Size'] = np.array([np.float64(k) for k in root[i].find("Size").text.split(',')])
            else:
                attrs['Size'] = [np.array([0, 0])]
            if "Focus" in tag_list:
                attrs['Focus'] = np.float64(root[i].find("Focus").text)
            else:
                attrs['Focus'] = 0
            return attrs

def load_im_xml(xml_path, exclude_file, progressbar=''):
    """

    :param xml_path:
    :param exclude_file:
    :param progressbar:
    :return:
    """
    path = os.path.split(xml_path)[0]
    from lxml import etree as ET
    tree = ET.parse(xml_path)
    root = tree.getroot()
    attr_list = []
    v = len(root.findall(".//Center"))
    for i, child in enumerate(root):
        if 'Image' in child.tag:
            if root[i].find("Filename") is not None:
                if os.path.join(path, root[i].find("Filename").text) not in exclude_file:
                    attrs = {'Path': os.path.join(path, root[i].find("Filename").text),
                             'Name': root[i].find("Filename").text}
                    # // build the tag list
                    tag_list = [c.tag for c in root[i]]
                    if "Opacity" in tag_list:
                        attrs['Opacity'] = int(root[i].find("Opacity").text)
                    else:
                        attrs['Opacity'] = 100
                    if "Visible" in tag_list:
                        if 'TRUE' in root[i].find("Visible").text:
                            attrs["Visible"] = True
                        else:
                            attrs["Visible"] = False
                    else:
                        attrs["Visible"] = True
                    if "Rotation" in tag_list:
                        attrs['Rotation'] = np.float64(root[i].find("Rotation").text)
                    else:
                        attrs['Rotation'] = 0
                    if "Center" in tag_list:
                        attrs['Center'] = np.array([np.float64(k) for k in root[i].find("Center").text.split(',')],
                                                   dtype=np.float64)
                    else:
                        attrs["Center"] = [np.array([50000, 50000])]
                    if "Size" in tag_list:
                        attrs['Size'] = np.array([np.float64(k) for k in root[i].find("Size").text.split(',')])
                    else:
                        attrs["Size"] = [np.array([0, 0])]
                    if "Focus" in tag_list:
                        attrs['Focus'] = np.float64(root[i].find("Focus").text)
                    else:
                        attrs['Focus'] = 0

                    if "BaseFolder" in tag_list:
                        attrs['BaseFolder'] = root[i].find("BaseFolder").text
                        attrs['Path'] = os.path.join(attrs['BaseFolder'], root[i].find("Filename").text)
                    if 'Particle' in tag_list:
                        for jj, child_par in enumerate(root[i].find('Particle')):
                            attrs[child_par.tag] = child_par.text
                    if 'StageCoords_TL' in tag_list:
                        attrs['StageCoords_TL'] = root[i].find("StageCoords_TL").text
                    c = attrs['Center']
                    s = attrs['Size']
                    #z is not used
                    z = attrs['Focus']
                    outline = [(c[0] - s[0] / 2.0), (c[0] + s[0] / 2.0), (c[1] - s[1] / 2.0), (c[1] + s[1] / 2.0), -0.5, 0.5]
                    attrs['Outline'] = outline
                    attrs['Parent'] = ""
                    attrs['NodeType'] = 'RGBA'
                    attr_list.append(attrs)
        elif 'Data' in child.tag:
            for j in root[i]:
                if j.tag == "BaseFolder":
                    for k in attr_list:
                        k["BaseFolder"] = root[i][1].text
                        p = os.path.join(k['BaseFolder'], k["Name"])
                    # if os.path.exists(p):
                    #     k['Path'] = p

        if progressbar:
            try:
                progressbar.setValue(i / v * 100)
            except:
                pass
    return attr_list

def load_im(filename, library=None):
    """
	Loads the file given by filename and calls appropriate load or open function
	based on the file extension.  Currently supported: .png, .jpg, .cvs, .mat, .dat, .txt, .sav, .arff, .mtx, .mtz.gz, .gif, .tiff, .bmp, .wav, .npy, .npz and
	those supported by load().

	For some file type, this function returns some value:
		- .cvs : a list of rows in the cvs
		- .png/.jpg: a numpy.ndarray of the image using pyplot
					 a PIL image type when using PIL
		- .txt: a list of lines in the file
		- .mat: dictionary with variable names as keys, and loaded matrices as values
				 as returned by scipy's loadmat()
		- .arff: a tuple of array of records and metadata
		- .wav: an int representing the sample rate and
				a numpy array of the sound file
		- .gif, .bit, .tiff: a PIL image object
		- .mtx, .mtz.gz: a matrix described by the file
		- .sav: dictionary object of the IDL save file
		- .f: executes the Fortran file, no return values
		- .dat: a list of lines in the dat file. Each line is further parsed into a list of
				number in each line

   Parameters
	----------

	filename: string
		path to the file to be loaded
	lib: string
		which library use to load file if there are more than one choice
				  - jpg/png: PIL or matplotlib.pyplot
	attach: string
		to attach the file given by URL or not
	Returns
	-------
	out: numpy ndarray

	Notes
	-----
	none

	Examples
	--------

	"""

    supported_types = (
        '.py', '.pyx', '.sage', '.spyx', '.m', '.png', '.jpg', '.cvs', '.mat', '.dat', '.txt', '.sav', '.arff', '.mtx',
        '.mtz.gz', '.gif', '.tiff', '.tif', '.bmp', '.wav', '.npy', '.npz')
    if (not filename.endswith(supported_types)):
        raise ValueError('argument (=%r) to load or attach must have extension %s' % (filename, supported_types))

    filename = filename.strip()
    if (filename.endswith('.csv')):
        import csv
        f = open(filename, 'rU')
        l = []
        try:
            reader = csv.reader(f)
            for row in reader:
                l.append(row)
        finally:
            f.close()
        return l
    elif (filename.endswith('.dat')):
        return np.loadtxt(filename)
    elif (filename.endswith('.mat')):
        from scipy import io
        return io.loadmat(filename)
    elif (filename.endswith('.f')):
        globals()['fortran'](filename)
    elif (filename.endswith('.txt')):
        myfile = open(filename, 'r')
        lines = myfile.readlines()
        return lines
    elif (filename.endswith('.sav')):
        from scipy import io
        dictR = dict()
        io.readsav(filename, dictR, True)
        return dictR
    elif (filename.endswith('.arff')):
        from scipy.io import arff
        return arff.loadarff(filename)
    elif (filename.endswith(('.mtx', '.mtz.gz'))):
        from scipy import io
        return io.mmread(filename)
    elif (filename.endswith(('.bmp', '.png', '.jpg'))):
        from PySide import QtGui
        img = QtGui.QPixmap(filename).toImage()
        assert img.format() == QtGui.QImage.Format.Format_RGB32, \
            "img format must be QImage.Format.Format_RGB32, got: {}".format(img.format())
        img_size = img.size()
        buffer = img.constBits()

        # Sanity check
        n_bits_buffer = len(buffer) * 8
        n_bits_image = img_size.width() * img_size.height() * img.depth()
        assert n_bits_buffer == n_bits_image, \
            "size mismatch: {} != {}".format(n_bits_buffer, n_bits_image)

        assert img.depth() == 32, "unexpected image depth: {}".format(img.depth())

        # Note the different width height parameter order!
        arr = np.ndarray(shape=(img_size.height(), img_size.width(), img.depth() // 8),
                         buffer=buffer,
                         dtype=np.uint8)
        # print(arr.shape)
        arr_corr = np.roll(arr[:, :, :3], axis=2, shift=2)
        # arr_corr = np.dstack((arr_corr,arr[:,:,3]))
        return arr_corr
    elif (filename.endswith(('.tiff', '.tif'))):
        from tifffile import TiffFile
        tif = TiffFile(filename)
        return tif.asarray()
    elif (filename.endswith('.wav')):
        from scipy.io import wavfile
        return wavfile.read(filename)
    elif (filename.endswith(('.npz', '.npy'))):
        return np.load(filename)
    else:
        return 'Could not load image'



