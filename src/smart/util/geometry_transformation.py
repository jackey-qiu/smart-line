# -*- coding: utf-8 -*-
import os


import numpy as np
from scipy import ndimage
from PyQt5 import QtCore
import pyqtgraph as pg


def registration_dft_stack(dset, z_axis=(2,),channel=(0,), channel_axis=(3,), scale=[1,0], angle=[0,0], tx=[0,0], ty=[0,0], \
	iterations=100, display=True, quiet=False, simulation=False, progressbar='', display_window=''):
	'''
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

	'''
	# select the middle slice as a reference
	rank=len(dset.shape)
	if isinstance(z_axis, tuple):
		z_axis=z_axis[0]
	if not isinstance(channel_axis, tuple):
		channel_axis=(channel_axis)
		
	_z = dset.shape[z_axis]//2
	if not quiet:
		QtCore.qDebug('Reference slice {} selected'.format(_z))
	
	if display:
		if not display_window:
			win = pg.GraphicsWindow(title="Overlay registration")
			win.resize(800,800)
			p1 = win.addPlot()
			# Item for displaying image data
			imv = pg.ImageItem()
			p1.addItem(imv)
			win.show()
			pg.QtGui.QApplication.processEvents()
			display_window=imv

	for k in range(_z,0,-1):
		# // get channels summed
		reg_slice=[slice(None)]*rank
		ref_slice=[slice(None)]*rank
		ref_slice[z_axis]=k
		reg_slice[z_axis]=k-1
		if z_axis>channel_axis[0]:
			channel_axis_alt = channel_axis
		else:
			channel_axis_alt = channel_axis-1
		dset[reg_slice] = registration_dft_slice(im0=dset[ref_slice],im1=dset[reg_slice],channel=(0,), channel_axis=channel_axis_alt, scale=scale, angle=angle, tx=tx, ty=ty, \
	iterations=iterations, display=display, quiet=quiet, simulation=simulation, progressbar='', display_window=display_window)
		if progressbar:
			progressbar.setValue(_z-k/z_axis*100)

	for k in range(_z,dset.shape[z_axis]-1,1):

		if progressbar:
			progressbar.setValue(k/z_axis*100)
	if progressbar:
			progressbar.setValue(100)
	return dset


def transform_img_dict(dset, tdict, invertx=False, inverty=False):
	"""
	reimplementation of transformation operation based on a dictionary of translation/scale/rotation vectors. Also enables invert

	image is 2D
	"""
	if not tdict:
		raise ValueError('Error, no vector translation/scale/rotation dictionary found')
	if inverty:
		dset=np.flipud(dset)
	if invertx:
		dset=np.fliplr(dset)
	if 'angle' in tdict:
		dset=ndimage.rotate(dset,tdict['angle'],reshape=False)
	if 'tvec' in tdict:
		dset = np.roll(dset,shift=int(tdict['tvec'][0]),axis=0)
	if 'tvec' in tdict:
		dset = np.roll(dset,shift=int(tdict['tvec'][1]),axis=1)
	return dset


def registration_dft_slice(im0, im1, scale=[1,0], angle=[0,0], tx=[0,0], ty=[0,0], \
	iterations=100, display=True, progressbar='', display_window=''):
	'''
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
	'''
	import imreg_dft as ird
	from sklearn.preprocessing import normalize
	# // normalize images to be registred
	rank=len(im1.shape)
	if display:
		if not display_window:
			win = pg.GraphicsWindow(title="Overlay registration")
			win.resize(800,800)
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
	vector_dict = ird.similarity(im0_r, im1_r, numiter=int(iterations))
	# // apply transformation to each channel
	if display:
		im2_r = ird.imreg.transform_img_dict(im1_r, tdict=vector_dict, bgval=None, order=1, invert=False)
		if not display_window:
			imv.setImage(im2_r+im0_r)
			# win.setWindowTitle('Reference slice {}; Target slice {}'.format(k,k-1))
			pg.QtGui.QApplication.processEvents()
			pg.QtGui.QApplication.processEvents()
		else:
			display_window.setImage(im2_r+im0_r)
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
	def registration_dft_worker(dset, _axis=(0, 1), tdict=vector_dict, bgval=None, order=1, invert=False, fast=False):
		# // fast transform compresses the result
		if fast:
			return ird.imreg.transform_img_dict(dset, tdict=tdict, bgval=bgval, order=order, invert=invert)
		else:
			return transform_img_dict(dset, tdict=tdict)

	return mp_worker(registration_dft_worker, dset=target, _axis=tuple([x for x in range(target.ndim) if x != 1]),
						 tdict=vector_dict, bgval=None, order=1, invert=False)


# // test image
# from skimage import data
# from skimage import img_as_float
# a = img_as_float(data.astronaut()[::2, ::2])
# a=np.reshape(np.repeat(a[:,:],20),(256,256,3,20))
# for k in range(20):
# 	a[:,:,:,k]=ndimage.rotate(a[:,:,:,k],20*k, reshape=False)
# a= registration_dft_stack(a, iterations=15, display=True, quiet=False,simulation=False,z_axis=(3,),channel=(0,), channel_axis=(2,),angle=[10,30], tx=[0,0], ty=[0,0])

# registration_dft_slice(a[:,:,:,0], a[:,:,:,1], channel=(0,), channel_axis=(2,), scale=[1,0], angle=[0,0], tx=[0,0], ty=[0,0], \
# 	iterations=3, display=True, quiet=False, simulation=False, progressbar='', display_window='', vector_dict_out=False)


# def _projection_registration_cv2(image_stack, channel, warp_mode = cv2.MOTION_EUCLIDEAN):
# 	"""
# 	image registration using a projection deformation model

# 	image_stack is 4D array

# 	"""

# 	_z = image_stack.shape[2]//2


# 	win = pg.GraphicsWindow(title="Overlay registration")
# 	win.resize(800,800)
# 	p1 = win.addPlot()
# 	# Item for displaying image data
# 	imv = pg.ImageItem()
# 	p1.addItem(imv)
# 	win.show()
# 	pg.QtGui.QApplication.processEvents()

# 	for k in range(_z,1,-1):
# 		# im1=np.squeeze(image_stack[:,:,k, channel])
# 		# im2=np.squeeze(image_stack[:,:,k+1, channel])
# 		# im1_gray =np.uint8(np.round((im1-im1.min())*65535/(im1.max()-im1.min())))
# 		# im2_gray = np.uint8(np.round((im2-im2.min())*65535/(im2.max()-im2.min())))

# 		# im1 =  cv2.imread("/run/media/admin/Storage4/Data_Backup_Containers/Data_Container_Live/Unprocessed/Grains/3D/stack/level_Mn55/level_Mn55{:04d}.jpg".format(k+1));
# 		# im2 =  cv2.imread("/run/media/admin/Storage4/Data_Backup_Containers/Data_Container_Live/Unprocessed/Grains/3D/stack/level_Mn55/level_Mn55{:04d}.jpg".format(k)); 
# 		im1 = np.float32(image_stack[:,:,k,channel,0])
# 		# im1_gray = cv2.cvtColor(im1,cv2.COLOR_GRAY2BGR)
# 		# im1_gray = cv2.cvtColor(im1_gray,cv2.COLOR_BGR2GRAY)
# 		im_tot=im1
# 		im1_gray=im1
# 		im2 = np.float32(image_stack[:,:,k-1,channel,0])
# 		# im2_gray = cv2.cvtColor(im2,cv2.COLOR_GRAY2BGR)
# 		# im2_gray = cv2.cvtColor(im2_gray,cv2.COLOR_BGR2GRAY)	
# 		im2_gray = im2
# 		sz = im1_gray.shape
		 
# 		# Define 2x3 or 3x3 matrices and initialize the matrix to identity
# 		if warp_mode == cv2.MOTION_HOMOGRAPHY :
# 		    warp_matrix = np.eye(3, 3, dtype=np.float32)
# 		else :
# 		    warp_matrix = np.eye(2, 3, dtype=np.float32)
		 
# 		# Specify the number of iterations.
# 		number_of_iterations = 1000;
		 
# 		# Specify the threshold of the increment
# 		# in the correlation coefficient between two iterations
# 		termination_eps = 1e-5;
		 
# 		# Define termination criteria
# 		criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations,  termination_eps)
		 
# 		# Run the ECC algorithm. The results are stored in warp_matrix.
# 		(cc, warp_matrix) = cv2.findTransformECC (im1_gray,im2_gray,warp_matrix, warp_mode, criteria)
		
# 		# for c in range(image_stack.shape[3]):
# 		if warp_mode == cv2.MOTION_HOMOGRAPHY :
# 		    # Use warpPerspective for Homography 
# 		    im2_aligned = cv2.warpPerspective (im2_gray, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
# 		else :
# 		    # Use warpAffine for Translation, Euclidean and Affine
# 		    im2_aligned = cv2.warpAffine(im2_gray, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP);
		
# 		im_tot+=im2_aligned
# 		im1=im2_aligned
# 		# # Show final results
# 		plt.imshow( im_tot)
# 		# plt.waitKey(0)
# 		# plt.show()

# 	for k in range(_z,image_stack.shape[2]-1,1):
# 		# im1=np.squeeze(image_stack[:,:,k, channel])
# 		# im2=np.squeeze(image_stack[:,:,k+1, channel])
# 		# im1_gray =np.uint8(np.round((im1-im1.min())*65535/(im1.max()-im1.min())))
# 		# im2_gray = np.uint8(np.round((im2-im2.min())*65535/(im2.max()-im2.min())))
		
# 		im1 = np.float32(image_stack[:,:,k,channel,0])
# 		im1_gray = cv2.cvtColor(im1,cv2.COLOR_GRAY2BGR)
# 		im1_gray = cv2.cvtColor(im1_gray,cv2.COLOR_BGR2GRAY)
# 		# im_tot=im1_gray
# 		im2 = np.float32(image_stack[:,:,k+1,channel,0])
# 		im2_gray = cv2.cvtColor(im2,cv2.COLOR_GRAY2BGR)
# 		im2_gray = cv2.cvtColor(im2_gray,cv2.COLOR_BGR2GRAY)
# 		sz = im1_gray.shape

		 
# 		# Define 2x3 or 3x3 matrices and initialize the matrix to identity
# 		if warp_mode == cv2.MOTION_HOMOGRAPHY :
# 		    warp_matrix = np.eye(3, 3, dtype=np.float32)
# 		else :
# 		    warp_matrix = np.eye(2, 3, dtype=np.float32)
		 
# 		# Specify the number of iterations.
# 		number_of_iterations = 1000;
		 
# 		# Specify the threshold of the increment
# 		# in the correlation coefficient between two iterations
# 		termination_eps = 1e-5;
		 
# 		# Define termination criteria


# 		criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations,  termination_eps)
		 
# 		# Run the ECC algorithm. The results are stored in warp_matrix.
# 		(cc, warp_matrix) = cv2.findTransformECC (im1_gray,im2_gray,warp_matrix, warp_mode, criteria)
		
# 		# for c in range(image_stack.shape[3]):
# 		if warp_mode == cv2.MOTION_HOMOGRAPHY :
# 		    # Use warpPerspective for Homography 
# 		    im2_aligned = cv2.warpPerspective (im2_gray, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
# 		else :
# 		    # Use warpAffine for Translation, Euclidean and Affine
# 		    im2_aligned = cv2.warpAffine(im2_gray, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP);

# 		# Show final results
# 		# cv2.imshow("Image 1", im1_gray)
# 		# cv2.imshow("Image 2", im2_gray)
# 		# cv2.imshow("im2_aligned", im2_aligned)
# 		# cv2.waitKey(0)
# 		im_tot+=im2_aligned

# 	# plt.imshow(np.mean(np.squeeze(im_tot[:,:,:])),axis=2)
# 	# plt.show()


# 		# imv.setImage(im1+im2_aligned)
# 		# win.setWindowTitle('slice {}'.format(k))
# 		# pg.QtGui.QApplication.processEvents()

# 	return im_tot



def _projection_registration_fft(image_stack, channel):
	"""
	image registration using a projection deformation model

	image_stack is 4D array

	"""
	# // half z
	_z = image_stack.shape[2]//2
	# // template is the middle image:
	# // new stack
	# tform = model.Affine()
	tform=model.Homography()
	registrator = register.Register()

	win = pg.GraphicsWindow(title="Overlay registration")
	win.resize(800,800)
	p1 = win.addPlot()
	# Item for displaying image data
	imv = pg.ImageItem()
	p1.addItem(imv)
	win.show()
	pg.QtGui.QApplication.processEvents()

	# Coerce the image data into RegisterData.
	# out_stack[:,:,_z]
	for k in range(_z,1,-1):
		image= image_stack[:,:,k-1, channel]
		template = image_stack[:,:,k, channel]
		image_med = np.mean(image)*5
		template_med = np.mean(template)*5
		m = np.mean(np.array([image_med,template_med]))
		image=np.clip(np.squeeze(image), image.min(),m)
		template=np.clip(np.squeeze(template), template.min(),m)
		image = register.RegisterData(image)
		template = register.RegisterData(template)
		step, search = registrator.register(image, template, model.Shift(), sampler=sampler.bilinear)
		step, search = registrator.register(image, template, tform, sampler=sampler.bilinear)
		for c in range(image_stack.shape[3]):
			image_stack[:,:,k-1,c,0] = sampler.bilinear(image_stack[:,:,k-1, c,0], tform(step.p, template.coords).tensor)
			if c==channel:
				imv.setImage(image_stack[:,:,k+1,c,0]+template.data)
				win.setWindowTitle('slice {}'.format(k))
				pg.QtGui.QApplication.processEvents()

	for k in range(_z,image_stack.shape[2]-1,1):
		image= image_stack[:,:,k+1, channel]
		template = image_stack[:,:,k, channel]
		image_med = np.mean(image)*5
		template_med = np.mean(template)*5
		m = np.mean(np.array([image_med,template_med]))
		image=np.clip(np.squeeze(image), image.min(),m)
		template=np.clip(np.squeeze(template), template.min(),m)
		image = register.RegisterData(image)
		template = register.RegisterData(template)
		step, search = registrator.register(image, template, model.Shift(), sampler=sampler.bilinear)
		step, search = registrator.register(image, template, tform, sampler=sampler.bilinear,p = np.array([0,0,0,0,0,0,step.p[0],step.p[1]]))
		for c in range(image_stack.shape[3]):
			image_stack[:,:,k+1,c,0] = sampler.bilinear(image_stack[:,:,k+1, c,0], tform(step.p, template.coords).tensor)
			if c==channel:
				imv.setImage(image_stack[:,:,k+1,c,0]+template.data)
				win.setWindowTitle('slice {}'.format(k))
				pg.QtGui.QApplication.processEvents()
	return image_stack


def rotatePoint(centerPoint,point,angle):
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
	temp_point = point[0]-centerPoint[0] , point[1]-centerPoint[1]
	temp_point = ( temp_point[0]*math.cos(angle)-temp_point[1]*math.sin(angle) , temp_point[0]*math.sin(angle)+temp_point[1]*math.cos(angle))
	temp_point = temp_point[0]+centerPoint[0] , temp_point[1]+centerPoint[1]
	return temp_point