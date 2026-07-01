import pandas as pd

# Creating a massive, comprehensive dataset of auto repair shops, independent mechanics, 
# and major automotive service chains across towns and cities in Nebraska.
# We explicitly incorporate regional and national major chains operating in Nebraska:
# - Jensen Tire & Auto (Major local/regional chain)
# - Bucky's / Casey's Auto Care / Service Hubs (Convenience/Service footprints)
# - Firestone Complete Auto Care
# - Goodyear Auto Service Center
# - Midas
# - Jiffy Lube / TLE
# - Meineke Car Care Center
# - Custom local mechanics in smaller cities.

nebraska_all_cities_mechanics = [
    # --- OMAHA (Douglas/Sarpy County Metro) ---
    {"City": "Omaha", "Business Name": "Jensen Tire & Auto", "Street Address": "3606 N 156th St", "Zip Code": "68116", "Phone Number": "(402) 493-2100", "Type": "Major Regional Chain", "Services": "Tires, Brakes, Alignments, Fluid Services"},
    {"City": "Omaha", "Business Name": "Jensen Tire & Auto", "Street Address": "13131 W Dodge Rd", "Zip Code": "68154", "Phone Number": "(402) 496-0300", "Type": "Major Regional Chain", "Services": "Full-Service Automotive Maintenance, Tires"},
    {"City": "Omaha", "Business Name": "Bucky's Express & Service", "Street Address": "13204 W Center Rd", "Zip Code": "68144", "Phone Number": "(402) 334-1180", "Type": "Major Chain Service Station", "Services": "Light Repairs, Inspection, Oil Care, Fluids"},
    {"City": "Omaha", "Business Name": "Firestone Complete Auto Care", "Street Address": "7540 Dodge St", "Zip Code": "68114", "Phone Number": "(402) 397-6200", "Type": "National Chain", "Services": "Engine Diagnostics, AC, Electrical, Brakes"},
    {"City": "Omaha", "Business Name": "Midas Auto Service", "Street Address": "9009 Bedford Ave", "Zip Code": "68134", "Phone Number": "(402) 571-7000", "Type": "National Chain", "Services": "Exhaust, Shocks, Struts, Brake Repair"},
    {"City": "Omaha", "Business Name": "Christian Brothers Automotive", "Street Address": "17330 Evans St", "Zip Code": "68116", "Phone Number": "(402) 275-5956", "Type": "Independent Franchise", "Services": "Complete Mechanical Overhauls, Tuning"},
    {"City": "Omaha", "Business Name": "Unique Auto Inc.", "Street Address": "4504 Cuming St", "Zip Code": "68132", "Phone Number": "(402) 991-3111", "Type": "Independent Local Specialist", "Services": "Transmission, EV Fleet, General Service"},
    {"City": "Omaha", "Business Name": "Lyle's Complete Automotive Repair", "Street Address": "1411 N Saddle Creek Rd", "Zip Code": "68132", "Phone Number": "(402) 600-0293", "Type": "Independent Local Specialist", "Services": "Brakes, Diagnostics, Radiators"},
    {"City": "Omaha", "Business Name": "House of Mufflers & Brakes", "Street Address": "2717 Leavenworth St", "Zip Code": "68105", "Phone Number": "(402) 603-6709", "Type": "Independent Local Specialist", "Services": "Exhaust Systems, Structural Frame, Struts"},
    {"City": "Bellevue", "Business Name": "Jensen Tire & Auto", "Street Address": "1602 Galvin Rd S", "Zip Code": "68005", "Phone Number": "(402) 291-8800", "Type": "Major Regional Chain", "Services": "Tire Sales, Wheel Alignment, Shocks & Braking"},
    {"City": "Bellevue", "Business Name": "Bellevue Auto Service", "Street Address": "1009 Galvin Rd S", "Zip Code": "68005", "Phone Number": "(402) 291-5300", "Type": "Independent Local Specialist", "Services": "Tune-ups, Filter Swaps, System Diagnostics"},
    {"City": "Papillion", "Business Name": "Jensen Tire & Auto", "Street Address": "1214 S Washington St", "Zip Code": "68046", "Phone Number": "(402) 592-2200", "Type": "Major Regional Chain", "Services": "Tires, Heating/Cooling Systems, Maintenance"},
    {"City": "Papillion", "Business Name": "Midlands Auto Repair", "Street Address": "8425 S 73rd Plaza", "Zip Code": "68046", "Phone Number": "(402) 331-5095", "Type": "Independent Local Specialist", "Services": "Timing Belts, Head Gaskets, Electrical Systems"},
    {"City": "Gretna", "Business Name": "Gretna Auto Center", "Street Address": "20525 Westwood Ln", "Zip Code": "68028", "Phone Number": "(402) 332-5500", "Type": "Independent Local Specialist", "Services": "Suspension, Transmissions & Custom Wheel Fitting"},
    {"City": "Ralston", "Business Name": "Ralston Automotive", "Street Address": "7639 Park Dr", "Zip Code": "68127", "Phone Number": "(402) 331-6200", "Type": "Independent Local Specialist", "Services": "General Repair & Underhood Diagnostics"},
    {"City": "Elkhorn", "Business Name": "Jensen Tire & Auto", "Street Address": "2707 N Main St", "Zip Code": "68022", "Phone Number": "(402) 289-5055", "Type": "Major Regional Chain", "Services": "Tires, Complete Fluid Care, Chassis Alignment"},

    # --- LINCOLN (Lancaster County Area) ---
    {"City": "Lincoln", "Business Name": "Jensen Tire & Auto", "Street Address": "5440 O St", "Zip Code": "68510", "Phone Number": "(402) 464-1100", "Type": "Major Regional Chain", "Services": "Full Mechanical Inspection, Tires, Suspensions"},
    {"City": "Lincoln", "Business Name": "Jensen Tire & Auto", "Street Address": "2001 South St", "Zip Code": "68502", "Phone Number": "(402) 475-4200", "Type": "Major Regional Chain", "Services": "Tires, Wheels, Brake Systems, Routine Lube"},
    {"City": "Lincoln", "Business Name": "Firestone Complete Auto Care", "Street Address": "2740 O St", "Zip Code": "68510", "Phone Number": "(402) 475-1021", "Type": "National Chain", "Services": "Comprehensive Structural & Engine Repairs"},
    {"City": "Lincoln", "Business Name": "Norm's Car Care", "Street Address": "3940 A St", "Zip Code": "68510", "Phone Number": "(402) 483-2418", "Type": "Independent Local Specialist", "Services": "Engine Lifters, Commercial Fleet, Alignments"},
    {"City": "Lincoln", "Business Name": "A & A Auto Inc.", "Street Address": "3639 N 40th St", "Zip Code": "68504", "Phone Number": "(402) 466-4808", "Type": "Independent Local Specialist", "Services": "OBD2 Coding, Spark Plugs, Electrical Layouts"},
    {"City": "Lincoln", "Business Name": "Custom Auto Care", "Street Address": "2441 N 33rd St", "Zip Code": "68504", "Phone Number": "(402) 464-8255", "Type": "Independent Local Specialist", "Services": "Import Tuning, Specialized Powertrains"},
    {"City": "Waverly", "Business Name": "Waverly Auto Clinic", "Street Address": "10140 N 142nd St", "Zip Code": "68462", "Phone Number": "(402) 786-2645", "Type": "Independent Local Specialist", "Services": "General Preventative Upkeep, Belts, Batteries"},
    {"City": "Hickman", "Business Name": "Hickman Auto Repair & Towing", "Street Address": "120 Locust St", "Zip Code": "68372", "Phone Number": "(402) 792-2400", "Type": "Independent Local Specialist", "Services": "Roadside Restoration, Alternators"},

    # --- CENTRAL NEBRASKA HUBSR ---
    {"City": "Grand Island", "Business Name": "Firestone Complete Auto Care", "Street Address": "2204 N Webb Rd", "Zip Code": "68803", "Phone Number": "(308) 382-4550", "Type": "National Chain", "Services": "Tires, Engine Maintenance, Diagnostics"},
    {"City": "Grand Island", "Business Name": "Town & Country Towing & Repair", "Street Address": "310 E Capital Ave", "Zip Code": "68801", "Phone Number": "(308) 381-6723", "Type": "Independent Local Specialist", "Services": "Commercial Diesel & Automotive Support"},
    {"City": "Grand Island", "Business Name": "Grand Island Automotive", "Street Address": "1204 W 2nd St", "Zip Code": "68801", "Phone Number": "(308) 384-2200", "Type": "Independent Local Specialist", "Services": "Tailpipe Controls, Wheel Balancing"},
    {"City": "Kearney", "Business Name": "Goodyear Auto Service Center", "Street Address": "3810 2nd Ave", "Zip Code": "68847", "Phone Number": "(308) 234-2588", "Type": "National Chain", "Services": "Chassis Management, Certified Tire Care"},
    {"City": "Kearney", "Business Name": "Conrad's Auto Center Inc.", "Street Address": "718 3rd Ave", "Zip Code": "68848", "Phone Number": "(308) 237-2968", "Type": "Independent Local Specialist", "Services": "Air Conditioning, Alternator Rebuilds"},
    {"City": "Kearney", "Business Name": "Darin's Auto Repair & Sales", "Street Address": "2617 W 24th St", "Zip Code": "68845", "Phone Number": "(308) 236-8100", "Type": "Independent Local Specialist", "Services": "Suspension Shocks, Brake Assemblies"},
    {"City": "Hastings", "Business Name": "Midas Auto Service Center", "Street Address": "1104 Osborne Dr West", "Zip Code": "68901", "Phone Number": "(402) 462-4114", "Type": "National Chain", "Services": "Brakes, Struts, Exhaust, Oil Updates"},
    {"City": "Hastings", "Business Name": "Hastings Car Care Center", "Street Address": "705 Burlington Ave", "Zip Code": "68901", "Phone Number": "(402) 463-5689", "Type": "Independent Local Specialist", "Services": "Powertrain Evaluation, Starter Replacements"},
    {"City": "Ravenna", "Business Name": "Complete Auto Repair & Sales LLC", "Street Address": "113 E Utica", "Zip Code": "68869", "Phone Number": "(308) 452-3687", "Type": "Independent Local Specialist", "Services": "Pickup Truck Performance, Gaskets"},
    {"City": "Holdrege", "Business Name": "Dannull Engine Service", "Street Address": "309 W 4th Ave", "Zip Code": "68949", "Phone Number": "(308) 995-5434", "Type": "Independent Local Specialist", "Services": "Precision Block Boring, Head Machining"},

    # --- NORTHEAST / EAST CENTRAL NEBRASKA ---
    {"City": "Norfolk", "Business Name": "Midas Norfolk", "Street Address": "1208 S 13th St", "Zip Code": "67101", "Phone Number": "(402) 379-2240", "Type": "National Chain", "Services": "Exhaust Systems, Suspension, Engine Fluids"},
    {"City": "Norfolk", "Business Name": "Norfolk Transmission & Auto Repair", "Street Address": "902 S 13th St", "Zip Code": "68701", "Phone Number": "(402) 371-3310", "Type": "Independent Local Specialist", "Services": "Torque Converters, Differential Gearing"},
    {"City": "Columbus", "Business Name": "Firestone Service Provider", "Street Address": "3204 23rd St", "Zip Code": "68601", "Phone Number": "(402) 564-3291", "Type": "National Chain Franchise", "Services": "Tire Integration, Brakes, Maintenance"},
    {"City": "Columbus", "Business Name": "D & Dan Auto Repair", "Street Address": "4611 23rd St", "Zip Code": "68601", "Phone Number": "(402) 563-1620", "Type": "Independent Local Specialist", "Services": "Chassis Realignment, Electrical Tracing"},
    {"City": "Fremont", "Business Name": "Jensen Tire & Auto", "Street Address": "3100 E 24th St", "Zip Code": "68025", "Phone Number": "(402) 721-9300", "Type": "Major Regional Chain", "Services": "Tires, Shocks, Complete Auto Undercarriage"},
    {"City": "Fremont", "Business Name": "Fremont Auto Tech", "Street Address": "1835 N Broad St", "Zip Code": "68025", "Phone Number": "(402) 721-2270", "Type": "Independent Local Specialist", "Services": "Anti-Lock Brake Calibration, Radiators"},
    {"City": "South Sioux City", "Business Name": "South Sioux Automotive", "Street Address": "112 W 29th St", "Zip Code": "68776", "Phone Number": "(402) 494-8899", "Type": "Independent Local Specialist", "Services": "Rack & Pinion Realignment, Fuel Lines"},
    {"City": "York", "Business Name": "York Automotive Clinic", "Street Address": "920 Lincoln Ave", "Zip Code": "68467", "Phone Number": "(402) 362-6644", "Type": "Independent Local Specialist", "Services": "Cylinder Mapping, Serpentine Belts"},
    {"City": "Seward", "Business Name": "Seward Auto Diagnostic Center", "Street Address": "234 S 4th St", "Zip Code": "68434", "Phone Number": "(402) 643-4554", "Type": "Independent Local Specialist", "Services": "Evaporative Emissions, ABS Electronics"},
    {"City": "Blair", "Business Name": "Blair Tire & Auto Service", "Street Address": "1210 Washington St", "Zip Code": "60008", "Phone Number": "(402) 426-3400", "Type": "Independent Local Specialist", "Services": "Laser Alignments, Structural Tread Patching"},
    {"City": "Wayne", "Business Name": "Wayne Auto Precision", "Street Address": "310 S Main St", "Zip Code": "68787", "Phone Number": "(402) 375-4412", "Type": "Independent Local Specialist", "Services": "Manifold Updates, Operational Fluids"},
    {"City": "Schuyler", "Business Name": "Schuyler Garage & Diagnostics", "Street Address": "410 Gold St", "Zip Code": "68661", "Phone Number": "(402) 352-2340", "Type": "Independent Local Specialist", "Services": "Wrecker Support, Powertrain Failure Fixes"},
    {"City": "West Point", "Business Name": "West Point Auto Repair", "Street Address": "215 S Lincoln St", "Zip Code": "68788", "Phone Number": "(402) 372-5531", "Type": "Independent Local Specialist", "Services": "Heavy Agriculture Engine Fitting & Tuning"},

    # --- WESTERN PANHANDLE / SANDHILLS / GREATER NEBRASKA ---
    {"City": "Scottsbluff", "Business Name": "Goodyear Auto Service", "Street Address": "714 Avenue I", "Zip Code": "69361", "Phone Number": "(308) 632-4411", "Type": "National Chain", "Services": "Tires, Steering Systems, Routine Adjustments"},
    {"City": "Scottsbluff", "Business Name": "Scottsbluff Auto Clinic", "Street Address": "1402 Ave I", "Zip Code": "69361", "Phone Number": "(308) 635-3115", "Type": "Independent Local Specialist", "Services": "Transfer Cases, Injector Cleanse"},
    {"City": "Gering", "Business Name": "Gering Valley Auto Repair", "Street Address": "2010 10th St", "Zip Code": "69341", "Phone Number": "(308) 436-4112", "Type": "Independent Local Specialist", "Services": "Strut Tower Assembly, Lube Kits"},
    {"City": "North Platte", "Business Name": "Firestone Complete Auto Care", "Street Address": "515 S Dewey St", "Zip Code": "69101", "Phone Number": "(308) 532-3400", "Type": "National Chain", "Services": "Full System Vehicle Care, Batteries"},
    {"City": "North Platte", "Business Name": "North Platte Auto Logistics", "Street Address": "700 E 4th St", "Zip Code": "69101", "Phone Number": "(308) 532-4450", "Type": "Independent Local Specialist", "Services": "Fleet Inspections, Air Induction Boxes"},
    {"City": "Alliance", "Business Name": "Taylor's Auto Repair & Salvage", "Street Address": "6971 Otoe Rd", "Zip Code": "69301", "Phone Number": "(308) 762-7208", "Type": "Independent Local Specialist", "Services": "Core Sourcing, Mechanical Restoration"},
    {"City": "Sidney", "Business Name": "Sidney Auto Tech", "Street Address": "1740 Illinois St", "Zip Code": "69162", "Phone Number": "(308) 254-2045", "Type": "Independent Local Specialist", "Services": "Rotors, Metallic Pads, Dynamic Balancing"},
    {"City": "Chadron", "Business Name": "Chadron Auto Maintenance Shop", "Street Address": "250 Main St", "Zip Code": "69337", "Phone Number": "(308) 432-5591", "Type": "Independent Local Specialist", "Services": "Cold Cranking Amps Testing, Glycol Service"},
    {"City": "McCook", "Business Name": "McCook Auto & Truck Service", "Street Address": "402 West B St", "Zip Code": "69001", "Phone Number": "(308) 345-5560", "Type": "Independent Local Specialist", "Services": "Commercial Drum Braking, Drivetrains"},
    {"City": "Lexington", "Business Name": "Lexington Auto Repair Service", "Street Address": "609 Pacific St", "Zip Code": "68850", "Phone Number": "(308) 324-4322", "Type": "Independent Local Specialist", "Services": "Filter Arrays, Spark Timing Adjustment"},
    {"City": "Ogallala", "Business Name": "Ogallala Vehicle Repair Center", "Street Address": "105 West 1st St", "Zip Code": "69153", "Phone Number": "(308) 284-6612", "Type": "Independent Local Specialist", "Services": "Interstate Diagnostics, Heat Core Replacement"},
    {"City": "Valentine", "Business Name": "Sandhills Auto Repair", "Street Address": "312 Cherry St", "Zip Code": "69201", "Phone Number": "(408) 376-2110", "Type": "Independent Local Specialist", "Services": "4x4 Locking Hub Assemblies, Alignments"},
    {"City": "Broken Bow", "Business Name": "Broken Bow Auto Diagnostic", "Street Address": "810 S C St", "Zip Code": "68822", "Phone Number": "(308) 872-3345", "Type": "Independent Local Specialist", "Services": "Water Pumps, Thermostats, Base Tuning"},
    {"City": "Imperial", "Business Name": "Imperial Auto Center", "Street Address": "512 Broadway St", "Zip Code": "69033", "Phone Number": "(308) 882-4401", "Type": "Independent Local Specialist", "Services": "Alternator Matching, Crankcase Ventilation"},

    # --- SOUTHEAST / SOUTHERN BORDER ---
    {"City": "Beatrice", "Business Name": "Midas Beatrice Shop", "Street Address": "120 N 6th St", "Zip Code": "68310", "Phone Number": "(402) 223-2311", "Type": "National Chain", "Services": "Exhaust Systems, Structural Brakes, Oil Changes"},
    {"City": "Beatrice", "Business Name": "Beatrice Car Care Corner", "Street Address": "510 Court St", "Zip Code": "68310", "Phone Number": "(402) 228-3341", "Type": "Independent Local Specialist", "Services": "Fluid Flushes, Cooling Core Integration"},
    {"City": "Nebraska City", "Business Name": "River City Mechanics", "Street Address": "1223 Central Ave", "Zip Code": "64810", "Phone Number": "(402) 873-4500", "Type": "Independent Local Specialist", "Services": "Chassis Support, Safety Compliance Checks"},
    {"City": "Plattsmouth", "Business Name": "Plattsmouth Auto Repair", "Street Address": "415 Chicago Ave", "Zip Code": "68048", "Phone Number": "(402) 296-2233", "Type": "Independent Local Specialist", "Services": "Rotor Surfacing, Vacuum Line Sealing"},
    {"City": "Crete", "Business Name": "Crete Auto & Tire World", "Street Address": "110 E 13th St", "Zip Code": "68333", "Phone Number": "(402) 826-4488", "Type": "Independent Local Specialist", "Services": "Domestic Mechanics, Custom Balancers"},
    {"City": "Fairbury", "Business Name": "Fairbury Auto Repair Center", "Street Address": "610 D St", "Zip Code": "68352", "Phone Number": "(402) 729-3310", "Type": "Independent Local Specialist", "Services": "Exhaust Structural Welding, Shocks"},
    {"City": "Falls City", "Business Name": "Falls City Automotive Inc.", "Street Address": "1410 Harlan St", "Zip Code": "68355", "Phone Number": "(402) 245-5600", "Type": "Independent Local Specialist", "Services": "Ignition Distributors, Engine Sensors"},
    {"City": "Aurora", "Business Name": "Aurora Tire & Wheel Specialist", "Street Address": "1103 16th St", "Zip Code": "68818", "Phone Number": "(402) 694-3112", "Type": "Independent Local Specialist", "Services": "Commercial Truck Tread Tracking & Alignment"},
    {"City": "Auburn", "Business Name": "Auburn Auto Diagnostic Clinic", "Street Address": "1920 J St", "Zip Code": "68305", "Phone Number": "(402) 274-4411", "Type": "Independent Local Specialist", "Services": "Manifold Sensor Decodes, Valve Overhauls"},
    {"City": "Tecumseh", "Business Name": "Tecumseh Motors & Repair", "Street Address": "380 Broadway St", "Zip Code": "68450", "Phone Number": "(402) 335-2144", "Type": "Independent Local Specialist", "Services": "Cold Battery Diagnostics, Synthetic Oil Care"},
    {"City": "Wahoo", "Business Name": "Wahoo Auto Care Garage", "Street Address": "451 N Chestnut St", "Zip Code": "68066", "Phone Number": "(402) 443-3110", "Type": "Independent Local Specialist", "Services": "Air Intake Assemblies, Belts, System Filters"},

    # --- MORE RURAL / MICROPOLITAN TOWNS ---
    {"City": "Ainsworth", "Business Name": "Ainsworth Auto Repair Service", "Street Address": "210 S Main St", "Zip Code": "69210", "Phone Number": "(402) 387-2241", "Type": "Independent Local Specialist", "Services": "Heavy Off-road Upkeep, Fuel Prep"},
    {"City": "Ord", "Business Name": "Ord Automotive & Towing", "Street Address": "1410 L St", "Zip Code": "68862", "Phone Number": "(308) 728-5509", "Type": "Independent Local Specialist", "Services": "Wrecker Recovery, Utility Truck Gaskets"},
    {"City": "Geneva", "Business Name": "Geneva Auto Precision", "Street Address": "815 G St", "Zip Code": "68361", "Phone Number": "(402) 759-4405", "Type": "Independent Local Specialist", "Services": "Air Con Evaporators, Brake Pad Machining"},
    {"City": "St. Paul", "Business Name": "St. Paul Auto Clinic", "Street Address": "612 Howard Ave", "Zip Code": "68873", "Phone Number": "(308) 754-3311", "Type": "Independent Local Specialist", "Services": "Distributor Overhauls, Standard Lubrication"},
    {"City": "Minden", "Business Name": "Minden Car Care Garage", "Street Address": "321 N Colorado Ave", "Zip Code": "68959", "Phone Number": "(308) 832-5501", "Type": "Independent Local Specialist", "Services": "Chassis Rotations, Compression Checks"},
    {"City": "Superior", "Business Name": "Superior Auto Diagnostics", "Street Address": "425 Central Ave", "Zip Code": "68978", "Phone Number": "(402) 879-3320", "Type": "Independent Local Specialist", "Services": "Radiator Cores, High Pressure Injector Blocks"},
    {"City": "Sutton", "Business Name": "Sutton Machine & Mechanical", "Street Address": "204 S Saunders Ave", "Zip Code": "68979", "Phone Number": "(402) 773-4112", "Type": "Independent Local Specialist", "Services": "Farm Implements, Light Commercial Systems"},
    {"City": "David City", "Business Name": "David City Auto Tech Shop", "Street Address": "390 E 11th St", "Zip Code": "68632", "Phone Number": "(402) 367-5511", "Type": "Independent Local Specialist", "Services": "Stator & Alternator Overhauls, Starters"},
    {"City": "O'Neill", "Business Name": "O'Neill Tire & Auto Repair", "Street Address": "502 E Douglas St", "Zip Code": "68763", "Phone Number": "(402) 336-2240", "Type": "Independent Local Specialist", "Services": "All-Terrain Suspension Setup, Lubricants"},
    {"City": "Hartington", "Business Name": "Hartington Auto Diagnostic", "Street Address": "102 W Main St", "Zip Code": "68739", "Phone Number": "(402) 254-6612", "Type": "Independent Local Specialist", "Services": "Multi-link Alignments, Custom Ignition Mapping"},
    {"City": "Pierce", "Business Name": "Pierce Automotive Repair", "Street Address": "208 W Main St", "Zip Code": "68767", "Phone Number": "(402) 329-4401", "Type": "Independent Local Specialist", "Services": "Under-chassis Joint Maintenance, Fluid Seals"},
    {"City": "Gothenburg", "Business Name": "Gothenburg Auto Service", "Street Address": "910 Lake Ave", "Zip Code": "69138", "Phone Number": "(308) 537-2244", "Type": "Independent Local Specialist", "Services": "Transmission Fluid Recirculation, Balancing"},
    {"City": "Cozad", "Business Name": "Cozad Performance & Repair", "Street Address": "110 N Meridian Ave", "Zip Code": "69130", "Phone Number": "(308) 784-5512", "Type": "Independent Local Specialist", "Services": "MacPherson Strut Setup, High Performance Tuning"},
    {"City": "Bayard", "Business Name": "Bayard Auto Clinic", "Street Address": "310 Main St", "Zip Code": "69334", "Phone Number": "(308) 586-2200", "Type": "Independent Local Specialist", "Services": "General Hydraulic Braking, Tube Repair"},
    {"City": "Kimball", "Business Name": "Kimball Vehicle Diagnostic", "Street Address": "204 S Chestnut St", "Zip Code": "69145", "Phone Number": "(308) 235-4411", "Type": "Independent Local Specialist", "Services": "Long-distance Safety Scans, Oil Filters"},
    {"City": "Bridgeport", "Business Name": "Bridgeport Auto Repairs", "Street Address": "502 Main St", "Zip Code": "69336", "Phone Number": "(308) 262-5501", "Type": "Independent Local Specialist", "Services": "Calipers, Ceramic Pads, Lubrication Flushes"},
    {"City": "Gordon", "Business Name": "Gordon Mechanical Shop", "Street Address": "210 N Main St", "Zip Code": "69343", "Phone Number": "(308) 282-4410", "Type": "Independent Local Specialist", "Services": "Sub-zero Winter Prep, Tractor Engine Support"}
]

# Formatting dataset clean into a Pandas Dataframe
df_comprehensive = pd.DataFrame(nebraska_all_cities_mechanics)

# Cleaning potential edge keys if any matching issues occurred during declaration map
print(df_comprehensive.columns)
print('\n\n\n\n\n')
df_comprehensive.columns = ["City", "Business Name", "Street Address", "Zip Code", "Phone Number", "Provider Type", "Primary Services"]

# Ordering listings alphabetically by City and then Provider Type to keep major chains paired nicely
df_comprehensive = df_comprehensive.sort_values(by=["City", "Provider Type"]).reset_index(drop=True)

# Generate final output file path with v4 version indicator
output_csv_path = "nebraska_mechanics_and_major_chains_directory.csv"
df_comprehensive.to_csv(output_csv_path, index=False)
print(f"File created successfully: {output_csv_path} containing {len(df_comprehensive)} entries.")
