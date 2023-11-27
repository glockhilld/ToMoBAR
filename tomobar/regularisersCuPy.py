#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Module to add regularisers from the CCPi-regularisation toolkit 
and initiate proximity operator for iterative methods

see installation for CuPy modules in
https://github.com/vais-ral/CCPi-Regularisation-Toolkit

GPLv3 license (ASTRA toolbox)
@author: Daniil Kazantsev: https://github.com/dkazanc
"""
import cupy as cp

try:
    from ccpi.filters.regularisersCuPy import ROF_TV as ROF_TV_cupy
    from ccpi.filters.regularisersCuPy import PD_TV as PD_TV_cupy
except ImportError:
    print(
        "____! CCPi-regularisation package (CuPy part needed only) is missing, please install !____"
    )


def prox_regul(self, X, _regularisation_):
    info_vec = (_regularisation_["iterations"], 0)
    # The proximal operator of the chosen regulariser
    if "ROF_TV" in _regularisation_["method"]:
        # Rudin - Osher - Fatemi Total variation method
        X_prox = ROF_TV_cupy(
            X,
            _regularisation_["regul_param"],
            _regularisation_["iterations"],
            _regularisation_["time_marching_step"],
            _regularisation_["tolerance"],
            self.GPUdevice_index,
        )
    if "PD_TV" in _regularisation_["method"]:
        # Primal-Dual (PD) Total variation method by Chambolle-Pock
        X_prox = PD_TV_cupy(
            X,
            _regularisation_["regul_param"],
            _regularisation_["iterations"],
            _regularisation_["tolerance"],
            cp.int(_regularisation_["methodTV"]),
            cp.int(self.nonneg_regul),
            cp.float32(_regularisation_["PD_LipschitzConstant"]),
            self.GPUdevice_index,
        )
    return X_prox
