from Tonga_functions import tephra_cleanup_volume_from_place


## Running the ash modelling using OSM data
place = "Tongatapu" #name of place to be modelled
Scenario_num = 3   # Number of scenarios to be modelled
min_thickness_scenarios = [1, 20, 30] # Minimum thickness for each scenario to be modelled
max_thickness_scenarios = [10, 30, 60] # Maximum thickness for each scenario to be modelled
surfaces_of_interest = ["all", "roads", "roofs"] # Surfaces to be modelled
scenario_names = ["1-10mm", "20-30mm", "30-60mm"] # Names of scenarios to be modelled
Exp_data = ['OSM', 'ABD']

# loop through the scenarios
for i in Exp_data: # loop through the exposure datasets
    Exposure = i
    print("Exposure dataset:", Exposure)
    for j in range(Scenario_num): # loop through the scenarios
        min_thickness = min_thickness_scenarios[j]
        max_thickness = max_thickness_scenarios[j]
        for k in surfaces_of_interest: # loop through the surfaces of interest
            surfaces = k
            scenario = str(min_thickness) + "-" + str(max_thickness) + "mm_" + surfaces + "_" + Exposure
            fig = False
            csv = True
            print(scenario)
            Tongatapu_cleanup = tephra_cleanup_volume_from_place(place, Exposure, min_thickness, max_thickness, surfaces,
                                                                 scenario, fig, csv)



