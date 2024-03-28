import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.ticker import AutoMinorLocator
import math
import os
from datetime import datetime

#%% create empty dataframe - possible to put it at the end
filename_output = '../../example_data/import/haushaltsinvestitionsbericht/prepared table/2024_bedarfsplan.xlsx'
# filename_output = os.path.join('C:\\','Users','Gut','Documents','Gastel_Praktikum','Programme','Verkehrsinvestitionsbericht','Ergebnisse','budget_2023_bedarfsplan.csv')

filename_input = '../../example_data/import/haushaltsinvestitionsbericht/2024_bedarfsplan.xlsx'

col_names_budget_bedarfsplan = ['budget_year', 'lfd_nr', 'fin_ve', 'bedarfsplan_number', 'name', 'starting_year', 
                                'cost_estimate_original', 'cost_estimate_last_year', 'cost_estimate_actual', 
                                'cost_estimate_actual_third_parties', 'cost_estimate_actual_equity', 
                                'cost_estimate_actual_891_01', 'cost_estimate_actual_891_02', 'cost_estimate_actual_891_03', 
                                'cost_estimate_actual_891_04', 'cost_estimate_actual_891_91', 'delta_previous_year', 
                                'delta_previous_year_relativ', 'delta_previous_year_reasons', 'spent_two_years_previous', 
                                'spent_two_years_previous_third_parties', 'spent_two_years_previous_equity', 
                                'spent_two_years_previous_891_01', 'spent_two_years_previous_891_02', 
                                'spent_two_years_previous_891_03', 'spent_two_years_previous_891_04', 
                                'spent_two_years_previous_891_91', 'allowed_previous_year', 
                                'allowed_previous_year_third_parties', 'allowed_previous_year_equity', 
                                'allowed_previous_year_891_01', 'allowed_previous_year_891_02', 
                                'allowed_previous_year_891_03', 'allowed_previous_year_891_04', 
                                'allowed_previous_year_891_91', 'spending_residues', 'spending_residues_891_01', 
                                'spending_residues_891_02', 'spending_residues_891_03', 'spending_residues_891_04', 
                                'spending_residues_891_91', 'year_planned', 'year_planned_third_parties', 
                                'year_planned_equity', 'year_planned_891_01', 'year_planned_891_02', 'year_planned_891_03', 
                                'year_planned_891_04', 'year_planned_891_91', 'next_years', 'next_years_third_parties', 
                                'next_years_equity', 'next_years_891_01', 'next_years_891_02', 'next_years_891_03', 
                                'next_years_891_04', 'next_years_891_91']

#df_budget_bedarfsplan = pd.DataFrame(columns = col_names_budget_bedarfsplan)
budget_year = 2023


#%%

df_budget_bedarfsplan_lst = []
new_project_lst = []

dict_fin_ve_lfd_nr = {}

#%% read csv-file in and adjust the format
verkehrsinvestitionsbericht_filename = '2023_VIB_Schiene_Tabelle_1.csv'
# verkehrsinvestitionsbericht_filename = os.path.join('C:\\','Users','Gut','Documents','Gastel_Praktikum','Programme','Verkehrsinvestitionsbericht','2023_VIB_Schiene_Tabelle_1.xlsx')

verkehrsinvestitionsbericht_original = pd.read_csv(verkehrsinvestitionsbericht_filename, header = None, sep=';')


#%% Delete rows without entries

indexes_of_rows = verkehrsinvestitionsbericht_original.index

for row in indexes_of_rows:
    if pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 0]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 1]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 2]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 3]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 4]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 5]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 6]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 7]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 8]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 9]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 10]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 11]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 12]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 13]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 14]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 15]): # and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 16]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row, 17]):
        verkehrsinvestitionsbericht_original.drop(row, inplace = True)
    # complete all columns to check all cells of a row and then delete it

checkcheckcheck = 'fail'

#%%

# create a loop to treat each project seperat

#testvariable = 1
#while testvariable > 0:
while len(verkehrsinvestitionsbericht_original.index) > 0:
    #slice all rows of the project
    #identify the lines - check in which line j the next project starts and chose the rows i to j
    rows_of_project_lst = []
    rows_of_project_lst.append(0)
    proof_variable = 0
    row_counter = 1
    while proof_variable == 0 and row_counter <= 15:
        if row_counter in verkehrsinvestitionsbericht_original.index:
            if pd.isnull(verkehrsinvestitionsbericht_original.loc[row_counter, 0]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row_counter, 1]) and pd.isnull(verkehrsinvestitionsbericht_original.loc[row_counter, 2]):
                rows_of_project_lst.append(row_counter)
                row_counter += 1
            else:
                proof_variable = 1
        else:
            proof_variable = 1
    project_data = verkehrsinvestitionsbericht_original.loc[rows_of_project_lst]
    print(project_data)
    
    #reset lst
    new_project_lst = []
    
    #add fix parameters
    new_project_lst.append(budget_year)
    
    #check which variable parameters are used
    
    status_891_01 = 0
    status_891_02 = 0
    status_891_03 = 0
    status_891_04 = 0
    status_891_91 = 0
    status_third_parties = 0
    status_equity = 0
    
    for row in rows_of_project_lst:
        if '891 01' in str(project_data.loc[row, 3]):
            status_891_01 = 1
        if '891 02' in str(project_data.loc[row, 3]):
            status_891_02 = 1
        if '891 03' in str(project_data.loc[row, 3]):
            status_891_03 = 1
        if '891 04' in str(project_data.loc[row, 3]):
            status_891_04 = 1
        if '891 91' in str(project_data.loc[row, 3]):
            status_891_91 = 1
        if 'Dritter' in str(project_data.loc[row, 3]):
            status_third_parties = 1
        if 'Eigenmittel' in str(project_data.loc[row, 3]):
            status_equity = 1
    
    #add variable parameters
    #lfd_nr
    lfd_nr_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 0]) and lfd_nr_proof == 0:
            lfd_nr = project_data.loc[row, 0]
            lfd_nr_proof += 1
    new_project_lst.append(lfd_nr)
    
    #fin_ve
    fin_ve_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 1]) and fin_ve_proof == 0:
            fin_ve = project_data.loc[row, 1]
            fin_ve_proof += 1
    new_project_lst.append(fin_ve)
    
    #bedarfsplan_number
    bedarfsplan_number_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 2]) and bedarfsplan_number_proof == 0:
            bedarfsplan_number = project_data.loc[row, 2]
            bedarfsplan_number_proof += 1
    new_project_lst.append(bedarfsplan_number)
    
    #name
    name_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 3]) and name_proof == 0:
            if 'davon' in project_data.loc[row, 3]:
                name = project_data.loc[row, 3].split('davon')[0]
            elif 'nachrichtlich' in project_data.loc[row, 3]:
                name = project_data.loc[row, 3].split('nachrichtlich')[0]
            else:
                name = project_data.loc[row, 3]
            name_proof += 1
    new_project_lst.append(name)
    
    #starting_year
    starting_year_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 4]) and starting_year_proof == 0:
            starting_year = project_data.loc[row, 4]
            starting_year_proof += 1
    new_project_lst.append(starting_year)
    
    #cost_estimate_original
    cost_estimate_original_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 5]) and cost_estimate_original_proof == 0:
            cost_estimate_original = project_data.loc[row, 5]
            cost_estimate_original_proof += 1
    cost_estimate_original = int(str(cost_estimate_original).replace('.', ''))
    new_project_lst.append(cost_estimate_original)    
    
    #cost_estimate_last_year
    cost_estimate_last_year_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 6]):
            cost_estimate_last_year = project_data.loc[row, 6]
            cost_estimate_last_year_proof += 1
    cost_estimate_last_year = int(str(cost_estimate_last_year).replace('.', ''))
    new_project_lst.append(cost_estimate_last_year)
    
    
    #cost_estimate_actual - all sorts
    
    cost_estimate_actual_lst_part = []
    cost_estimate_actual_lst = []
    
    cost_estimate_actual_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 7]):
            cost_estimate_actual_lst_part = project_data.loc[row, 7].split()
            for i in cost_estimate_actual_lst_part:
                cost_estimate_actual_lst.append(i)
    
    cost_estimate_actual_counter = 0
    cost_estimate_actual = cost_estimate_actual_lst[cost_estimate_actual_counter]
    if not type(cost_estimate_actual) is int:
        if '.' in  cost_estimate_actual:
            cost_estimate_actual = int(cost_estimate_actual.replace('.', ''))
    cost_estimate_actual_counter += 1
    
    if status_891_01 == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_891_01 = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_891_01 == 1:
        cost_estimate_actual_891_01 = 'ERGÄNZEN'
    else:
        cost_estimate_actual_891_01 = '-'
    
    if status_891_02 == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_891_02 = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_891_02 == 1:
        cost_estimate_actual_891_02 = 'ERGÄNZEN'
    else:
        cost_estimate_actual_891_02 = '-'
    
    if status_891_03 == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_891_03 = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_891_03 == 1:
        cost_estimate_actual_891_03 = 'ERGÄNZEN'
    else:
        cost_estimate_actual_891_03 = '-'
    
    if status_891_04 == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_891_04 = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_891_04 == 1:
        cost_estimate_actual_891_04 = 'ERGÄNZEN'
    else:
        cost_estimate_actual_891_04 = '-'
    
    if status_891_91 == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_891_91 = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_891_91 == 1:
        cost_estimate_actual_891_91 = 'ERGÄNZEN'
    else:
        cost_estimate_actual_891_91 = '-'
    
    if status_third_parties == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_third_parties = cost_estimate_actual_lst[cost_estimate_actual_counter]
        cost_estimate_actual_counter += 1
    elif status_third_parties == 1:
        cost_estimate_actual_third_parties = 'ERGÄNZEN'
    else:
        cost_estimate_actual_third_parties = '-'
    
    if status_equity == 1 and cost_estimate_actual_counter < len(cost_estimate_actual_lst):
        cost_estimate_actual_equity = cost_estimate_actual_lst[cost_estimate_actual_counter]
    elif status_891_01 == 1:
        cost_estimate_actual_equity = 'ERGÄNZEN'
    else:
        cost_estimate_actual_equity = '-'
    
    new_project_lst.append(cost_estimate_actual)
    new_project_lst.append(cost_estimate_actual_third_parties)
    new_project_lst.append(cost_estimate_actual_equity)
    new_project_lst.append(cost_estimate_actual_891_01)
    new_project_lst.append(cost_estimate_actual_891_02)
    new_project_lst.append(cost_estimate_actual_891_03)
    new_project_lst.append(cost_estimate_actual_891_04)
    new_project_lst.append(cost_estimate_actual_891_91)
    
    #delta_previous_year and delta_previous_year_relativ
    if type(cost_estimate_actual) is int and type(cost_estimate_last_year) is int:
        delta_previous_year = cost_estimate_actual - cost_estimate_last_year
        delta_previous_year_relativ = delta_previous_year / cost_estimate_last_year
    else:
        delta_previous_year = 'ERGÄNZEN'
        delta_previous_year_relativ = 'ERGÄNZEN'
    
    new_project_lst.append(delta_previous_year)
    new_project_lst.append(delta_previous_year_relativ)
    
    #delta_previous_year_reasons
    delta_previous_year_reasons = ''
    new_project_lst.append(delta_previous_year_reasons)
    
    
    #spent_two_years_previous - all sorts
    
    spent_two_years_previous_lst_part = []
    spent_two_years_previous_lst = []
    
    spent_two_years_previous_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 11]):
            spent_two_years_previous_lst_part = project_data.loc[row, 11].split()
            for i in spent_two_years_previous_lst_part:
                spent_two_years_previous_lst.append(i)
    
    spent_two_years_previous_counter = 0
    spent_two_years_previous = spent_two_years_previous_lst[spent_two_years_previous_counter]
    if not type(spent_two_years_previous) is int:
        if '.' in  spent_two_years_previous:
            spent_two_years_previous = int(spent_two_years_previous.replace('.', ''))
    spent_two_years_previous_counter += 1
    
    #spent_two_years_previous_counter = 0
    #spent_two_years_previous = spent_two_years_previous_lst[spent_two_years_previous_counter]
    #spent_two_years_previous_counter += 1
    
    if status_891_01 == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_891_01 = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_891_01 == 1:
        spent_two_years_previous_891_01 = 'ERGÄNZEN'
    else:
        spent_two_years_previous_891_01 = '-'
    
    if status_891_02 == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_891_02 = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_891_02 == 1:
        spent_two_years_previous_891_02 = 'ERGÄNZEN'
    else:
        spent_two_years_previous_891_02 = '-'
    
    if status_891_03 == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_891_03 = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_891_03 == 1:
        spent_two_years_previous_891_03 = 'ERGÄNZEN'
    else:
        spent_two_years_previous_891_03 = '-'
    
    if status_891_04 == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_891_04 = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_891_04 == 1:
        spent_two_years_previous_891_04 = 'ERGÄNZEN'
    else:
        spent_two_years_previous_891_04 = '-'
    
    if status_891_91 == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_891_91 = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_891_91 == 1:
        spent_two_years_previous_891_91 = 'ERGÄNZEN'
    else:
        spent_two_years_previous_891_91 = '-'
    
    if status_third_parties == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_third_parties = spent_two_years_previous_lst[spent_two_years_previous_counter]
        spent_two_years_previous_counter += 1
    elif status_third_parties == 1:
        spent_two_years_previous_third_parties = 'ERGÄNZEN'
    else:
        spent_two_years_previous_third_parties = '-'
    
    if status_equity == 1 and spent_two_years_previous_counter < len(spent_two_years_previous_lst):
        spent_two_years_previous_equity = spent_two_years_previous_lst[spent_two_years_previous_counter]
    elif status_equity == 1:
        spent_two_years_previous_equity = 'ERGÄNZEN'
    else:
        spent_two_years_previous_equity = '-'
    
    new_project_lst.append(spent_two_years_previous)
    new_project_lst.append(spent_two_years_previous_third_parties)
    new_project_lst.append(spent_two_years_previous_equity)
    new_project_lst.append(spent_two_years_previous_891_01)
    new_project_lst.append(spent_two_years_previous_891_02)
    new_project_lst.append(spent_two_years_previous_891_03)
    new_project_lst.append(spent_two_years_previous_891_04)
    new_project_lst.append(spent_two_years_previous_891_91)
  
    
    #allowed_previous_year - all sorts
    
    allowed_previous_year_lst_part = []
    allowed_previous_year_lst = []
    
    allowed_previous_year_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 12]):
            allowed_previous_year_lst_part = project_data.loc[row, 12].split()
            for i in allowed_previous_year_lst_part:
                allowed_previous_year_lst.append(i)
    
    allowed_previous_year_counter = 0
    allowed_previous_year = allowed_previous_year_lst[allowed_previous_year_counter]
    if not type(allowed_previous_year) is int:
        if '.' in  allowed_previous_year:
            allowed_previous_year = int(allowed_previous_year.replace('.', ''))
    allowed_previous_year_counter += 1
    
    #allowed_previous_year_counter = 0
    #allowed_previous_year = allowed_previous_year_lst[allowed_previous_year_counter]
    #allowed_previous_year_counter += 1
    
    if status_891_01 == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_891_01 = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
    elif status_891_01 == 1:
        allowed_previous_year_891_01 = 'ERGÄNZEN'
    else:
        allowed_previous_year_891_01 = '-'
    
    if status_891_02 == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_891_02 = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
    elif status_891_02 == 1:
        allowed_previous_year_891_02 = 'ERGÄNZEN'
    else:
        allowed_previous_year_891_02 = '-'
    
    if status_891_03 == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_891_03 = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
    elif status_891_03 == 1:
        allowed_previous_year_891_03 = 'ERGÄNZEN'
    else:
        allowed_previous_year_891_03 = '-'
    
    if status_891_04 == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_891_04 = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
    elif status_891_04 == 1:
        allowed_previous_year_891_04 = 'ERGÄNZEN'
    else:
        allowed_previous_year_891_04 = '-'
    
    if status_891_91 == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_891_91 = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
    elif status_891_91 == 1:
        allowed_previous_year_891_91 = 'ERGÄNZEN'
    else:
        allowed_previous_year_891_91 = '-'
    
    if status_third_parties == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_third_parties = allowed_previous_year_lst[allowed_previous_year_counter]
        allowed_previous_year_counter += 1
        if '-' in allowed_previous_year_third_parties:
            chechcheckcheck = 'checkcheckcheck'
            allowed_previous_year_third_parties = '-'
    elif status_third_parties == 1:
        allowed_previous_year_third_parties = 'ERGÄNZEN'
    else:
        allowed_previous_year_third_parties = '-'
    
    if status_equity == 1 and allowed_previous_year_counter < len(allowed_previous_year_lst):
        allowed_previous_year_equity = allowed_previous_year_lst[allowed_previous_year_counter]
    else:
        allowed_previous_year_equity = '-'
    
    new_project_lst.append(allowed_previous_year)
    new_project_lst.append(allowed_previous_year_third_parties)
    new_project_lst.append(allowed_previous_year_equity)
    new_project_lst.append(allowed_previous_year_891_01)
    new_project_lst.append(allowed_previous_year_891_02)
    new_project_lst.append(allowed_previous_year_891_03)
    new_project_lst.append(allowed_previous_year_891_04)
    new_project_lst.append(allowed_previous_year_891_91)
    

    #spending_residues - all sorts
    
    spending_residues_lst_part = []
    spending_residues_lst = []
    
    spending_residues_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 13]):
            spending_residues_lst_part = project_data.loc[row, 13].split()
            for i in spending_residues_lst_part:
                spending_residues_lst.append(i)
    
    spending_residues_counter = 0
    spending_residues = spending_residues_lst[spending_residues_counter]
    if not type(spending_residues) is int:
        if '.' in  spending_residues:
            spending_residues = int(spending_residues.replace('.', ''))
    spending_residues_counter += 1
    
    #spending_residues_counter = 0
    #spending_residues = spending_residues_lst[spending_residues_counter]
    #spending_residues_counter += 1
    
    if status_891_01 == 1 and spending_residues_counter < len(spending_residues_lst):
        spending_residues_891_01 = spending_residues_lst[spending_residues_counter]
        spending_residues_counter += 1
    elif status_891_01 == 1:
        spending_residues_891_01 = 'ERGÄNZEN'
    else:
        spending_residues_891_01 = '-'
    
    if status_891_02 == 1 and spending_residues_counter < len(spending_residues_lst):
        spending_residues_891_02 = spending_residues_lst[spending_residues_counter]
        spending_residues_counter += 1
    elif status_891_02 == 1:
        spending_residues_891_02 = 'ERGÄNZEN'
    else:
        spending_residues_891_02 = '-'
    
    if status_891_03 == 1 and spending_residues_counter < len(spending_residues_lst):
        spending_residues_891_03 = spending_residues_lst[spending_residues_counter]
        spending_residues_counter += 1
    elif status_891_03 == 1:
        spending_residues_891_03 = 'ERGÄNZEN'
    else:
        spending_residues_891_03 = '-'
    
    if status_891_04 == 1 and spending_residues_counter < len(spending_residues_lst):
        spending_residues_891_04 = spending_residues_lst[spending_residues_counter]
        spending_residues_counter += 1
    elif status_891_04 == 1:
        spending_residues_891_04 = 'ERGÄNZEN'
    else:
        spending_residues_891_04 = '-'
    
    if status_891_91 == 1 and spending_residues_counter < len(spending_residues_lst):
        spending_residues_891_91 = spending_residues_lst[spending_residues_counter]
        spending_residues_counter += 1
    elif status_891_91 == 1:
        spending_residues_891_91 = 'ERGÄNZEN'
    else:
        spending_residues_891_91 = '-'

    
    new_project_lst.append(spending_residues)
    new_project_lst.append(spending_residues_891_01)
    new_project_lst.append(spending_residues_891_02)
    new_project_lst.append(spending_residues_891_03)
    new_project_lst.append(spending_residues_891_04)
    new_project_lst.append(spending_residues_891_91)
    
    
    #year_planned - all sorts
    
    year_planned_lst_part = []
    year_planned_lst = []
    
    year_planned_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 14]):
            year_planned_lst_part = project_data.loc[row, 14].split()
            for i in year_planned_lst_part:
                year_planned_lst.append(i)
    
    year_planned_counter = 0
    year_planned = year_planned_lst[year_planned_counter]
    if not type(year_planned) is int:
        if '.' in  year_planned:
            year_planned = int(year_planned.replace('.', ''))
    year_planned_counter += 1
    
    #year_planned_counter = 0
    #year_planned = year_planned_lst[year_planned_counter]
    #year_planned_counter += 1
    
    if status_891_01 == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_891_01 = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_891_01 == 1:
        year_planned_891_01 = 'ERGÄNZEN'
    else:
        year_planned_891_01 = '-'
    
    if status_891_02 == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_891_02 = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_891_02 == 1:
        year_planned_891_02 = 'ERGÄNZEN'
    else:
        year_planned_891_02 = '-'
    
    if status_891_03 == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_891_03 = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_891_03 == 1:
        year_planned_891_03 = 'ERGÄNZEN'
    else:
        year_planned_891_03 = '-'
    
    if status_891_04 == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_891_04 = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_891_04 == 1:
        year_planned_891_04 = 'ERGÄNZEN'
    else:
        year_planned_891_04 = '-'
    
    if status_891_91 == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_891_91 = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_891_91 == 1:
        year_planned_891_91 = 'ERGÄNZEN'
    else:
        year_planned_891_91 = '-'
    
    if status_third_parties == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_third_parties = year_planned_lst[year_planned_counter]
        year_planned_counter += 1
    elif status_third_parties == 1:
        year_planned_third_parties = 'ERGÄNZEN'
    else:
        year_planned_third_parties = '-'
    
    if status_equity == 1 and year_planned_counter < len(year_planned_lst):
        year_planned_equity = year_planned_lst[year_planned_counter]
    elif status_equity == 1:
        year_planned_equity = 'ERGÄNZEN'
    else:
        year_planned_equity = '-'
    
    new_project_lst.append(year_planned)
    new_project_lst.append(year_planned_third_parties)
    new_project_lst.append(year_planned_equity)
    new_project_lst.append(year_planned_891_01)
    new_project_lst.append(year_planned_891_02)
    new_project_lst.append(year_planned_891_03)
    new_project_lst.append(year_planned_891_04)
    new_project_lst.append(year_planned_891_91)
    

    
    #next_years - all sorts
    
    next_years_lst_part = []
    next_years_lst = []
    
    next_years_proof = 0
    for row in rows_of_project_lst:
        if not pd.isnull(project_data.loc[row, 15]):
            next_years_lst_part = project_data.loc[row, 15].split()
            for i in next_years_lst_part:
                next_years_lst.append(i)
    
    next_years_counter = 0
    next_years = next_years_lst[next_years_counter]
    if not type(next_years) is int:
        if '.' in  next_years:
            next_years = int(next_years.replace('.', ''))
    next_years_counter += 1
    
    #next_years_counter = 0
    #next_years = next_years_lst[next_years_counter]
    #next_years_counter += 1
    
    if status_891_01 == 1 and next_years_counter < len(next_years_lst):
        next_years_891_01 = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_891_01 == 1:
        next_years_891_01 = 'ERGÄNZEN'
    else:
        next_years_891_01 = '-'
    
    if status_891_02 == 1 and next_years_counter < len(next_years_lst):
        next_years_891_02 = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_891_02 == 1:
        next_years_891_02 = 'ERGÄNZEN'
    else:
        next_years_891_02 = '-'
    
    if status_891_03 == 1 and next_years_counter < len(next_years_lst):
        next_years_891_03 = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_891_03 == 1:
        next_years_891_03 = 'ERGÄNZEN'
    else:
        next_years_891_03 = '-'
    
    if status_891_04 == 1 and next_years_counter < len(next_years_lst):
        next_years_891_04 = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_891_04 == 1:
        next_years_891_04 = 'ERGÄNZEN'
    else:
        next_years_891_04 = '-'
    
    if status_891_91 == 1 and next_years_counter < len(next_years_lst):
        next_years_891_91 = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_891_91 == 1:
        next_years_891_91 = 'ERGÄNZEN'
    else:
        next_years_891_91 = '-'
    
    if status_third_parties == 1 and next_years_counter < len(next_years_lst):
        next_years_third_parties = next_years_lst[next_years_counter]
        next_years_counter += 1
    elif status_third_parties == 1:
        next_years_third_parties = 'ERGÄNZEN'
    else:
        next_years_third_parties = '-'
    
    if status_equity == 1 and next_years_counter < len(next_years_lst):
        next_years_equity = next_years_lst[next_years_counter]
    elif status_equity == 1:
        next_years_equity = 'ERGÄNZEN'
    else:
        next_years_equity = '-'
    
    new_project_lst.append(next_years)
    new_project_lst.append(next_years_third_parties)
    new_project_lst.append(next_years_equity)
    new_project_lst.append(next_years_891_01)
    new_project_lst.append(next_years_891_02)
    new_project_lst.append(next_years_891_03)
    new_project_lst.append(next_years_891_04)
    new_project_lst.append(next_years_891_91)
    
    df_budget_bedarfsplan_lst.append(new_project_lst)
    
    #last: remove the used rows of the dataframe
    print('davor')
    verkehrsinvestitionsbericht_original.drop(rows_of_project_lst, inplace = True)
    verkehrsinvestitionsbericht_original.reset_index(drop = True, inplace = True)
    print('danach')
    #testvariable -= 1

df_budget_bedarfsplan = pd.DataFrame(df_budget_bedarfsplan_lst, columns = col_names_budget_bedarfsplan)
df_budget_bedarfsplan.to_excel(filename_output)
# df_budget_bedarfsplan.to_csv(filename_output, sep = ';')

print(checkcheckcheck)

#%% code useful if delta_values available in the source

    #delta_previous_year
    #if not pd.isnull(project_data.loc[0, 8]):
    #    delta_previous_year = project_data.loc[0, 8]
    #elif not pd.isnull(project_data.loc[1, 8]):
    #    delta_previous_year = project_data.loc[1, 8]
    #elif not pd.isnull(project_data.loc[2, 8]):
    #    delta_previous_year = project_data.loc[2, 8]
    #new_project_lst.append(delta_previous_year)
    
    #delta_previous_year_relativ
    #if not pd.isnull(project_data.loc[0, 9]):
    #    delta_previous_year_relativ = project_data.loc[0, 9]
    #elif not pd.isnull(project_data.loc[1, 9]):
    #    delta_previous_year_relativ = project_data.loc[1, 9]
    #elif not pd.isnull(project_data.loc[2, 9]):
    #    delta_previous_year_relativ = project_data.loc[2, 9]
    #new_project_lst.append(delta_previous_year_relativ)
   

    
#%% create Variables - not necessary any more

#budget_year = 2023

#lfd_nr
#fin_ve
#bedarfsplan_number
#name
#starting_year

#cost_estimate_original
#cost_estimate_last_year
#cost_estimate_actual
#cost_estimate_actual_third_parties
#cost_estimate_actual_equity
#cost_estimate_actual_891_01
#cost_estimate_actual_891_02
#cost_estimate_actual_891_03
#cost_estimate_actual_891_04
#cost_estimate_actual_891_91

#delta_previous_year
#delta_previous_year_relativ
#delta_previous_year_reasons

#spent_two_years_previous
#spent_two_years_previous_third_parties
#spent_two_years_previous_equity
#spent_two_years_previous_891_01
#spent_two_years_previous_891_02
#spent_two_years_previous_891_03
#spent_two_years_previous_891_04
#spent_two_years_previous_891_91

#allowed_previous_year
#allowed_previous_year_third_parties
#allowed_previous_year_equity
#allowed_previous_year_891_01
#allowed_previous_year_891_02
#allowed_previous_year_891_03
#allowed_previous_year_891_04
#allowed_previous_year_891_91

#spending_residues
#spending_residues_891_01
#spending_residues_891_02
#spending_residues_891_03
#spending_residues_891_04
#spending_residues_891_91
	
#year_planned
#year_planned_third_parties
#year_planned_equity
#year_planned_891_01
#year_planned_891_02
#year_planned_891_03
#year_planned_891_04
#year_planned_891_91

#next_years
#next_years_third_parties
#next_years_equity
#next_years_891_01
#next_years_891_02
#next_years_891_03
#next_years_891_04
#next_years_891_91