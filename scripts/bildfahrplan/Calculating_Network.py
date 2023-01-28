# -*- coding: utf-8 -*-
"""
Created on Tue Jan 24 13:22:36 2023

@author: Gut
"""

import copy
import csv
from datetime import datetime
import func_timeout
import glob
from IPython.display import Image
import itertools
import math
import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
from networkx.algorithms import *
from networkx.algorithms.flow import *
import numpy as np
import operator
import os
import pandas as pd
import pygraphviz as pgv
import random
import subprocess
import time
from deepdiff import DeepDiff

import createBildfahrplan_Gut

import gurobipy as gp
from gurobipy import *

#%% Define

a_up_fv = 
a_down_fr =
a_up_fr =
a_down_fr =
a_up_rb =
a_down_rb
a_up_gz = 
a_down_gz =

umwegfaktor =

t_stop =
t_change =

line_variants = ['Harburg_Celle_direct','Harburg_Soltau_Hbf','Soltau_Hbf_sued_kurz_Celle','Soltau_Hbf_sued_lang_Celle','Soltau_Hbf_Soltau-Harder']
dict_linevar = {}
for line_variant in line_variants:
    dict_linevar.update({
        line_variant: pd.read_csv(line_variant+'.csv', delimiter=';', header = 0, index_col = 0)
        })



