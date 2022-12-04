# -*- coding: utf-8 -*-

from elecsus.elecsus_methods import calculate
import numpy as np


class Elecsus(object):

    def plotTheory(detuning_range, E_in, p_dict, outputs=['S0']):
        return calculate(detuning_range,E_in,p_dict,outputs)