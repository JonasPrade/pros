# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 17:08:42 2023

@author: Gut
"""

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.ticker import AutoMinorLocator
import math
import os

from Bildfahrplan_functions import drawTimetableForTrack
from Bildfahrplan_functions import drawTimetableForSingleSection
from Bildfahrplan_functions import drawTimetableForMultiSections
from Bildfahrplan_functions import drawTimetableforTrain

#%% Join all csv-files


#%% Read csv-File
# Ich gehe davon aus, dass Sie ein entsprechendes DataFrame im Format der csv.Datei bereits erzeugt haben
df = pd.read_csv('20230126_1843_Timetable_Ham_Han.csv', sep = ';', header = 0)


#%% Define global Variables and Set Default values - Die angegebenen Werte sind nur beispielhaft und werden durch das umgebende Programm / die umgebende Schleife erzeugt

file_path = '20230126_1843_Timetable_Ham_Han.csv'
 
file_name = os.path.basename(file_path)
file = os.path.splitext(file_name)
Testname = file[0]

#Variables for Single Track
StartNode = 'DON'
EndNode = 'DKB'
TrackNumber = 1

#Variables for Single Section
StartNode = 'DON'
EndNode = 'DKB'

#Variables for Multi Sections
Nodes = ['nAH','nAHAR','nAMA','nYASET','nHHG','nHH']

#Variables for Train Ride dependent timetables
Train = 'N_33.a_SA-1'
Tracks = 'T'

Directions = 2 # 1 or 2
TimeHorizon = 'Z' # U - Untersuchungszeitraum, Z - Zeitraum vom ersten bis letzten Zug, (Zahl, Zahl) - selbstdefiniertes Zeitfenster

PrintTrainAnnotation = 'J' # J or N
PrintTimeAnnotation = 'J' # J or N
PrintLegend = 'J' # J or N


#Type of Timetable: 1 - Streckengleis, 2 - Streckenabschnitt, 3 - mehrere zusammenhängende Streckenabschnitte, 4 - Fahrtverlauf eines Zuges
timetable_choice = 3

if timetable_choice == 1:
    drawTimetableForTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
elif timetable_choice == 2:
    drawTimetableForSingleSection(Testname, df, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
elif timetable_choice == 3:
    drawTimetableForMultiSections(Testname, df, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
elif timetable_choice == 4:
    drawTimetableforTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
