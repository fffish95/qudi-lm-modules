# -*- coding: utf-8 -*-

from elecsus.elecsus_methods import calculate
import numpy as np


class Elecsus(object):
    def plotTheory(self, p_dict, detuning_range = np.linspace(-10,10,1000)*1e3, E_in = np.array([1,0,0]), outputs=['S0']):
        return calculate(detuning_range,E_in,p_dict,outputs)