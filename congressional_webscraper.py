from bs4 import BeautifulSoup
import requests
import lxml
import pandas as pd
import re
import argparse
import logging

parser = argparse.ArgumentParser(description='Helpful description here')
parser.add_argument('--html_file', type=str, help="Path to html input file", required=True)
parser.add_argument('--year', type=str, help="Congressional year", required=True)
args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s -  %(levelname)s -  %(message)s')
# logging.disable(logging.CRITICAL)     # <-- Uncomment to disable logging.

def getQuery(html_file):
    """ Function to open and scrape an html file. Returns a search query.
        Args:
            html_file: The html file for input passed in from the command line.
        Returns:
            search_results: The bs4.object.
    """
    logging.info("Getting query.")
    HTMLFileToBeOpened = open(html_file, "r", encoding="utf8")
    contents = HTMLFileToBeOpened.read()
    soup = BeautifulSoup(contents, 'lxml')
    HTMLFileToBeOpened.close()
    search_results = soup.find_all('table', attrs={"class":"multicol", "role":"presentation", "style":"border-collapse: collapse; padding: 0; border: 0; background:transparent; width:100%;"})
    return search_results


def parseRepresentatives(states, reps, group):
    """ Function to parse through two dictionaries containing congressional data. Returns a dictionary.
        Args:
            states: bs4.object containing a list of states.
            reps: bs4.oject containing congressional member information.
            group: Value to list as either Senate or House.
        Returns:
            return_dict: A dictionary object where the keys are U.S. States and the Values are congressional member information.
    """
    logging.info("Parsing representatives.")
    suffix_list = ['jr','jr.','sr','sr.','i','ii','iii','iv','v']       # Not an all encompassing list. May need amending later.
    return_dict = {}
    for state,rep in zip(states,reps):
        current_state = state.text.split("[")[0]
        placeholder_list = []
        for r in rep.find_all('dd'):
            suffix = False
            tmp_list = re.sub('▌\s?\d{0,2}\.?\s?(At-Large)?(At Large)?\.?\s?', '', r.text.strip(), flags=re.IGNORECASE).split(")")[0].split()
            # First_Name (req.), Middle_Name (opt., 0+), Last_Name (req.), Suffix (opt.), Party (req.).
            if tmp_list[-2].lower() in suffix_list:
                suffix = True
            
            # Whether Suffix is present.
            if suffix == True:
                # First_Name, Last_Name, Suffix, Party
                if (len(tmp_list) == 4):
                    tmp_list.insert(1,"") # Blank Middle_Name
                    tmp_list.insert(0, group) # group = Senate OR House
                    tmp_list[-1] = tmp_list[-1].lstrip("(")
                    placeholder_list.append(tmp_list.copy())
                
                # First_Name, Middle_Names (1+), Last_Name, Suffix, Party
                elif (len(tmp_list) >= 5):
                    middle_names = " ".join(tmp_list[1:-3])
                    del tmp_list[1:-3]
                    tmp_list.insert(1, middle_names)
                    tmp_list.insert(0, group) # group = Senate OR House
                    tmp_list[-1] = tmp_list[-1].lstrip("(")
                    placeholder_list.append(tmp_list.copy())
                else:
                    logging.error("Error: " + str(tmp_list))
                    
            else:
                # First_Name, Last_Name, Party
                if (len(tmp_list) == 3):
                    tmp_list.insert(-1,"") # Blank Suffix
                    tmp_list.insert(1,"") # Blank Middle_Name
                    tmp_list.insert(0, group) # group = Senate OR House
                    tmp_list[-1] = tmp_list[-1].lstrip("(")
                    placeholder_list.append(tmp_list.copy())
                
                # First_Name, Middle_Name (1+), Last_Name, Party
                elif (len(tmp_list) >= 4):
                    tmp_list.insert(-1,"") # Blank Suffix
                    middle_names = " ".join(tmp_list[1:-3])
                    del tmp_list[1:-3]
                    tmp_list.insert(1, middle_names)
                    tmp_list.insert(0, group) # group = Senate OR House
                    tmp_list[-1] = tmp_list[-1].lstrip("(")
                    placeholder_list.append(tmp_list.copy())
                
                else:
                    logging.error("Error: " + str(tmp_list))
                
        return_dict[current_state] = placeholder_list.copy()
    return return_dict


def getRepresentatives(search_query):
    """ Function to get congressional datasets from a bs4.object search query. Returns two dictionaries, each with information for both chambers of congress.
        Args:
            search_query: A bs4.object search query.
        Returns:
            State_Senators: A dictionary with information of senators, where the keys are U.S. States and the Values are congressional member information.
            State_house_reps: A dictionary with information of house representatives, where the keys are U.S. States and the Values are congressional member information.
    """
    logging.info("Getting representatives.")
    states = search_query[0].find_all('h4')
    
    # United States Senators
    senators = []
    for x in search_query[0].find_all('td'):
        for y in x.find_all("dl", recursive=False):
            senators.append(y)
    #print(senators)
    
    State_Senators = parseRepresentatives(states, senators, "Senate")
    
    # United States House Representatives
    house_reps = []
    for x in search_query[1].find_all('td'):
        for y in x.find_all("dl", recursive=False):
            house_reps.append(y)
            
    State_house_reps = parseRepresentatives(states, house_reps, "House")
    
    return State_Senators, State_house_reps


def getCongressionalDataset(State_Senators, State_house_reps, Congressional_year):
    """ A function to create a congressional dataset in csv format.
        Args:
            State_Senators: A dictionary with information of senators, where the keys are U.S. States and the Values are congressional member information.
            State_house_reps: A dictionary with information of house representatives, where the keys are U.S. States and the Values are congressional member information.
            Congressional_Year: The argument passed in the command line to add as a column in the dataset and to use in naming the output file.
        returns:
            None
    """
    logging.info("Now creating dataset.")
    senate_temp_df = pd.DataFrame(Senate_dict.items(), columns=["State","Info"]).explode("Info").reset_index(drop=True)
    house_temp_df = pd.DataFrame(House_dict.items(), columns=["State","Info"]).explode("Info").reset_index(drop=True)
    #Congressional_df = senate_temp_df.append(house_temp_df, ignore_index=True)     # <-- Will be depreciated soon.
    Congressional_df = pd.concat([senate_temp_df,house_temp_df], ignore_index=True)
    
    chamber = []
    First_Name = []
    Middle_Name = []
    Last_Name = []
    Suffix = []
    Party = []


    for index,row in Congressional_df.iterrows():
        chamber.append(row[1][0])       # Chamber of Congress (House or Senate)
        First_Name.append(row[1][1])    # First name
        Middle_Name.append(row[1][2])   # Middle name (Opt.)
        Last_Name.append(row[1][3])     # Last name
        Suffix.append(row[1][4])        # Suffix (Opt.)
        Party.append(row[1][5])         # Party affilication


    Congressional_df["Chamber"] = chamber
    Congressional_df["First_Name"] = First_Name
    Congressional_df["Middle_Name"] = Middle_Name
    Congressional_df["Last_Name"] = Last_Name
    Congressional_df["Suffix"] = Suffix
    Congressional_df["Party"] = Party

    Congressional_df.drop(columns=["Info"], inplace=True)
    Congressional_df = Congressional_df[["Chamber","State","First_Name","Middle_Name","Last_Name","Suffix","Party"]]
    Congressional_df["Congressional_Year"] = [Congressional_year for i in range(Congressional_df.shape[0])]
    
    # Determining ordinallity.
    if Congressional_year.endswith("1"):
        ordinal = "st"
    elif Congressional_year.endswith("2"):
        ordinal = "nd"
    elif Congressional_year.endswith("3"):
        ordinal = "rd"
    else:
        ordinal = "th"
    
    # Write to csv.
    Congressional_df.to_csv(f"{Congressional_year}{ordinal}_Congressional_dataset.csv",index=False)
    logging.info("Dataset Created: " + f"{Congressional_year}{ordinal}_Congressional_dataset.csv")



if __name__ == "__main__":
    logging.info("Start of program.")
    assert type(args.html_file) == str, 'args.html_file datatype needs correcting! Should be string!'
    assert type(args.year) == str, 'args.year datatype needs correcting! Should be string!'
    
    search_results = getQuery(args.html_file)
    Senate_dict,House_dict = getRepresentatives(search_results)
    getCongressionalDataset(Senate_dict, House_dict, args.year)
