import datetime

## CALCUATION PARAMETER
REROUTE_TRAINGROUP = False
DELETE_AREAS = False
CREATE_AREAS = False
OVERWRITE_INFRASTRUCTURE = True

## H2
KILOMETER_PER_STATION_H2 = 60
COST_STATION_H2 = 6000  # Tausend Euro

## Diesel
KILOMETER_PER_STATION_DIESEL = 40
COST_STATION_DIESEL = 1000  # Tausend Euro

## EFuel
KILOMETER_PER_STATION_EFUEL = 40
COST_STATION_EFUEL = 1000  # Tausend Euro

# Battery
WAIT_TIME = datetime.timedelta(minutes=10)

## DATE STUFF
BASE_YEAR = 2016
RATE = 0.017
ANUALITY_FACTOR = 0.0428
START_YEAR = 2030
START_MONTH = 1
START_DATE = 1
TRACTIONS = ["electrification", "efuel", "battery", "optimised_electrification", "diesel", "h2"]
SPFV_STANDI_METHOD = ["electrification", "efuel", "battery", "optimised_electrification", "diesel", "h2"]

### COST FACTORS
CO2_COST = 670

FACTOR_PLANNING = 0.18
MAINTENANCE_FACTOR = 0.014  # electrification
MAINTENANCE_FACTOR_FILLING_STATION = 0.03
# COST_OVERHEAD_ONE_TRACK = 1141  # Tausend Euro pro Kilometer
# COST_OVERHEAD_TWO_TRACKS = 2282  # Tausend Euro pro Kilometer
COST_CATENARY = 737  # Tausend Euro pro Kilometer
COST_TRACTION_POWER_SUPPLY = 200 # Tausend Euro pro Kilometer
COST_CIVIL_ENGINEERING_CONSTRUCTION = 200  # Tausend Euro pro Kilometer
COST_LAND_AQUISITOIN = 5  # Tausend Euro pro Kilometer
LIFETIME_CATENARY = 60  # Jahre
COST_CHARGING_STATION = 2582  # Tausend Euro
COST_SMALL_CHARGING_STATION = 1200  # Tausend Euro

ENERGY_COST_ELECTRO_CASUAL = 0.12
ENERGY_COST_ELECTRO_RENEWABLE = 0.14
ENERGY_COST_DIESEL = 0.75
ENERGY_COST_EFUEL = 2.5
ENERGY_COST_H2 = 5

ENERGY_CO2_ELECTRO_CASUAL = 414
ENERGY_CO2_ELECTRO_RENEWABLE = 21
ENERGY_CO2_DIESEL = 2774
ENERGY_CO2_EFUEL = 370
ENERGY_CO2_H2 = 938

ENERGY_POLLUTANTS_ELECTRO_CASUAL = 0.96
ENERGY_POLLUTANTS_ELECTRO_RENEWABLE = 0.05
ENERGY_POLLUTANTS_DIESEL = 6.57
ENERGY_POLLUTANTS_EFUEL = 6.57
ENERGY_POLLUTANTS_H2 = 2.18

ENERGY_PRIMARYENERGY_ELECTRO_CASUAL = 6
ENERGY_PRIMARYENERGY_ELECTRO_RENEWABLE = 4.5
ENERGY_PRIMARYENERGY_DIESEL = 38.9
ENERGY_PRIMARYENERGY_EFUEL = 78.2
ENERGY_PRIMARYENERGY_H2 = 198.7

UTILITY_POINT_PRIMARY_ENERGY = 0.9
UTILITY_TO_MONEY = 15.5

### durations
DURATION_PLANNING = 5
DURATION_BUILDING = 5
DURATION_OPERATION = 30

### cost road transport 40t Lkw
ROAD_ENERGY_ELECTRO_RENWEABLE_COST = 17.5  # €/100km
ROAD_PERSONAL_COST = 25.18  # €/100km angenommene Reisegeschwindigkeit 80 km/h
ROAD_CAPITAL_COST = 11.73  # €/100km
ROAD_MAINTENANCE_COST = 25.72  # €/100km
ROAD_CO2_ELECTRO_RENEWABLE_COST = 1.8  # €/100km
ROAD_PRIMARY_ENERGIE_ELECTRO_RENEWABLE_COST = 7.8  # €/100km
ROAD_EMISSION_ELECTRO_RENEWABLE_COST = 0.1  # €/100km nur Energiebereitstellung, keine Emissionen durch Radabrieb etc
PAYLOAD_TRUCK = 25  # t Nutzlast für Lkw. Damit angenommen: Zusätzliches Gewicht Batterie wird nicht negativ auf Nutzlast angerechnet

### wagon cargo rail
LENGTH_CONTAINER_WAGON = 19.7  # m
DEAD_WEIGHT_CONTAINER_WAGON = 20  # t
PAYLOAD_CONTAINER_WAGON = 70 # t
AVERAGE_SPEED_RESILIENCE = 60  # km/h für Ausweichrouten
COST_CONTAINER_WAGON = 1.06  # € pro Wagen-h
COST_TRAIN_DRIVER = 57  # € pro Stunde
TRAIN_PROVISION_COST_PER_WAGGON = 23  # € pro Wagen
DISTURBANCE_PERCENTAGE = 0.0463  # proportion of time where infrastructure is disturbed
#
##
CHARGE = 1200  # kWh