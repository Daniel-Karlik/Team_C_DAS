# Functions for scraping data from hlidacstatu.cz and saving scraped data

# Loading packages for data scraping
import urllib.request as urllib2
import ssl
import json
import pickle # For saving data in pickle format - much more memory efficient than json

# Loading packages for constructing path to file
import os.path

# Loading packages for operation with dates
import datetime
from dateutil.relativedelta import relativedelta

### Section of user defined variables ----------------------

# Define datasets to get data from
datasets = ["vyjadreni-politiku", "stenozaznamy-psp", "tiskove-konference-vlady"]
# "vyjadreni-politiku" -> statements of politicians from Twitter, Facebook, Youtube
# "stenozaznamy-psp" -> shorthand records of the Chamber of Deputies (Czech: stenozáznamy poslanecké sněmovny)
# "tiskove-konference-vlady" -> records of press conferences of the government of the Czech Republic

# Select which datasets you want to download
# Index of each value in dataset_download corresponds to index of name of dataset in datasets list
dataset_download = [1]  # E.g. if you want to download only dataset 0 and 2 select [0,2]

# Define starting year for each dataset from which you want to download the records.
# Index of each value in year_of_oldest_record corresponds to index of name of dataset in datasets list
# Set equal to "NA" if you want to get all the data.
# Note: Size of datasets are as follows
#       1. stenozaznamy-psp -> largest dataset
#       2. vyjadreni-politiku -> medium size
#       3. tiskove-konference-vlady -> small dataset

years_of_oldest_record = ["NA", 2021, "NA"]

# Define name of relative path for saving data
path = "data"
# If relative path doesn't exist create it
if not os.path.exists(path):
    os.makedirs("data")

# Getting authorization token
with open(os.path.join("Access_token", "Token_info.json")) as infile:
    authorization = json.load(infile)
Authorization_token = authorization["Authorization token"]

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'{Authorization_token}'  # Token loaded from json file
}
### ---------------------------------------------------------

# Creating unverified ssl context because it doesn't work otherwise, this is not a good solution as it introduces
# exposure to Man In the Middle attacks
# Note: Need to revise this later
ssl._create_default_https_context = ssl._create_unverified_context


def data_scraper(dataset, year_of_oldest_record):
    # Input:
    #       dataset - string with name of dataset to download
    #       years_of_oldest_record - number representing year of the oldest record we want to download
    #                                or "NA" string to download full dataset
    # Output:
    #       Downloaded data from HlidacStatu.cz API in format of python dictionary

    # Request to url with data is divided into pages, where maximum number of pages is 200. If number of requested
    # records surpasses 200 pages, they are truncated, this means we cannot simply request full dataset from the url.
    # We circumvent this by sequentially getting data from url for each day.
    # Note: Getting data for each month was considered, but in case of vyjadreni-politiku dataset, the number of entries
    #       exceed 200 pages.

    ### Getting date of most recent record and year of oldest record

    request = urllib2.Request(
            f'https://api.hlidacstatu.cz/api/v2/datasety/{dataset}/hledat?dotaz=datum%3A[*+TO+{datetime.date.today()}]&strana=1&sort=datum&desc=1',

        headers=headers)  # Requesting first page of results ordered from the latest date
    response_body = json.load(urllib2.urlopen(request))  # Request returns json type, loading json
    # Getting the latest date from data and adding +1 day to it
    # this is done because of format of request to url
    # e.g. request for date 12-10-2022 - 13-10-2022 will get data for date 13-10-2022
    date_right = datetime.datetime.strptime(response_body["results"][1]["datum"][:10],
                                            "%Y-%m-%d").date() + relativedelta(days=1)
    # Subtracting one day from right bound to receive left bound
    date_left = date_right + relativedelta(days=-1)

    # If statement tests if there is user defined limit to the oldest record if not then get it from the data
    if year_of_oldest_record == "NA":
        # Requesting first page of results ordered from the oldest date
        request = urllib2.Request(
            f'https://api.hlidacstatu.cz/api/v2/datasety/{dataset}/hledat?dotaz=datum%3A[*+TO+{datetime.date.today()}]&strana=1&sort=datum&desc=0',
            headers=headers)
        response_body = json.load(urllib2.urlopen(request))  # Request returns json type, loading json

        # Getting the oldest year of data entry
        year_of_oldest_record = datetime.datetime.strptime(response_body["results"][1]["datum"][:10], "%Y-%m-%d").year

    ### Getting data
    # Initializing dictionary for saving downloaded data
    data = {"results": []}

    # While date of right bound is bigger than year_of_oldest_record from data/set by user, download data
    while date_right.year >= year_of_oldest_record:
        # Getting data sequentially for each day and each page
        page = 0
        while True:
            # Incrementing number of pages
            page += 1
            # Requesting data from HlidacStatu.cz in time window defined by interval <date_left, date_right} (this means excluding right bound) and from
            # page defined in page
            request = urllib2.Request(
                f'https://api.hlidacstatu.cz/api/v2/datasety/{dataset}/hledat?dotaz=datum%3A[{date_left}+TO+{date_right}' + '}' + f'&strana={page}&sort=datum&desc=',
                headers=headers)
            response_body = json.load(urllib2.urlopen(request))  # Request returns json type, loading json

            # If results in response body is empty: break
            if response_body["results"] == []:
                break
            # Adding results of response_body to data
            data["results"] += response_body["results"]

        # Moving date window back in time by one day
        date_right = date_right + relativedelta(
            days=-1)  # Moving right bound by one day
        date_left = date_left + relativedelta(
            days=-1)  # Moving left bound by one day
    return data


def saving_data(data, file_name, path):
    # Input:
    #       data - python dictionary with downloaded data
    #       file_name - name of the file to be saved
    #       path - relative path to the folder that file is to be saved to
    # Output:
    #       None

    # Writing sample data to pickle file format
    file_name = file_name.replace("-", "_")  # Replace - with _ if there are any
    # This is set up, so you can use dataset string as name of the output file
    output_file_name = os.path.join(path, f'{file_name}.pickle')  # Adding file name to the path of saving files
    with open(output_file_name, "wb") as outfile:
        pickle.dump(data, outfile, protocol=pickle.HIGHEST_PROTOCOL) # Saving data in picke format,
                                                                     # using highest protocol which is version 5 and was introduced in python 3.8
def date_range(start, end, intv):
    start = datetime.strptime(start,"%Y%m%d")
    end = datetime.strptime(end,"%Y%m%d")
    diff = (end  - start ) / intv
    for i in range(intv):
        yield (start + diff * i).strftime("%Y%m%d")
    yield end.strftime("%Y%m%d")


for i in dataset_download:
    data = data_scraper(datasets[i], years_of_oldest_record[i])
    # Saving data from downloaded dataset
    saving_data(data, datasets[i], path)
