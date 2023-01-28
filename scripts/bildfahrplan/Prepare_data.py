# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 17:32:03 2023

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
from datetime import datetime

#df_timetable_origin = pd.read_csv('Dateien_Ham_Han/FV8_1.csv', sep = ',', header = 0)

#%% Define a function to convert the timetable data and cut it to the relevant data

#def convert_timetable_data(train_line, file_path, line_endpoints):
#    df_timetable_origin = pd.read_csv('Dateien_Ham_Han/FV8_1.csv', sep = ',', header = 0)
    
    

#%% Call function to convert the timetable data

#Define empty variables
df_timetable_all_trains_arc_based_lst = []
df_timetable_all_trainlines_arc_based_lst = []
time_span_lst = []
trainline_counter = 0

# Define input
input_path = 'Dateien_Ham_Han/'
train_lines = ('FV8_1','FV8_2')
line_endpoints = ('Hamburg Hbf', 'Hannover Hbf')
outputpath = os.path.join('C:\\','Users','Gut','Documents','Gastel_Praktikum','Programme')
now = datetime.now()
dt_string = now.strftime("%Y%m%d_%H%M")
filename_csv = outputpath+'\\'+dt_string+'_'+'Timetable_Ham_Han'+'.csv'

for train_line in train_lines:
    df_timetable_trainline_arc_based_lst = []
    
    file_path = input_path + train_line + '.csv'
    #convert_timetable_data(train_line, file_path, line_endpoints) - call the function
    df_timetable_origin = pd.read_csv(file_path, sep = ',', header = None)
    df_timetable_origin.columns = ['Train', 'shortcut', 'station', 'arrival', 'departure', 'ridenumber']
    #check whether the train runs from endpoint A to endpoint B or reverse
    #get first line with endpoint A
    rownumber_Endpoint_A = df_timetable_origin[df_timetable_origin['station'] == line_endpoints[0]].index[0]
    #get first line with endpoint B
    rownumber_Endpoint_B = df_timetable_origin[df_timetable_origin['station'] == line_endpoints[1]].index[0]
    #cut all before first endpoint and after second endpoint
    if rownumber_Endpoint_A < rownumber_Endpoint_B:
        df_timetable_origin = df_timetable_origin.loc[rownumber_Endpoint_A:rownumber_Endpoint_B]
    else:
        df_timetable_origin = df_timetable_origin.loc[rownumber_Endpoint_B:rownumber_Endpoint_A]
    #complete arrivaltimes
    for timetable_origin_index in df_timetable_origin.index:
        if pd.isnull(df_timetable_origin.loc[timetable_origin_index, 'arrival']):
            df_timetable_origin.loc[timetable_origin_index, 'arrival'] = df_timetable_origin.loc[timetable_origin_index, 'departure']
    #reset index
    df_timetable_origin.reset_index(drop = True, inplace = True)
    #calculate new nodes along the ride with all times and insert it - later new function
    
    
    #convert timetable data from node-based format to arc-based format - later seperate function
    for timetable_origin_index in range(len(df_timetable_origin.index)-1):
        timetable_origin_index_next = timetable_origin_index + 1
        arc_lst = []
        departure_arrival_lst = []
        arc_lst.append(df_timetable_origin.loc[timetable_origin_index, 'Train'])
        if 'FV' in train_line:
            arc_lst.append('FV')        
        elif 'FR' in train_line:
            arc_lst.append('FR')
        elif 'RB' in train_line:
            arc_lst.append('RB')        
        elif 'GZ' in train_line:
            arc_lst.append('GZ')
        else:
            arc_lst.append('unknown')
        arc_lst.append(df_timetable_origin.loc[timetable_origin_index, 'shortcut'])        
        arc_lst.append(df_timetable_origin.loc[timetable_origin_index_next, 'shortcut'])
        #change time_format
        departure_lst = df_timetable_origin.loc[timetable_origin_index, 'departure'].split(':')
        departure_time_in_minutes = round(float(departure_lst[0])*60 + float(departure_lst[1]) + float(departure_lst[2])/60, 3)
        arc_lst.append(departure_time_in_minutes)
        arrival_lst = df_timetable_origin.loc[timetable_origin_index_next, 'arrival'].split(':')
        arrival_time_in_minutes = round(float(arrival_lst[0])*60 + float(arrival_lst[1]) + float(arrival_lst[2])/60, 3)
        arc_lst.append(arrival_time_in_minutes)
        #define alphabetical ordered arcs
        if df_timetable_origin.loc[timetable_origin_index, 'Train'] < df_timetable_origin.loc[timetable_origin_index, 'Train']:
            arc_lst.append(df_timetable_origin.loc[timetable_origin_index, 'shortcut'])
            arc_lst.append(df_timetable_origin.loc[timetable_origin_index_next, 'shortcut'])
        else:
            arc_lst.append(df_timetable_origin.loc[timetable_origin_index_next, 'shortcut'])
            arc_lst.append(df_timetable_origin.loc[timetable_origin_index, 'shortcut'])
        arc_lst.append(1)
        df_timetable_trainline_arc_based_lst.append(arc_lst)
        
    df_timetable_all_trainlines_arc_based_lst.append(df_timetable_trainline_arc_based_lst)
        
    #get longest time_span
    trainline_min_departure_lst = df_timetable_origin.loc[0, 'departure'].split(':')
    trainline_min_departure_in_minutes = round(float(trainline_min_departure_lst[0])*60 + float(trainline_min_departure_lst[1]) + float(trainline_min_departure_lst[2])/60, 3)
    timetable_origin_index_max = len(df_timetable_origin.index)-1
    trainline_max_arrival_lst = df_timetable_origin.loc[timetable_origin_index_max, 'arrival'].split(':')
    trainline_max_arrival_in_minutes = round(float(trainline_max_arrival_lst[0])*60 + float(trainline_max_arrival_lst[1]) + float(trainline_max_arrival_lst[2])/60, 3)
    time_span_lst.append(math.ceil(trainline_max_arrival_in_minutes - trainline_min_departure_in_minutes))
    
    trainline_counter += 1

#%%
#adjust all trains in the same time_slot based on the longest time_span and copy them each hour
#define time_span
time_span = max(time_span_lst) - max(time_span_lst)%60 + 60
number_of_period = int(time_span / 60)
#%%
for timetable_trainline in df_timetable_all_trainlines_arc_based_lst:
    for timetable_trainline_ride_arc_lst in timetable_trainline:
        for i in range(number_of_period):
            print(i)
            timetable_train_ride_arc_lst = []
            print(timetable_train_ride_arc_lst)
            timetable_train_ride_arc_lst = timetable_trainline_ride_arc_lst
            
            timetable_train_ride_arc_lst[4] = round((timetable_train_ride_arc_lst[4]%60)+60*i, 3)
            print(timetable_train_ride_arc_lst[4])
            timetable_train_ride_arc_lst[5] = round((timetable_train_ride_arc_lst[5]%60)+60*i, 3)
            print(timetable_train_ride_arc_lst)
            df_timetable_all_trains_arc_based_lst.append(timetable_train_ride_arc_lst)
            print(df_timetable_all_trains_arc_based_lst)
        

#create dataframe with all timetable data
#df_timetable_all_trains_arc_based = pd.DataFrame(df_timetable_all_trains_arc_based_lst, columns =  ['Train', 'type', 'i', 'j', 'dep', 'arr', 'arc_i', 'arc_j', 'arc_tr'])  
#export dataframe to csv
#df_timetable_all_trains_arc_based.to_csv(filename_csv, sep = ';')


