# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 09:07:09 2022

@author: Gut
"""

#import gurobipy as gp
#from gurobipy import *
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.ticker import AutoMinorLocator
import math
import os

#%% Define a function to get input manually from the user

def run_the_program_individual(Testname, df):
    print("Fahrpläne können für einzelne Streckengleise (single track), einzelne Streckenabschnitte (single section) erstellt werden. Perspektivisch sollen Fahrpläne auch für einzelne Linien oder Zugläufe erstellt werden können, aber das ist noch in Arbeit.")
    timetable_choice = int(input('Wählen Sie welchen Fahrplantyp sie angezeigt haben wollen, indem Sie die entsprechende Ziffer eingeben. 1 Einzelner Streckenabschnitt (single track), 2 - Einzelner Streckenabschnitt (single arc), 3 - Mehrere Streckenabschnitte (multi-arc) oder 4 - Fahrplan entlang des Fahrweges eines Zuges.  '))
    
    # General properties of the Timetable
    PrintTrainAnnotation = input('Wollen Sie eine Beschriftung der Fahrlinien mit den zugehörigen Zugnamen? Geben Sie bitte J (Ja) oder N (Nein) ein.  ')
    PrintTimeAnnotation = input('Wollen Sie eine Beschriftung der Ankunfts- und Abfahrtszeitpunkte? Geben Sie bitte J (Ja) oder N (Nein) ein.  ')
    PrintLegend = input('Wollen Sie eine Legende? Geben Sie bitte J (Ja) oder N (Nein) ein.  ')
    TimeHorizon = input('Wählen Sie den gewünschten Zeitraum zur Darstellung des Fahrplanes. Wollen Sie den Fahrplan für den gesamten Untersuchungszeitraum, geben Sie U ein. Wollen Sie den Fahrplan vom ersten bis zum letzten Zug, geben Sie Z ein. Wollen Sie einen individuellen Zeitraum, geben Sie die Anfangs- und Endminute durch ein Komma separiert ohne Leerzeichen ein. Beachten Sie, dass nur Zugfahrten, die vollständig im gewählten Zeitfenster liegen dargestellt werden.  ')
    Directions = input('Wollen Sie die Darstellung für Zugfahrten beider Richtungen oder nur einer Richtung? Geben Sie 1 für eine Richtung oder 2 für beide Richtungen ein.  ')
    Directions = int(Directions)
    
    if timetable_choice == 1:
        print('Es wird ein Fahrplan für ein Streckengleis erstellt.')
        # Ask for the timetable sort dependet input
        track_chosen = input('Wählen Sie das gewünschte Streckengleis aus. Geben Sie dazu Startknoten, Zielknoten und Gleisnummer durch Kommata getrennt ohne Leerzeichen ein.  ')
        track_chosen_list = track_chosen.split(',')
        StartNode = track_chosen_list[0]
        EndNode = track_chosen_list[1]
        TrackNumber = track_chosen_list[2]
        # Call the next function
        drawTimetableForTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
    elif timetable_choice == 2:
        print('Es wird ein Fahrplan für einen Streckenabschnitt erstellt.')
        # Ask for the timetable sort dependet input
        section_chosen = input('Wählen Sie das gewünschte Streckengleis aus. Geben Sie dazu Startknoten und Zielknoten durch Komma getrennt ohne Leerzeichen ein.  ')
        section_chosen_list = section_chosen.split(',')
        StartNode = section_chosen_list[0]
        EndNode = section_chosen_list[1]
        # Call the next function
        drawTimetableForSingleSection(Testname, df, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
    elif timetable_choice == 3:
        print('Es wird ein Fahrplan für mehrere zusammenhängende Streckenabschnitte erstellt.')
        sections_chosen = input('Wählen Sie die gewünschten Streckenabschnitte aus. Beachten Sie, dass die Abschnitte zusammenhängen müssen. Geben Sie die Knoten in der angefahrenen Reihenfolge durch Kommata getrennt ohne Leerzeichen in der richtigen zusammenhängenden Reihenfolge ein. Beachten Sie, dass das Programm keine Überprüfung Ihrer Eingabe durchführt. Sie sind für die korrekte Eingabe verantwortlich.  ')
        Nodes = sections_chosen.split(',')
        drawTimetableForMultiSections(Testname, df, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
    elif timetable_choice == 4:
        print('Es wird ein Fahrplan entlang des Fahrtverlaufs eines Zuges erstellt.')
        # Ask for the timetable sort dependent input
        Train = input('Wählen Sie den Zug entlang dessen Laufweg der Fahrplan gedruckt werden soll und geben Sie die Zugbezeichnung ein.  ')
        Tracks = input('Geben Sie an, ob nur die Fahrten auf vom gewählten Zug befahrenen Streckengleise (T) dargestellt werden sollen oder alle Zugfahrten entlang des Fahrtverlaufs auf allen Streckngleisen (S). Geben Sie dazu entweder T oder S ein.  ')
        # Call the next function
        drawTimetableforTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
    else:
        print('Ungültige Eingabe. Bitte geben Sie eine Zahl von 1 bis 4 ein.')   


#%% Define the overall functions

def drawTimetableForTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    TrackNumber = str(TrackNumber)
    StructureTheDataTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)

def drawTimetableForSingleSection(Testname, df, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    timetable_choice = 2
    Nodes = []
    StructureTheDataSection(Testname, df, timetable_choice, StartNode, EndNode, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
def drawTimetableForMultiSections(Testname, df, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    timetable_choice = 3 # needed because structuredata-function used for single and multi-section
    StartNode = ''
    EndNode = ''
    StructureTheDataSection(Testname, df, timetable_choice, StartNode, EndNode, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    
def drawTimetableforTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    StructureTheDataTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)

#%% Functions for Single Track

# Function to structure the data for tracks
def StructureTheDataTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    # Create a column for the sections and for tracks, eachone for undirected, one for directed
    df['track'] = df['arc_i'] + ' - ' + df['arc_j'] + ' ' + df['arc_tr'].astype(str)
    df['track_directed'] =  df['i'] + ' - ' + df['j'] + ' ' + df['arc_tr'].astype(str)
    
    # Create a DataFrame only with the tracks
    df_tracks = df.loc[: , ['arc_i','arc_j','arc_tr','track','track_directed']]
    # Delete all duplicates to get all arcs
    df_tracks.drop_duplicates(inplace = True, ignore_index = True)
    # Sort by alphabet
    df_tracks.sort_values(by=['track'], inplace = True)
    # Change DataFrame to list
    #df_tracks_list = df_tracks['track'].tolist()
    
    GetTrainsOfTrack(Testname, df_tracks, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)

# Function to Get the Dataset of the Trains riding on the chosen single track
def GetTrainsOfTrack(Testname, df_tracks, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    plot_area = []
    # Select the plot area and select all train rides of the chosen track and direction(s)
    if Directions == 1:
        plot_area.append(StartNode + ' - ' + EndNode + ' ' + TrackNumber)
        # Select all train rides on the chosen track
        train_rides = df.loc[df['track_directed'].isin(plot_area)]
    
    elif Directions == 2:
        plot_area.append(StartNode + ' - ' + EndNode + ' ' + TrackNumber)
        plot_area.append(EndNode + ' - ' + StartNode + ' ' + TrackNumber)
        # Select all train rides on the chosen track
        train_rides = df.loc[df['track'].isin(plot_area)]
    
    # Get a list of the nodes of the chosen track
    Nodes = [StartNode, EndNode]
    
    # Create Filename
    fname = Testname + '_' + StartNode + '_' + EndNode + '_' + TrackNumber
        
    # Call the next function
    TimeWindow(df, train_rides, Nodes, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname)        

#%% Functions for Sections (Single and Multi)

# Function to structure the data for sections
def StructureTheDataSection(Testname, df, timetable_choice, StartNode, EndNode, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    # Create a column for the tracks, one for undirected, one for directed
    df['section'] = df[['arc_i', 'arc_j']].agg(' - '.join, axis=1)
    df['section_directed'] = df[['i','j']].agg(' - '.join, axis=1)
    
    # Create a DataFrame only with the sections
    df_sections = df.loc[: , ['arc_i','arc_j','section','section_directed']]
    # Delete all duplicates to get all arcs
    df_sections.drop_duplicates(inplace = True, ignore_index = True)
    # Sort by alphabet
    df_sections.sort_values(by=['section'], inplace = True)
    # Change DataFrame to list
    #df_section_list = df_sections['section'].tolist()
    
    if timetable_choice == 2:
        GetTrainsOfSingleSection(Testname, df, df_sections, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
    elif timetable_choice == 3:
        GetTrainsOfMultiSection(Testname, df, df_sections, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)

# Function to get the Dataset of the Trains riding on the chosen single section
def GetTrainsOfSingleSection(Testname, df, df_sections, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    plot_area = []
    # Select the plot area and select all train rides of the chosen track and direction(s)
    if Directions == 1:
        plot_area.append(StartNode + ' - ' + EndNode)
        # Select all train rides on the chosen track
        train_rides = df.loc[df['section_directed'].isin(plot_area)]
        
    elif Directions == 2:
        plot_area.append(StartNode + ' - ' + EndNode)
        plot_area.append(EndNode + ' - ' + StartNode)         
        # Select all train rides on the chosen track
        train_rides = df.loc[df['section'].isin(plot_area)]
    
    # Get a list of the nodes of the chosen section
    Nodes = [StartNode, EndNode]
        
    # Create Filename
    fname = Testname + '_' + StartNode + '_' + EndNode
    
    # Call the next function
    TimeWindow(df, train_rides, Nodes, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname)

# Function to get the Dataset of the Trains riding on the chosen multi sections
def GetTrainsOfMultiSection(Testname, df, df_sections, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    plot_area = []
    i = 0
    
    # Select the plot area and select all train rides of the chosen track and direction(s)
    if Directions == 1:
        while i < len(Nodes)-1:
            plot_area.append(Nodes[i] + ' - ' + Nodes[i+1])
            i += 1
        # Select all train rides on the chosen track
        train_rides = df.loc[df['section_directed'].isin(plot_area)]
        
    elif Directions == 2:
        while i < len(Nodes)-1:
            plot_area.append(Nodes[i] + ' - ' + Nodes[i+1])
            plot_area.append(Nodes[i+1] + ' - ' + Nodes[i])
            i += 1
        # Select all train rides on the chosen track
        train_rides = df.loc[df['section'].isin(plot_area)]
    
    # Create Filename
    StartNode = Nodes[0]
    EndNode = Nodes[-1]
    fname = Testname + '_' + StartNode + '_' + EndNode
    
    # Call the next function
    TimeWindow(df, train_rides, Nodes, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname)    

#%% Functions for Timetables along the ride of a single train

def StructureTheDataTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    # Create a column for the arcs and one for the tracks, each for undirected and directed
    df['section'] = df[['arc_i', 'arc_j']].agg(' - '.join, axis=1)
    df['section_directed'] = df[['i','j']].agg(' - '.join, axis=1)
    df['track'] = df['section'] + ' ' + df['arc_tr'].astype(str)
    df['track_directed'] = df['section_directed'] + ' ' + df['arc_tr'].astype(str)

    # Create a DataFrame only with the trains
    df_trains = df.loc[: , ['Train']]
    # Delete all duplicates to get all trains
    df_trains.drop_duplicates(inplace = True, ignore_index = True)
    # Sort by Alphabet
    df_trains.sort_values(by=['Train'], inplace = True)
    
    GetTrainsOfTrainRide(Testname, df_trains, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)

def GetTrainsOfTrainRide(Testname, df_trains, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend):
    plot_area = []
    Nodes = []
    tracks_or_sections = Tracks
    
    # Generate a list of nodes in the right order along the rides of the chosen train
    train_chosen_rides = df.loc[df['Train'] == Train]
    # Get all i nodes
    a = 0
    b = len(train_chosen_rides)-1
    while a < b:
        min_dep = train_chosen_rides['dep'].min()
        actual_ride = train_chosen_rides.loc[train_chosen_rides['dep'] == min_dep]
        actual_node = actual_ride['i'].loc[actual_ride.index[0]]
        Nodes.append(actual_node)
        train_chosen_rides.drop(actual_ride.index, inplace = True)
        a += 1
    # Get the j node for the last section of the train ride
    min_dep = train_chosen_rides['dep'].min()
    actual_ride = train_chosen_rides.loc[train_chosen_rides['dep'] == min_dep]
    actual_node = actual_ride['i'].loc[actual_ride.index[0]]
    Nodes.append(actual_node)
    actual_node = actual_ride['j'].loc[actual_ride.index[0]]
    Nodes.append(actual_node)
    train_chosen_rides.drop(actual_ride.index, inplace = True)
    
    train_chosen_rides2 = df.loc[df['Train'] == Train]
    i = 0
    j = 0
    k = len(Nodes)-1
    
    # Select the plot area and all train rides, different ways for different requests necessary
    if tracks_or_sections == 'T': # single tracks
        plot_area_completesections = []
        if Directions == 1: # single tracks, one direction
            # Create the arcs
            while i < k:
                plot_area_completesections.append(Nodes[i] + ' - ' + Nodes[i+1])
                i += 1
            # Chose the number of the tracks and append plot_area with the specified track 
            while j < k:
                actual_section = plot_area_completesections[j]
                actual_ride2 = train_chosen_rides2.loc[train_chosen_rides2['section_directed'].eq(actual_section)]
                actual_track_number = actual_ride2['arc_tr'].loc[actual_ride2.index[0]].astype(str)
                plot_area.append(Nodes[j] + ' - ' + Nodes[j+1] + ' ' +  actual_track_number)
                j += 1
            # Select all train rides on the chosen track
            train_rides = df.loc[df['track_directed'].isin(plot_area)]
            
        elif Directions == 2: # single tracks, both directions
            while i < k:
                plot_area_completesections.append(Nodes[i] + ' - ' + Nodes[i+1])
                plot_area_completesections.append(Nodes[i+1] + ' - ' + Nodes[i])
                i += 1
            # Chose the number of the tracks and append plot_area with the specified track 
            while j < k:
                actual_sections = [plot_area_completesections[2*j], plot_area_completesections[2*j+1]]
                actual_ride2 = train_chosen_rides2.loc[train_chosen_rides2['section'].isin(actual_sections)]
                actual_track_number = actual_ride2['arc_tr'].loc[actual_ride2.index[0]].astype(str)
                plot_area.append(Nodes[j] + ' - ' + Nodes[j+1] + ' ' +  actual_track_number)
                plot_area.append(Nodes[j+1] + ' - ' + Nodes[j] + ' ' +  actual_track_number)
                j += 1
            # Select all train rides on the chosen track
            train_rides = df.loc[df['track'].isin(plot_area)]
    
    elif tracks_or_sections == 'S': # complete sections
        if Directions == '1': # complete sections, one direction
            while i < k:
                plot_area.append(Nodes[i] + ' - ' + Nodes[i+1])
                i += 1
            # Select all train rides on the chosen track
            train_rides = df.loc[df['section_directed'].isin(plot_area)]
        
        elif Directions == '2': # complete sections, both directions
            while i < k:
                plot_area.append(Nodes[i] + ' - ' + Nodes[i+1])
                plot_area.append(Nodes[i+1] + ' - ' + Nodes[i])
                i += 1
            # Select all train rides on the chosen track
            train_rides = df.loc[df['section'].isin(plot_area)]
    
    # Create Filename
    fname = Testname + '_' + Train
    
    # Call the next function
    TimeWindow(df, train_rides, Nodes, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname)

#%% Define a function to chose the time window

def TimeWindow(df, train_rides, Nodes, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname):
    
    if TimeHorizon == 'U' or TimeHorizon == 'u':
        # Get the time span of the data and round it to Minute '10
        time_min_df = df['dep'].min()
        time_min = math.floor(time_min_df * 10**-2) / 10**-2
        time_max_df = df['arr'].max()
        time_max = math.ceil(time_max_df * 10**-2) / 10**-2
    elif TimeHorizon == 'Z' or TimeHorizon == 'z':
        time_min = train_rides['dep'].min()
        time_max = train_rides['arr'].max()
    else:
        time_input_list = TimeHorizon.split(',')
        time_min = int(time_input_list[0])
        time_max = int(time_input_list[1])
    
    # Select all train rides which starts and/or ends within the time window
    train_rides = train_rides.loc[(train_rides['dep'] <= (time_max)) & (train_rides['arr'] >= (time_min))]
    
    timetable_plot(df, train_rides, Nodes, time_min, time_max, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname)
    
    with pd.option_context('display.max_rows', None,
                       'display.max_columns', None,
                       'display.precision', 3,
                       ):
        print(train_rides)

#%% Create a general function for plotting all sorts of timetables

def timetable_plot(df, train_rides, Nodes, time_min, time_max, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend, fname):
    y_step = 30
        
    # Create a dictionary for Replacing the values
    nodes_dict = {Nodes[x] : x for x in range(len(Nodes))}
        # Replace the values in 'i' and 'j' by numeric, dummy values to create the plot in the right order
    train_rides.loc[: , 'i'] = train_rides['i'].map(nodes_dict)
    train_rides.loc[: , 'j'] = train_rides['j'].map(nodes_dict)
    
    # Get the time span to adjust the height of the figure
    time_span = time_max - time_min
    # Inch to centimeter
    cm =1/2.54
    # Create binary variable for giving extra space for the legend, if legend is printed
    if PrintLegend == 'J' or PrintLegend == 'j':
        legend_binary = 1
    else:
        legend_binary = 0
    
    # Get the start time value
    ylabel_min = time_min - math.fmod(time_min, y_step) + y_step
    
    ### Create Figure
    number_of_nodes = len(Nodes)
    fig, ax = plt.subplots(figsize=(3*len(Nodes)*cm, time_span*4/60*cm+1*cm*legend_binary),dpi=300) # 1 cm for the legend at the bottom if legend is printed
    ax.set(xlim=(0, number_of_nodes-1), 
           ylim=(time_max, time_min),
           #title='Fahrplan'
           )
    ax.set_xticks(np.arange(0, number_of_nodes, 1))
    ax.set_xticklabels(Nodes)
    ax.set_yticks(np.arange(ylabel_min, time_max, y_step))
    ax.set_yticklabels(np.arange(ylabel_min, time_max, y_step), fontsize='small')
    ax.tick_params(top=True, labeltop=True, bottom=True, labelbottom=True, left=True, labelleft=True, right=True, labelright=True)
    #ax.grid(True)
    ax.grid(which='major', color='#000000', linewidth=1.0)
    ax.grid(which='minor', color='#808080', linewidth=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator(3))
    
    
    ### Create custom legend
    if PrintLegend == 'J' or PrintLegend == 'j':
        # Define all possible legend entries
        legend_track1 = mlines.Line2D((0, 0), (1, 0), linestyle='solid', color='#000000', label=1)
        legend_track2 = mlines.Line2D((0, 0), (1, 0), linestyle='dotted', color='#000000', label=2)
        legend_track3 = mlines.Line2D((0, 0), (1, 0), linestyle='dashed', color='#000000', label=3)
        legend_track4 = mlines.Line2D((0, 0), (1, 0), linestyle='dashdot', color='#000000', label=4)
        legend_track_others = mlines.Line2D((0, 0), (1, 0), linestyle=(0, (3, 5, 1, 5, 1, 5)), color='#000000', label=5)
        legend_fill = mlines.Line2D((0,0), (1,0), linestyle='None', label=0)
        legend_ice = mlines.Line2D((0, 0), (1, 0), linestyle='solid', color='#FF0000', label=6)
        legend_rb = mlines.Line2D((0, 0), (1, 0), linestyle='solid', color='#006400', label=7)
        legend_gz = mlines.Line2D((0, 0), (1, 0), linestyle='solid', color='#0000FF', label=8)
        
        possible_legend_entries = [legend_track1, legend_track2, legend_track3, legend_track4, legend_track_others, legend_ice, legend_rb, legend_gz]
        possible_legend_entries_text = ['Gleis 1', 'Gleis 2', 'Gleis 3', 'Gleis 4', 'Gleise 5+', 'ICE', 'RB', 'GZ']
        
        # Define list of possible legend entries seperat for tracknumbers and traintypes to garante a consistent order in the legend
        list_of_tracknumbers = [1,2,3,4]
        list_of_traintypes = ['ICE', 'RB', 'GZ']
        
        
        # Get all used track numbers and train types
        tracknumbers_to_print = train_rides.loc[: , ['arc_tr']]
        tracknumbers_to_print.drop_duplicates(inplace = True, ignore_index = True)
        tracknumbers_to_print_list = tracknumbers_to_print['arc_tr'].tolist()
        print(tracknumbers_to_print_list)
        
        traintypes_to_print = train_rides.loc[: , ['Typ']]
        traintypes_to_print.drop_duplicates(inplace = True, ignore_index = True)
        traintypes_to_print_list = traintypes_to_print['Typ'].tolist()
        
        print(traintypes_to_print_list)
    
        # Create a list of all used legend entries and the entry_texts
        # Create empty lists
        legend_entries_tracknumbers = []
        legend_entries_tracknumbers_text = []
        legend_entries_traintypes = []
        legend_entries_traintypes_text = []        
        legend_entries = []
        legend_entries_text = []
        
        # Create seperate lists of legend sign and textt for tracknumbers and traintypes, get the number of columns (max of number of tracknumbers or traintypes); if there are more train_types than tracknumbers create invisible fill entries, 
        # Create list of legend sign an text of tracknumbers for the tracks 1-4, if used
        for i in list_of_tracknumbers:
            if (i in tracknumbers_to_print_list):
                legend_entries_tracknumbers.append(possible_legend_entries[i-1])
                legend_entries_tracknumbers_text.append(possible_legend_entries_text[i-1])
        # If there are used tracks with number 5+ add the symbology for these tracknumber group
        for k in tracknumbers_to_print_list:
            if k >= 5:
                legend_entries_tracknumbers.append(possible_legend_entries[i-1])
                legend_entries_tracknumbers_text.append(possible_legend_entries_text[i-1])
        
        # Get the number of columns as the max of tracknumbers or traintypes; if there are more traintypes than tracknumbers create invisible tracknumber fill entries
        if len(traintypes_to_print_list) > len(tracknumbers_to_print_list):
            col_legend = len(traintypes_to_print_list)
            len_difference = len(traintypes_to_print_list) - len(tracknumbers_to_print_list)
            while len_difference > 0:
                legend_entries_tracknumbers.append(legend_fill)
                legend_entries_tracknumbers_text.append(' ')
                len_difference -= 1
        else:
            col_legend = len(tracknumbers_to_print_list)
        
        # Create list of legend sign and text of used traintypes
        for x in list_of_traintypes:
            if (x in traintypes_to_print_list):
                j = list_of_traintypes.index(x)
                entry = possible_legend_entries[j+5]
                legend_entries_traintypes.append(entry)
                legend_entries_traintypes_text.append(x)
        
        # Create a string with all legend entries and entry texts alternating tracknumber and traintype to get in the final legend one row for the tracknumbers and one for the traintypes (the legend is filled column after column)
        k = 0
        while k < col_legend:
            legend_entries.append(legend_entries_tracknumbers[k])
            legend_entries.append(legend_entries_traintypes[k])
            legend_entries_text.append(legend_entries_tracknumbers_text[k])
            legend_entries_text.append(legend_entries_traintypes_text[k])
            k += 1
        
        # Get the point to fix the upper bound of the legend
        y_legend = -((time_span*4/60*cm+1*cm)/(time_span*4/60*cm)-1)
        
        # Create the legend
        ax.legend(legend_entries, legend_entries_text, bbox_to_anchor = (0.5, y_legend), loc='upper center', ncol = col_legend)
    
    
    ### Iteration over the Index of the Dataframe to create the line of each section for each train individually
    for idx in train_rides.index:
        # Select the row with the actual index
        train_plot = train_rides.loc[[idx]]
        # Select the parameters for plotting by index and column
        x = [train_plot.at[idx,'i'], train_plot.at[idx,'j']]
        y = [train_plot.at[idx,'dep'], train_plot.at[idx,'arr']]
        
       
        # Track color by train type. 
        if train_plot.at[idx,'i'] < train_plot.at[idx,'j']:
            linewidth_value = 1.5
        elif train_plot.at[idx,'j'] < train_plot.at[idx,'i']:
            linewidth_value = 1.0
        
        # Less bold colors for trains running "backwards"
        if train_plot.at[idx, 'Typ'] == 'RB':
            traincolor = '#006400'
        elif train_plot.at[idx, 'Typ'] == 'ICE':
            traincolor = '#FF0000'
        elif train_plot.at[idx, 'Typ'] == 'GZ':
            traincolor = '#0000FF'
        
        # Choice the track linestyle - it is assumed that there will be mostly max. 4 tracks for each section, if there are more, the rest get the same linestyle
        if train_plot.at[idx, 'arc_tr'] == 1:
            trackstyle = 'solid'
        elif train_plot.at[idx, 'arc_tr'] == 2:
            trackstyle = 'dotted'
        elif train_plot.at[idx, 'arc_tr'] == 3:
            trackstyle = 'dashed'
        elif train_plot.at[idx, 'arc_tr'] == 4:
            trackstyle = 'dashdot'
        else:
            trackstyle = (0, (3, 5, 1, 5, 1, 5))

        # Plot the line
        ax.plot(x, y, color=traincolor, linestyle=trackstyle, linewidth=linewidth_value)
        
        # Plot Annotations
        if PrintTrainAnnotation == 'J' or PrintTrainAnnotation == 'j':
            
            # Different annotation whether the train comes from left or right in the timetable
            if train_plot.at[idx, 'i'] < train_plot.at[idx, 'j']:
                xylabel = ((train_plot.at[idx,'i']+(train_plot.at[idx,'j']-train_plot.at[idx,'i'])*0.42), train_plot.at[idx,'dep']+(train_plot.at[idx,'arr']-train_plot.at[idx,'dep'])*0.42)
                
                x1 = train_plot.at[idx,'i']
                x2 = train_plot.at[idx,'j']
                y1 = train_plot.at[idx,'arr']
                y2 = train_plot.at[idx,'dep']
                                
                p1 = ax.transData.transform_point((x1, y2))
                p2 = ax.transData.transform_point((x2, y1))
                Dy = (p2[1] - p1[1])
                Dx = (p2[0] - p1[0])
                rotn = np.degrees(np.arctan2(Dy,Dx))
                
                ax.annotate(train_plot.at[idx, 'Train'], xy = xylabel, ha = 'right', va = 'bottom', rotation = rotn, rotation_mode='anchor', color=traincolor, fontsize = 5)
                             
            else:
                xylabel = ((train_plot.at[idx,'i']+(train_plot.at[idx,'j']-train_plot.at[idx,'i'])*0.42), train_plot.at[idx,'dep']+(train_plot.at[idx,'arr']-train_plot.at[idx,'dep'])*0.42)
                
                x1 = train_plot.at[idx,'j']
                x2 = train_plot.at[idx,'i']
                y1 = train_plot.at[idx,'dep']
                y2 = train_plot.at[idx,'arr']
                                
                p1 = ax.transData.transform_point((x1, y2))
                p2 = ax.transData.transform_point((x2, y1))
                Dy = (p2[1] - p1[1])
                Dx = (p2[0] - p1[0])
                rotn = np.degrees(np.arctan2(Dy,Dx))
                
                ax.annotate(train_plot.at[idx, 'Train'], xy = xylabel, ha = 'left', va = 'bottom', rotation = rotn, rotation_mode='anchor', color=traincolor, fontsize = 5)
                
        if PrintTimeAnnotation == 'J' or PrintTimeAnnotation == 'j':
            if train_plot.at[idx, 'i'] < train_plot.at[idx, 'j']:
                ax.annotate(train_plot.at[idx, 'dep'], xy = ((train_plot.at[idx,'i'], train_plot.at[idx,'dep']+1)), ha = 'left', va = 'top', color=traincolor, fontsize = 4)
                ax.annotate(train_plot.at[idx, 'arr'], xy = ((train_plot.at[idx,'j'], train_plot.at[idx,'arr']-1)), ha = 'right', va = 'bottom', color=traincolor, fontsize = 4)
            else:
                ax.annotate(train_plot.at[idx, 'dep'], xy = ((train_plot.at[idx,'i'], train_plot.at[idx,'dep']+1)), ha = 'right', va = 'top', color=traincolor, fontsize = 4)
                ax.annotate(train_plot.at[idx, 'arr'], xy = ((train_plot.at[idx,'j'], train_plot.at[idx,'arr']-1)), ha = 'left', va = 'bottom', color=traincolor, fontsize = 4)
        
    # Plot the timetable
    plt.show
    
    # Change Path for savefig
    #dir_name = r"C:\Users\Gut\Documents" # das r vor dem Pfadnamen ist zwingend zu lassen bei Wechsel des Pfades
    #plt.rcParams['savefig.directory'] = os.chdir(os.path.dirname(dir_name))
    
    # Append the extension .png to filename
    fname = fname + '.png'
    
    # Save the timetable to a png-file
    plt.savefig(fname, format='png', bbox_inches = 'tight')
  

#%% Run the functions

#drawTimetableForTrack(Testname, df, StartNode, EndNode, TrackNumber, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
#drawTimetableForSingleSection(Testname, df, StartNode, EndNode, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
#drawTimetableForMultiSections(Testname, Nodes, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
#drawTimetableforTrain(Testname, df, Train, Tracks, Directions, TimeHorizon, PrintTrainAnnotation, PrintTimeAnnotation, PrintLegend)
#run_the_program_individual(Testname, df)


