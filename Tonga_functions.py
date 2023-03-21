import osmnx as ox
import pandas as pd
import geopandas as gpd
import random
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import shutil
import glob
import os
import requests

# Tephra cleanup functions

def tephra_cleanup_volume_from_place (place, Exposure, min_thickness, max_thickness, surfaces, scenario, fig, csv):
    """
    This function will estimate the volume of tephra requiring removal as part of municipal clean-up efforts.
    The function requires the name of the place and the thickness of tephra in mm. The user can specifiy whether a
    graph and csv file is produced with the model results.

        Arguments:
            place (str): Name of the place for OSMnX to search the OSM database and collect the exposure data
            thickness (float): Thickness of tephra in mm to model across the urban area of interest
            fig (Bool): Defines whether a graph is produced and saved of the model results (True) or not (False)
            csv (Bool): Defines whether a csv file is generated that contains the model results (True) or not (False)
        Returns:
             Volume (Dict): Returns a Dictionary of model results at the 5th, 50th, and 95th percentile for the volume
             of tephra removal required in cubic metres
    """
    scenario = scenario
    ox.config(timeout=2000)
    print("Initiating tephra clean-up model for ", place)
    substring = ","
    if place.find(substring) != -1:
        place_name_initial = place[:place.index(",")]
        place_name = place_name_initial.replace(" ", "")
        place_name_save = place_name.replace(" ", "_")
    else:
        place_name = place
        place_name_save = place_name.replace(" ", "_")
    directory = os.path.dirname(os.path.abspath(__file__))
    Geospatial_dir = directory + "/Geospatial_data/" + place_name_save
    if not os.path.exists(Geospatial_dir):
        os.makedirs(Geospatial_dir)
        print("Geospatial folder has been created")
    else:
        print("Geospatial folder already exists")
    if Exposure == "OSM":
        print("Obtaining building footprints from OSM.")
        if not os.path.exists(Geospatial_dir+"/"+ place_name_save + "_buildings.gpkg"):
            for attempt in range(10):
                try:
                    try:
                        buildings = ox.geometries_from_place(place, tags={"building": True}, which_result=None,
                                                             buffer_dist=None)
                        break
                    except (TypeError, ValueError, KeyError):
                        print("OSMnX may not be able to find place. "
                              "Try using the tephra_cleanup_from_address function instead")
                        exit()

                except requests.exceptions.ReadTimeout:
                    print("Timeout")
            print("Reprojecting buildings to UTM")
            FP_area_UTM = ox.projection.project_gdf(buildings, to_crs=None, to_latlong=False)
            print("Calculating footprint area.")
            FP_area_UTM["area"] = FP_area_UTM['geometry'].area
            fp_area = FP_area_UTM['area'].sum()
            print("Saving building footprints to disk")
            print("Total building footprint area is: ", fp_area)
            FP_area_UTM[['area', 'geometry']].to_file(
                "Geospatial_data/" + place_name_save + "/" + place_name_save + "_buildings.gpkg", driver="GPKG",
                encoding='UTF-8')

            print("Building footprints obtained, now obtaining roads from OSM.")

        else:
            print ("Buildings already exist")
            FP_area_UTM = gpd.read_file(
                "Geospatial_data/" + place_name_save + "/" + place_name_save + "_buildings.gpkg")

        if not os.path.exists(Geospatial_dir+"/"+ place_name_save + "_roads.gpkg"):
            try:
                roads = ox.graph_from_place(place, network_type='drive')
            except (TypeError, ValueError, KeyError):
                print(
                    "OSMnX may not be able to find location using from_place. "
                    "Try using the tephra_cleanup_from_address instead")
                exit()
            print("reprojecting roads to UTM")
            road_UTM = ox.project_graph(roads)
            print("saving roads locally")
            ox.io.save_graph_geopackage(road_UTM,
                                        "Geospatial_data/" + place_name_save + "/" + place_name_save + "_roads.gpkg",
                                        encoding='UTF-8')
            print("Roads save locally")
            road_UTM = gpd.read_file("Geospatial_data/" + place_name_save + "/" + place_name_save + "_roads.gpkg",
                                               layer='edges')
        else:
            print("roads already exist")
            road_UTM = gpd.read_file("Geospatial_data/" + place_name_save + "/" + place_name_save + "_roads.gpkg",
                                     layer='edges')

    else:
        road_UTM = gpd.read_file(Geospatial_dir + "/" + "Tongatapu_roads_ADB_paved_only.gpkg")
        FP_area_UTM = gpd.read_file(Geospatial_dir + "/" + "Tongatapu_buildings_ADB.gpkg")
        FP_area_UTM["area"] = FP_area_UTM['geometry'].area

    print("Estimating road area")
    if Exposure == "OSM":
        road_UTM["area"] = road_UTM['length']*3
        road_area = road_UTM['area'].sum()
    else:
        road_UTM["area"] = road_UTM["Length"] * 3
        road_area = road_UTM['area'].sum()
    print("Estimating impervious surface area based on road area")
    impervious_area = road_area
    print("Estimating building footprint area")
    fp_area = FP_area_UTM['area'].sum()
    all_area = road_area + fp_area + impervious_area

    # ---------- Cleanup model thresholds ----------
    print("Initiating clean-up modelling for", place)
    print("Maximum tephra thickness for", place, "is:", max_thickness, "mm. Minimum  thickness is:",
          min_thickness)
    #####
    #####
    # Clean-up thresholds
    print("Determining the appropriate clean-up threshold to use.")
    if surfaces == "all":
        if max_thickness >= 1000:
            cleanup_area_min = all_area - (all_area * 0.1)
            cleanup_area_max = all_area + (all_area * 0.1)
        elif max_thickness >= 10:
            cleanup_area_min = (road_area - (road_area * 0.1)) + (impervious_area - (impervious_area * 0.1)) + (
                    fp_area - (fp_area * 0.1))
            cleanup_area_max = (road_area + (road_area * 0.1)) + (impervious_area + (impervious_area * 0.1)) + (
                    fp_area + (fp_area * 0.1))
        elif max_thickness >= 0.5:
            cleanup_area_min = road_area - (road_area * 0.1)
            cleanup_area_max = road_area + (road_area * 0.1)
        elif max_thickness < 0.5:
            cleanup_area_min = 0
            cleanup_area_max = 0
    elif surfaces == "roads":
        cleanup_area_min = road_area - (road_area * 0.1)
        cleanup_area_max = road_area + (road_area * 0.1)
    elif surfaces == "roofs":
        cleanup_area_min = fp_area - (fp_area * 0.1)
        cleanup_area_max = fp_area + (fp_area * 0.1)

    # --- Monte Carlo analysis ---
    Thickness = []
    Area = []
    Volume = []
    # Dollars=[]
    # Duration=[]

    N = 10000
    print("Calculating tephra volume requiring clean-up.")
    for i in range(N):
        DThickness = ((random.uniform((min_thickness), (max_thickness)) / 1000))
        DArea = (random.uniform((cleanup_area_min), (cleanup_area_max)))
        DVolume = (DArea * DThickness)
        # DDollars =((random.randint(Min_cost_per_m3, Max_cost_per_m3)*DVolume)/1000)
        # DDuration =((DVolume/(random.randint(Min_truck_size_m3, Max_truck_size_m3)))*
        # (random.randint(Min_disposal_time_mins,Max_disposal_time_mins)/(random.randint(Min_trucks, Max_trucks)))/
        # (random.randint(Min_hrs_day, Max_hrs_day)*60))

        Thickness = Thickness + [DThickness]
        Area = Area + [DArea]
        Volume = Volume + [DVolume]
        # Dollars=Dollars+[DDollars]
        # Duration=Duration+[DDuration]

    num_bins = 50

    df = pd.DataFrame(Volume)
    print(df.describe())

    Percentile_50 = stats.scoreatpercentile(Volume, 50)
    Percentile_10 = stats.scoreatpercentile(Volume, 10)
    Percentile_90 = stats.scoreatpercentile(Volume, 90)
    CleanUpVolume = pd.DataFrame([[place, Percentile_10, Percentile_50, Percentile_90]],
                                 columns=["Place",
                                          "10th Percentile",
                                          "50th Percentile",
                                          "90th Percentile"])
    print(CleanUpVolume)
    df_volume_list = pd.DataFrame(Volume, columns=["Volume"])
    df_volume_list.to_csv("Results/temp/" + place_name_save + "_raw_" + scenario + ".csv", index=False)
    if csv==True:
        path_csv = "Results/" + place + "_" + ".csv"
        CleanUpVolume.to_csv(path_csv, index=False)
        path_temp = "Results/temp/" + place_name_save + "_" + scenario + ".csv"
        CleanUpVolume.to_csv(path_temp, index=False)
    else:
        print("No csv will be produced because csv=False. If you want a csv, make csv=True")

    # --- plotting the results ---
    if fig == True:
        if cleanup_area_min > 0:
            fig1 = plt.figure(figsize=(8, 8))

            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(np.sort(Volume), np.linspace(0.0, 1.0, len(Volume)))
            plt.xlabel('Volume [$m^3$]')
            plt.ylabel('Cumulative density function')
            plt.yticks([0, 0.25, 0.5, 0.75, 1])
            # ax1.axvspan(15000, 45000, alpha=0.5, color='gray')
            ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            plt.show()

            # fig1.savefig(City_dir + "/" + place + '_volume.png', transparent=True, dpi=300,
            #              bbox_inches='tight')
            #plt.close()
        else:
            print("No ash expected to require removal. No graph will be made")
    else:
        print ("No figure will be produced because fig=False. If you want a figure make fig=True")

    return()


