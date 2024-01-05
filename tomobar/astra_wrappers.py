"""The series of classes for wrapping of ASTRA toolbox to perform projection/backprojection
and reconstruction of of 2D/3D parallel beam data.

GPLv3 license (defined by ASTRA toolbox)
"""
import numpy as np
from typing import Union
from tomobar.supp.funcs import _vec_geom_init2D, _vec_geom_init3D

try:
    import cupy as xp

    try:
        xp.cuda.Device(0).compute_capability
    except xp.cuda.runtime.CUDARuntimeError:
        import numpy as xp

        print("CuPy is installed but the GPU device is inaccessible")
except ImportError:
    import numpy as xp

    print("CuPy is not installed")

try:
    import astra
except ImportError:
    print("____! Astra-toolbox package is missing, please install !____")

###########Base class############
class AstraBase:
    """The base class for projection/backprojection and algorithms using ASTRA toolbox.

    Args:
        detectors_x (int): Horizontal detector dimension in pixel units.        
        angles_vec (np.ndarray): A vector of projection angles in radians.
        centre_of_rotation (float, np.ndarray): The Centre of Rotation (CoR) scalar or a vector of CoRs for each angle.
        recon_size (int): Reconstructed object size (a slice).
        processing_arch (str): 'cpu' or 'gpu' - based processing.
        device_index (int, optional): An integer for the GPU device, -1 for CPU computing and >0 for the GPU device.        
        ordsub_number (int): The number of ordered-subsets for iterative reconstruction.
        detectors_y (int): Vertical detector dimension in pixel units (3D case).        
    """
    def __init__(
        self,
        detectors_x,        
        angles_vec,
        centre_of_rotation,
        recon_size,
        processing_arch,
        device_index,
        ordsub_number,
        detectors_y,        
    ):
        self.detectors_x = detectors_x        
        self.angles_vec = angles_vec
        self.centre_of_rotation = centre_of_rotation
        self.recon_size = recon_size
        self.processing_arch = processing_arch
        self.device_index = device_index
        self.ordsub_number = ordsub_number
        self.detectors_y = detectors_y

    @property
    def detectors_x(self) -> int:
        return self._detectors_x

    @detectors_x.setter
    def detectors_x(self, detectors_x_val):
        if detectors_x_val <= 0:
            raise ValueError("The size of the horizontal detector cannot be negative or zero")
        self._detectors_x = detectors_x_val

    @property
    def angles_vec(self) -> np.ndarray:
        return self._angles_vec
    
    @angles_vec.setter
    def angles_vec(self, angles_vec_val):
        if len(angles_vec_val) == 0:
            raise ValueError("The length of angles array cannot be zero")
        if np.ndim(angles_vec_val) >= 2:
            raise ValueError("The array of angles must be 1D")
        self._angles_vec = angles_vec_val

    @property
    def centre_of_rotation(self) -> Union[float, np.ndarray]:
        return self._centre_of_rotation
    
    @centre_of_rotation.setter
    def centre_of_rotation(self, centre_of_rotation_val):
        if np.ndim(centre_of_rotation_val) == 1 and len(centre_of_rotation_val) != len(self.angles_vec):
            raise ValueError("The CoR must be a scalar or a 1D array of the SAME size as angles")
        if centre_of_rotation_val is None:
            centre_of_rotation_val = 0.0
        self._centre_of_rotation = centre_of_rotation_val

    @property
    def recon_size(self) -> int:
        return self._recon_size

    @recon_size.setter
    def recon_size(self, recon_size_val):
        if isinstance(recon_size_val, tuple):
            raise ValueError(
                        "Reconstruction is currently available for square or cubic objects only, please provide a scalar"
                    )
        if recon_size_val <= 0:
            raise ValueError("The size of the reconstruction object cannot be zero")
        self._recon_size = recon_size_val

    @property
    def processing_arch(self) -> str:
        return self._processing_arch

    @processing_arch.setter
    def processing_arch(self, processing_arch_val):
        if processing_arch_val != 'cpu' and processing_arch_val != 'gpu':
            raise ValueError("Please choose the processing architecture to be either 'cpu' or 'gpu'")
        self._processing_arch = processing_arch_val

    @property
    def device_index(self) -> int:
        return self._device_index

    @device_index.setter
    def device_index(self, device_index_val):
        if device_index_val <= -2:
            raise ValueError("The GPU device index can be only -1, 0 and larger than 0")
        if self.processing_arch == 'cpu':
            self._device_index = -1
        else:
            self._device_index = device_index_val

    @property
    def ordsub_number(self) -> int:
        return self._ordsub_number

    @ordsub_number.setter
    def ordsub_number(self, ordsub_number_val):
        if ordsub_number_val is None:
            ordsub_number_val = 1
        if ordsub_number_val <= 0:
            raise ValueError("The number of ordered subsets cannot be negative or zero")
        self._ordsub_number = ordsub_number_val

    @property
    def detectors_y(self) -> int:
        return self._detectors_y

    @detectors_y.setter
    def detectors_y(self, detectors_y_val):
        if detectors_y_val is not None:
            if detectors_y_val <= 0:
                raise ValueError("The size of the vertical detector cannot be negative or zero")
        self._detectors_y = detectors_y_val        

    def _setOS_indices(self):
        angles_tot = np.size(self.angles_vec)  # total number of angles
        self.NumbProjBins = (int)(
            np.ceil(float(angles_tot) / float(self.ordsub_number))
        )  # get the number of projections per bin (subset)
        self.newInd_Vec = np.zeros(
            [self.ordsub_number, self.NumbProjBins], dtype="int"
        )  # 2D array of OS-sorted indeces
        for sub_ind in range(self.ordsub_number):
            ind_sel = 0
            for proj_ind in range(self.NumbProjBins):
                indexS = ind_sel + sub_ind
                if indexS < angles_tot:
                    self.newInd_Vec[sub_ind, proj_ind] = indexS
                    ind_sel += self.ordsub_number

    def _set_vol2d_geometry(self):
        """set the reconstruction (vol_geom)
        """
        self.vol_geom = astra.create_vol_geom(self.recon_size, self.recon_size)

    def _set_vol3d_geometry(self):
        """set the reconstruction (vol_geom)
        """
        self.vol_geom = astra.create_vol_geom(self.recon_size, self.recon_size, self.recon_size)

    def _set_cpu_projection2d_parallel_geometry(self):
        """the classical 2D projection geometry (cpu)
        """
        # NOTE: Scalar geometry since parallel_vec is not implemented for CPU ASTRA modules yet?
        self.proj_geom = astra.create_proj_geom(
                "parallel", 1.0, self.detectors_x, self.angles_vec
        )
        self.proj_id = astra.create_projector(
                "line", self.proj_geom, self.vol_geom
        )  # for CPU
        # optomo operator is used for ADMM algorithm only
        self.A_optomo = astra.OpTomo(self.proj_id)

    def _set_gpu_projection3d_parallel_geometry(self):
        """the classical 3D projection geometry (cpu)
        """        
        vectors = _vec_geom_init3D(self.angles_vec, 1.0, 1.0, self.centre_of_rotation)
        self.proj_geom = astra.create_proj_geom(
            "parallel3d_vec", self.detectors_y, self.detectors_x, vectors
        )
        # optomo operator is used for ADMM algorithm only
        self.proj_id = astra.create_projector(
            "cuda3d", self.proj_geom, self.vol_geom
        )  # for GPU
        self.A_optomo = astra.OpTomo(self.proj_id)        

    def _set_gpu_projection2d_parallel_geometry(self):
        """the classical projection geometry (gpu)
        """
        vectors = _vec_geom_init2D(self.angles_vec, self.centre_of_rotation)
        self.proj_geom = astra.create_proj_geom(
            "parallel_vec", self.detectors_x, vectors
        )
        self.proj_id = astra.create_projector(
            "cuda", self.proj_geom, self.vol_geom
        )  # for GPU
        # optomo operator is used for ADMM algorithm only
        self.A_optomo = astra.OpTomo(self.proj_id)

    def _set_projection2d_OS_parallel_geometry(self):
        """organising 2d projection geometry CPU/GPU
        """
        self.proj_geom_OS = {}
        self.proj_id_OS = {}
        for sub_ind in range(self.ordsub_number):
            self.indVec = self.newInd_Vec[sub_ind, :]  # OS-specific indices
            if self.indVec[self.NumbProjBins - 1] == 0:
                self.indVec = self.indVec[:-1]  # shrink vector size
            anglesOS = self.angles_vec[self.indVec]  # OS-specific angles

            if np.ndim(self.centre_of_rotation) == 0:
                # centre_of_rotation is a _scalar_
                vectorsOS = _vec_geom_init2D(anglesOS, self.centre_of_rotation)
            else:
                # centre_of_rotation is a _vector_
                vectorsOS = _vec_geom_init2D(
                    anglesOS, self.centre_of_rotation[self.indVec]
                )
            self.proj_geom_OS[sub_ind] = astra.create_proj_geom(
                "parallel_vec", self.detectors_x, vectorsOS
            )
            if self.processing_arch == "cpu":
                self.proj_id_OS[sub_ind] = astra.create_projector(
                    "line", self.proj_geom_OS[sub_ind], self.vol_geom
                )  # for CPU
            else:
                self.proj_id_OS[sub_ind] = astra.create_projector(
                    "cuda", self.proj_geom_OS[sub_ind], self.vol_geom
                )  # for GPU


    def _runAstraBackproj2D(self, sinogram, method, iterations, os_index):
            """set ASTRA configuration for 2D classical/OS reconstructor
            """
            if self.ordsub_number != 1:
                # ordered-subsets
                sinogram_id = astra.data2d.create(
                    "-sino", self.proj_geom_OS[os_index], sinogram
                )
            else:
                # traditional geometry
                sinogram_id = astra.data2d.create("-sino", self.proj_geom, sinogram)

            # Create a data object for the reconstruction
            rec_id = astra.data2d.create("-vol", self.vol_geom)

            # Create algorithm object
            cfg = astra.astra_dict(method)
            if self.processing_arch == "cpu":
                if self.ordsub_number != 1:
                    cfg["ProjectorId"] = self.proj_id_OS[os_index]
                else:
                    cfg["ProjectorId"] = self.proj_id
            else:
                cfg["option"] = {"GPUindex": self.device_index}
            cfg["ReconstructionDataId"] = rec_id
            cfg["ProjectionDataId"] = sinogram_id
            if method == "FBP" or method == "FBP_CUDA":
                cfg["FilterType"] = "Ram-Lak"

            # Create the algorithm object from the configuration structure
            alg_id = astra.algorithm.create(cfg)
            astra.algorithm.run(alg_id, iterations)

            # Get the result
            recon_slice = astra.data2d.get(rec_id)

            astra.algorithm.delete(alg_id)
            astra.data2d.delete(rec_id)
            astra.data2d.delete(sinogram_id)
            if self.ordsub_number != 1:
                astra.data2d.delete(self.proj_id_OS)
            else:
                astra.data2d.delete(self.proj_id)
            return recon_slice
    
    def _runAstraProj2D(self, image, os_index, method):
        """set ASTRA configuration for 2D projector
        """
        if isinstance(image, np.ndarray):
            rec_id = astra.data2d.link("-vol", self.vol_geom, image)
        else:
            rec_id = image
        if self.ordsub_number != 1:
            # ordered-subsets
            sinogram_id = astra.data2d.create("-sino", self.proj_geom_OS[os_index], 0)
        else:
            # traditional full data parallel beam projection geometry
            sinogram_id = astra.data2d.create("-sino", self.proj_geom, 0)

        # Create algorithm object
        cfg = astra.astra_dict(method)
        if self.processing_arch == "cpu":
            if self.ordsub_number != 1:
                cfg["ProjectorId"] = self.proj_id_OS[os_index]
            else:
                cfg["ProjectorId"] = self.proj_id
        else:
            cfg["option"] = {"GPUindex": self.device_index}
        cfg["VolumeDataId"] = rec_id
        cfg["ProjectionDataId"] = sinogram_id

        # Create the algorithm object from the configuration structure
        alg_id = astra.algorithm.create(cfg)
        astra.algorithm.run(alg_id)

        # Get the result
        sinogram = astra.data2d.get(sinogram_id)

        astra.algorithm.delete(alg_id)
        astra.data2d.delete(rec_id)
        if self.ordsub_number != 1:
            astra.data2d.delete(self.proj_id_OS)
        else:
            astra.data2d.delete(self.proj_id)
        astra.data2d.delete(sinogram_id)
        return sinogram

    def runAstraBackproj3D(self, proj_data, method, iterations, os_index):
        # set ASTRA configuration for 3D reconstructor
        if self.ordsub_number != 1:
            # ordered-subsets
            proj_id = astra.data3d.create(
                "-sino", self.proj_geom_OS[os_index], proj_data
            )
        else:
            # traditional full data parallel beam projection geometry
            proj_id = astra.data3d.create("-sino", self.proj_geom, proj_data)

        # Create a data object for the reconstruction
        rec_id = astra.data3d.create("-vol", self.vol_geom)

        # Create algorithm object
        cfg = astra.astra_dict(method)
        cfg["option"] = {"GPUindex": self.device_index}
        cfg["ReconstructionDataId"] = rec_id
        cfg["ProjectionDataId"] = proj_id

        # Create the algorithm object from the configuration structure
        alg_id = astra.algorithm.create(cfg)
        astra.algorithm.run(alg_id, iterations)

        # Get the result
        recon_volume = astra.data3d.get(rec_id)

        astra.algorithm.delete(alg_id)
        astra.data3d.delete(rec_id)
        astra.data3d.delete(proj_id)
        return recon_volume

    def runAstraProj3D(self, volume_data, os_index):
        # set ASTRA configuration for 3D projector
        if isinstance(volume_data, np.ndarray):
            volume_id = astra.data3d.link("-vol", self.vol_geom, volume_data)
        else:
            volume_id = volume_data
        if self.ordsub_number != 1:
            # ordered-subsets
            proj_id = astra.data3d.create("-sino", self.proj_geom_OS[os_index], 0)
        else:
            # traditional full data parallel beam projection geometry
            proj_id = astra.data3d.create("-sino", self.proj_geom, 0)

        # Create algorithm object
        algString = "FP3D_CUDA"
        cfg = astra.astra_dict(algString)
        cfg["option"] = {"GPUindex": self.GPUdevice_index}
        cfg["VolumeDataId"] = volume_id
        cfg["ProjectionDataId"] = proj_id

        # Create the algorithm object from the configuration structure
        alg_id = astra.algorithm.create(cfg)
        astra.algorithm.run(alg_id)

        # Get the result
        proj_volume = astra.data3d.get(proj_id)

        astra.algorithm.delete(alg_id)
        astra.data3d.delete(volume_id)
        astra.data3d.delete(proj_id)
        return proj_volume      

###########Child class############
class AstraTools2D(AstraBase):
    """2D parallel beam projection/backprojection child class.

    Args:
        AstraBase (class): the inhereted base class.
    """    
    def __init__(
        self,
        detectors_x,
        angles_vec,
        centre_of_rotation,
        recon_size,
        processing_arch,
        device_index,
        ordsub_number=1,
        verbosity=False,
    ):
        super().__init__(
        detectors_x,        
        angles_vec,
        centre_of_rotation,
        recon_size,
        processing_arch,
        device_index,
        ordsub_number,
        detectors_y=None,
    )   
        super()._set_vol2d_geometry()
        if verbosity:
            print("2D volume geometry initialised...")        
        if ordsub_number == 1 or ordsub_number is None:
            if processing_arch == 'cpu':
                super()._set_cpu_projection2d_parallel_geometry()
            else:
                super()._set_gpu_projection2d_parallel_geometry()
            if verbosity:
                print("2D <{}> classical parallel-beam projection geometry initialised...".format(processing_arch))
        else:
            super()._setOS_indices()
            super()._set_projection2d_OS_parallel_geometry()
            if verbosity:
                print("2D <{}> ordered-subsets parallel-beam projection geometry initialised...".format(processing_arch))

    def _forwproj(self, image: np.ndarray) -> np.ndarray:
        astra_method = "FP_CUDA"  # 2d forward projection
        if self.processing_arch == "cpu":
            astra_method = "FP"
        return super()._runAstraProj2D(image, None, astra_method)

    def _forwprojOS(self, image: np.ndarray, os_index: int) -> np.ndarray:
        astra_method = "FP_CUDA"  # 2d forward projection
        if self.processing_arch == "cpu":
            astra_method = "FP"
        return super()._runAstraProj2D(image, os_index, astra_method)

    def _backproj(self, sinogram: np.ndarray) -> np.ndarray:
        astra_method = "BP_CUDA"  # 2D back projection
        if self.processing_arch == "cpu":
            astra_method = "BP"
        return super()._runAstraBackproj2D(sinogram, astra_method, 1, None)

    def backproj_OS(self, sinogram: np.ndarray, os_index: int) -> np.ndarray:
        astra_method = "BP_CUDA"  # 2D back projection
        if self.processing_arch == "cpu":
            astra_method = "BP"
        return super()._runAstraBackproj2D(sinogram, astra_method, 1, os_index)

    def _fbp(self, sinogram: np.ndarray) -> np.ndarray:
        astra_method = "FBP_CUDA"  # 2D FBP reconstruction
        if self.processing_arch == "cpu":
            astra_method = "FBP"
        return super()._runAstraBackproj2D(sinogram, astra_method, 1, None)

    def _sirt(self, sinogram: np.ndarray, iterations: int)-> np.ndarray:
        astra_method = "SIRT_CUDA"  # perform 2D SIRT reconstruction
        if self.processing_arch == "cpu":
            astra_method = "SIRT"
        return super()._runAstraBackproj2D(sinogram, astra_method, iterations, None)

    def _cgls(self, sinogram: np.ndarray, iterations: int) -> np.ndarray:
        astra_method = "CGLS_CUDA"  # perform 2D CGLS reconstruction
        if self.processing_arch == "cpu":
            astra_method = "CGLS"
        return super()._runAstraBackproj2D(sinogram, astra_method, iterations, None)


###########Child class############
class AstraTools3D(AstraBase):
    """3D parallel beam projection/backprojection child class.

    Args:
        AstraBase (class): the inhereted base class.
    """    
    def __init__(
        self,
        detectors_x,
        detectors_y,
        angles_vec,
        centre_of_rotation,
        recon_size,
        processing_arch,
        device_index,
        ordsub_number=1,
        verbosity=False,
    ):
        super().__init__(
        detectors_x,        
        angles_vec,
        centre_of_rotation,
        recon_size,
        processing_arch,
        device_index,
        ordsub_number,
        detectors_y,
    )   
        super()._set_vol3d_geometry()
        if verbosity:
            print("3D volume geometry initialised...")        
        if ordsub_number == 1 or ordsub_number is None:
            if processing_arch == 'cpu':
                raise ValueError("3D CPU reconstruction is not supported, please use GPU")
            else:
                super()._set_gpu_projection3d_parallel_geometry()
            if verbosity:
                print("3D <{}> classical parallel-beam projection geometry initialised...".format(processing_arch))
        else:
            super()._setOS_indices()
            super()._set_projection3d_OS_parallel_geometry()
            if verbosity:
                print("3D <{}> ordered-subsets parallel-beam projection geometry initialised...".format(processing_arch))

    def _forwproj(self, object3D: np.ndarray) -> np.ndarray:
        return super().runAstraProj3D(object3D, None)  # 3D forward projection

    # def _forwprojCuPy(self, object3D: xp.ndarray) -> xp.ndarray:
    #     return super().runAstraProj3DCuPy(object3D, None
    #     )  # 3D forward projection using CuPy array
    
    def _backproj(self, proj_data: np.ndarray) -> np.ndarray:
        return super().runAstraBackproj3D(proj_data, "BP3D_CUDA", 1, None
        )  # 3D backprojection

    # def _backprojCuPy(self, proj_data: xp.ndarray) -> xp.ndarray:
    #     return super().runAstraBackproj3DCuPy(
    #         self, proj_data, "BP3D_CUDA", None
    #     )  # 3D backprojection using CuPy array

    def _sirt(self, proj_data: np.ndarray, iterations: int) -> np.ndarray:
        return super().runAstraBackproj3D(proj_data, "SIRT3D_CUDA", iterations, None
        )  # 3D SIRT reconstruction

    def _cgls(self, proj_data: np.ndarray, iterations: int) -> np.ndarray:
        return super().runAstraBackproj3D(proj_data, "CGLS3D_CUDA", iterations, None
        )  # 3D CGLS reconstruction

