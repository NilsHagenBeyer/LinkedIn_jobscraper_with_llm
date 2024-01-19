#%%
import webscraper as w
import os
from IPython.display import display

job_url='https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}'
url_template = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId={geo_id}&distance={distance}&f_E={level}&f_WT={employment_type}&start="


'''
#################################################################################################################################
This project aims to simplifly and automate the job search on LinkedIn. As a programmer the number of job offers can be overwhelming
and its ineficcient to read 100+ job descriptions to find the right job. This project aims to solve this problem by scraping the job
offers and compare the job descriptions with your formulated preferences, by utilizing chatGPTs API.

### HOW TO USE ###
1. Create your vita and system input for the language model
2. Set your query settings
3. Run the code


1) Create your vita and system input for the language model

    - Create a text file with your vita and save it in the same folder as this file:            vita.txt
    - Create a text file with your system input and save it in the same folder as this file:    system.txt
   
    There are example files for both files in this folder. You can use them as a template.
    Note that the language you use may affect the results of the language model, so I recommend to use the same language as the linkedIn is in your country.
    Also note that the script expects from the language model a response in the format: "Ranking: <your ranking> Comment: <your short explanation>"


2) Set your query settings

    Create a list of settings dictionaries. Each dictionary represents a search query.
    To extract or check your inputs, go to the link in a private browser window:

    https://www.linkedin.com/jobs/search/?currentJobId=3272687552&f_WT=2&refresh=true&ref=nubela.co

    Then set your query settings for one query. Copy the contents of the following parameters into a dictionary:

    get the stings for 
    keywords:           &keywords=<your keywords>
    location:           &location=<your location>
    geo_id:             &geoId=<your geo id>
    distance            &distance=<your distance>
    level:              &f_E=<level filter tag>
    employment_type:    &f_WT=<employment type filter tag>

    For example:
    settings_list = [
        {"keywords": "Python+(Programmiersprache)", 
            "location": "Karlsruhe%2C+Baden-Württemberg%2C+Germany", 
            "geo_id": "106523486"},
    ]

    You also can set a filter dictionary. The filter dictionary contains the filter tag as key and a list of filter options as value.

    For example: 
    filter = {"Seniority level": ["Associate", "Entry level"]}

3) Run the code

    Run the simple_search function with the target urls and the job url. The job url is the url to the job description like:

    ---------------------------------------------------------------------------------------------------
    job_df = w.simple_search(target_urls, job_url, filter, number_of_jobs=100, do_max=None)
    ---------------------------------------------------------------------------------------------------

    target_urls:        List of urls to scrape to search multiple query options. You can create this list with the create_target_url_list function.

    job_url:            Url to the job description. The Url points to LinkedIn's job description API endpoint. You can adjust it if needed at the top of this file.
                        You can also adjust the url template at the top of this file, if needed. But this is only necessary if LinkedIn changes the url structure.

    filter:             Dictionary of filter tags and filter options. You can set this to None if you don't want to filter the results.
    
    number_of_jobs:     Number of jobs found in each query. You can enter the max number of jobs found for one query.
                        This cuts the runtime when you have not a lot of jobs for each query.
                        If you expect many job results for a query you can set this to a higher number

    do_max:             Only for testing purposes. If you want to test the code, you can set this to a low number, for deployment set to None.
                        The script will stop requesting job descriptions after the do_max threshold is reached.

    
    The Results are saved in a csv file in the same folder as this file.

##################################################################################################################################
'''


query_list = [
    {   # keyword: Python in Karlsruhe, no employment type filter
        "keywords": "Python+(Programmiersprache)", 
        "location": "Karlsruhe%2C+Baden-Württemberg%2C+Germany", 
        "geo_id": "106523486",
        "distance": "10",
    },
    {   # keyword. Python in Germany only remote
        "keywords": "Python+(Programmiersprache)", 
        "location": "Germany", 
        "geo_id": "101282230",
        "employment_type": "2",
    },
    {   # keyword: machine learning in Karlsruhe, no employment type filter
        "keywords": "Maschinelles+Lernen", 
        "location": "Karlsruhe%2C+Baden-Württemberg%2C+Germany", 
        "geo_id": "106523486",
        "distance": "10",
    },
    {   # keyword. machine learning in Germany only remote
        "keywords": "Maschinelles+Lernen", 
        "location": "Germany", 
        "geo_id": "101282230",
        "employment_type": "2",
    },

]

filter = {"Seniority level": ["Associate", "Entry level"]}
# create list of urls to scrape for each query
target_urls = w.create_target_url_list(query_list, url_template)
# scrape jobs
job_df = w.simple_search(target_urls, job_url, filter, number_of_jobs=400, do_max=None)

#%% 
# display jobs dataframes
display(job_df)
# save job_df to csv
if not os.path.exists("outputs/jobs.csv"):
    os.mkdir("outputs")
job_df.to_csv("outputs/jobs.csv", index=False, sep=";")