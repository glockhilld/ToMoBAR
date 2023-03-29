#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A reconstruction class for direct reconstructon methods.

-- Fourier Slice Theorem reconstruction (adopted from Tim Day's code)
-- Forward/Backward projection (ASTRA)
-- Filtered Back Projection (ASTRA)

@author: Daniil Kazantsev
"""

import numpy as np
from tomobar.supp.astraOP import AstraTools
from tomobar.supp.astraOP import AstraTools3D
from tomobar.supp.astraOP import parse_device_argument
import scipy.fftpack

def filtersinc3D(projection3D):
    # applies filters to __3D projection data__ in order to achieve FBP
    # Data format [DetectorVert, Projections, DetectorHoriz]
    # adopted from Matlabs code by  Waqas Akram
    #"a":	This parameter varies the filter magnitude response.
    #When "a" is very small (a<<1), the response approximates |w|
    #As "a" is increased, the filter response starts to
    #roll off at high frequencies.
    a = 1.1
    [DetectorsLengthV, projectionsNum, DetectorsLengthH] = np.shape(projection3D)
    w = np.linspace(-np.pi,np.pi-(2*np.pi)/DetectorsLengthH, DetectorsLengthH,dtype='float32')

    rn1 = np.abs(2.0/a*np.sin(a*w/2.0))
    rn2 = np.sin(a*w/2.0)
    rd = (a*w)/2.0
    rd_c = np.zeros([1,DetectorsLengthH])
    rd_c[0,:] = rd
    r = rn1*(np.dot(rn2, np.linalg.pinv(rd_c)))**2
    multiplier = (1.0/projectionsNum)
    f = scipy.fftpack.fftshift(r)
    # making a 2d filter for projection
    f_2d = np.zeros((DetectorsLengthV,DetectorsLengthH), dtype='float32')
    f_2d[0::,:] = f
    filtered = np.zeros(np.shape(projection3D), dtype='float32')

    for i in range(0,projectionsNum):
        IMG = scipy.fftpack.fft2(projection3D[:,i,:])
        fimg = IMG*f_2d
        filtered[:,i,:] = np.real(scipy.fftpack.ifft2(fimg))
    return multiplier*filtered

def filtersinc2D(sinogram):
    # applies filters to __2D projection data__ in order to achieve FBP
    a = 1.1
    [projectionsNum, DetectorsLengthH] = np.shape(sinogram)
    w = np.linspace(-np.pi,np.pi-(2*np.pi)/DetectorsLengthH, DetectorsLengthH,dtype='float32')

    rn1 = np.abs(2.0/a*np.sin(a*w/2.0))
    rn2 = np.sin(a*w/2.0)
    rd = (a*w)/2.0
    rd_c = np.zeros([1,DetectorsLengthH])
    rd_c[0,:] = rd
    r = rn1*(np.dot(rn2, np.linalg.pinv(rd_c)))**2
    multiplier = (1.0/projectionsNum)
    f = scipy.fftpack.fftshift(r)
    filtered = np.zeros(np.shape(sinogram))

    for i in range(0,projectionsNum):
        IMG = scipy.fftpack.fft(sinogram[i,:])
        fimg = IMG*f
        filtered[i,:] = multiplier*np.real(scipy.fftpack.ifft(fimg))
    return np.float32(filtered)

class RecToolsDIR:
    """ A class for reconstruction using DIRect methods (FBP and Fourier)"""
    def __init__(self,
              DetectorsDimH,    # DetectorsDimH # detector dimension (horizontal)
              DetectorsDimV,    # DetectorsDimV # detector dimension (vertical) for 3D case only
              CenterRotOffset,  # Centre of Rotation (CoR) scalar or a vector
              AnglesVec,        # Array of angles in radians
              ObjSize,          # A scalar to define reconstructed object dimensions
              device_projector  # Choose the device  to be 'cpu' or 'gpu' OR provide a GPU index (integer) of a specific device
              ):
        if isinstance(ObjSize,tuple):
            raise (" Reconstruction is currently available for square or cubic objects only, provide a scalar ")
        else:
            self.ObjSize = ObjSize # size of the object
        self.DetectorsDimH = DetectorsDimH
        self.DetectorsDimV = DetectorsDimV
        self.AnglesVec = AnglesVec
        if CenterRotOffset is not None:
            self.CenterRotOffset = CenterRotOffset
        else:
            self.CenterRotOffset = 0.0
        self.OS_number = 1
        self.device_projector, self.GPUdevice_index = parse_device_argument(device_projector)
        
        if DetectorsDimV is None:
            #2D geometry
            self.geom = '2D'
            self.Atools = AstraTools(self.DetectorsDimH, self.AnglesVec, self.CenterRotOffset, self.ObjSize, self.OS_number, self.device_projector, self.GPUdevice_index) # initiate 2D ASTRA class object            
        else:
            self.geom = '3D'            
            self.Atools = AstraTools3D(self.DetectorsDimH, self.DetectorsDimV, self.AnglesVec, self.CenterRotOffset, self.ObjSize, self.OS_number, self.device_projector, self.GPUdevice_index) # initiate 3D ASTRA class object            
    def FORWPROJ(self, 
                 data):
        """Module to perform forward projection of 2d/3d data array

        Args:
            data (ndarray): 2d or 3d array to project, either numpy or cupy
        Returns:
            ndarray: Forward projected array either numpy or cupy
        """
        # perform check here if the given array is numpy or not 
        # if not we assume that it is CuPy (loose assumption of course)
        if isinstance(data, np.ndarray):
            data_not_numpyarray = False
        else:
            data_not_numpyarray = True
        if (self.geom == '2D'):
            projdata = self.Atools.forwproj(data)
        if (self.geom == '3D'):
            if data_not_numpyarray:
                projdata = self.Atools.forwprojCuPy(data)
            else:
                projdata = self.Atools.forwproj(data)
        return projdata 
    def BACKPROJ(self, 
                 projdata):
        """Module to perform back-projection of 2d/3d data array

        Args:
            projdata (ndarray): 2d or 3d array to backproject, either numpy or cupy

        Returns:
            ndarray: backprojected array either numpy or cupy
        """
        # perform check here if the given array is numpy or not 
        # if not we assume that it is CuPy (loose assumption of course)
        if isinstance(projdata, np.ndarray):
            data_not_numpyarray = False
        else:
            data_not_numpyarray = True
        if (self.geom == '2D'):
            backproj = self.Atools.backproj(projdata)
        if (self.geom == '3D'):
            if data_not_numpyarray:
                backproj = self.Atools.backprojCuPy(projdata)
            else:
                backproj = self.Atools.backproj(projdata)
        return backproj
    def FOURIER(self, sinogram, method='linear'):
        """
        2D Reconstruction using Fourier slice theorem (scipy required)
        for griddata interpolation module choose nearest, linear or cubic
        """
        if sinogram.ndim == 3:
            raise ("Fourier method is currently for 2D data only, use FBP if 3D needed ")
        else:
            pass
        if ((method == 'linear') or (method == 'nearest') or (method == 'cubic')):
            pass
        else:
            raise ("For griddata interpolation module choose nearest, linear or cubic ")
        import scipy.interpolate
        import scipy.fftpack
        import scipy.misc
        import scipy.ndimage.interpolation

        # Fourier transform the rows of the sinogram, move the DC component to the row's centre
        sinogram_fft_rows=scipy.fftpack.fftshift(scipy.fftpack.fft(scipy.fftpack.ifftshift(sinogram,axes=1)),axes=1)

        """
        V  = 100
        plt.figure()
        plt.subplot(121)
        plt.title("Sinogram rows FFT (real)")
        plt.imshow(np.real(sinogram_fft_rows),vmin=-V,vmax=V)
        plt.subplot(122)
        plt.title("Sinogram rows FFT (imag)")
        plt.imshow(np.imag(sinogram_fft_rows),vmin=-V,vmax=V)
        """
        # Coordinates of sinogram FFT-ed rows' samples in 2D FFT space
        a = -self.AnglesVec
        r=np.arange(self.DetectorsDimH) - self.DetectorsDimH/2
        r,a=np.meshgrid(r,a)
        r=r.flatten()
        a=a.flatten()
        srcx=(self.DetectorsDimH /2)+r*np.cos(a)
        srcy=(self.DetectorsDimH /2)+r*np.sin(a)

        # Coordinates of regular grid in 2D FFT space
        dstx,dsty=np.meshgrid(np.arange(self.DetectorsDimH),np.arange(self.DetectorsDimH))
        dstx=dstx.flatten()
        dsty=dsty.flatten()

        """
        V = 100
        plt.figure()
        plt.title("Sinogram samples in 2D FFT (abs)")
        plt.scatter(srcx, srcy,c=np.absolute(sinogram_fft_rows.flatten()), marker='.', edgecolor='none', vmin=-V, vmax=V)
        """
        # Interpolate the 2D Fourier space grid from the transformed sinogram rows
        fft2=scipy.interpolate.griddata((srcy,srcx), sinogram_fft_rows.flatten(), (dsty,dstx), method, fill_value=0.0).reshape((self.DetectorsDimH,self.DetectorsDimH))
        """
        plt.figure()
        plt.suptitle("FFT2 space")
        plt.subplot(221)
        plt.title("Recon (real)")
        plt.imshow(np.real(fft2),vmin=-V,vmax=V)
        plt.subplot(222)
        plt.title("Recon (imag)")
        plt.imshow(np.imag(fft2),vmin=-V,vmax=V)
        """

        """
        # Show 2D FFT of target, just for comparison
        expected_fft2=scipy.fftpack.fftshift(scipy.fftpack.fft2(scipy.fftpack.ifftshift(phantom_2D)))

        plt.subplot(223)
        plt.title("Expected (real)")
        plt.imshow(np.real(expected_fft2),vmin=-V,vmax=V)
        plt.subplot(224)
        plt.title("Expected (imag)")
        plt.imshow(np.imag(expected_fft2),vmin=-V,vmax=V)
        """
        # Transform from 2D Fourier space back to a reconstruction of the target
        recon=np.real(scipy.fftpack.fftshift(scipy.fftpack.ifft2(scipy.fftpack.ifftshift(fft2))))

        # Cropping reconstruction to size of the original image
        image = recon[int(((self.DetectorsDimH-self.ObjSize)/2)+1):self.DetectorsDimH-int(((self.DetectorsDimH-self.ObjSize)/2)-1),int(((self.DetectorsDimH-self.ObjSize)/2)):self.DetectorsDimH-int(((self.DetectorsDimH-self.ObjSize)/2))]
        return image
    def FBP(self, sinogram):
        if (self.geom == '2D'):            
            'dealing with FBP 2D not working for parallel_vec geometry and CPU'
            if (self.device_projector == 'gpu'):
                FBP_rec = self.Atools.fbp2D(sinogram) # GPU reconstruction
            else:
                filtered_sino = filtersinc2D(sinogram) # filtering sinogram
                FBP_rec = self.Atools.backproj(filtered_sino) # backproject
        if (self.geom == '3D'):
            filtered_sino = filtersinc3D(sinogram) # filtering projection data
            FBP_rec = self.Atools.backproj(filtered_sino) # 3d backproject
        return FBP_rec
    