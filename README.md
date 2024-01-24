# LinkedIn Jobscraper with chatGPT

This project is based on the following project: 

https://github.com/llorenspujol/linkedin-jobs-scraper


# LinkedIn Job Search Automation

This project aims to simplify and automate the job search on LinkedIn by scraping job offers and comparing the job descriptions with your formulated preferences, utilizing chatGPT's API.

## How To Use 

Follow the steps below to use this project.

### 1. Create your vita and system input for the language model


- Create a text file with your vita and save it in the same folder as this file named `vita.txt`.

- Create a text file with your system input and save it in the same folder as this file named `system.txt`.

- Create a text file with your chatGPT API key and save it in the same folder as this file named `api_key.txt`.

Example files for both are included in this folder. You can use them as a template. Note that the language you use may affect the results of the language model, so it is recommended to use the same language as the job offers. 

The script expects a response from the language model in the following format: 

```
Ranking: <your ranking> 
Comment: <your short explanation>
```

### 2. Set your query settings

Create a list of settings dictionaries where each dictionary represents a search query.

To retrieve your inputs, visit the link [here](https://www.linkedin.com/jobs/search/?currentJobId=3272687552&f_WT=2&refresh=true&ref=nubela.co) in a private browser window and set your query settings for one query.

Use a **PRIVATE BROWSER WINDOW** for this link, otherwise LinkedIn will try to log you in.

Copy the contents of the following parameters into a dictionary:


| Parameter | Query String in URL| Description |
| --- | --- | --- |
| keywords | `&keywords=<your keywords>` | Keywords related to the job you're searching |
| location | `&location=<your location>` | Desired job location |
| geo_id | `&geoId=<your geo id>` | Geographical ID of your desired location |
| distance | `&distance=<your distance>` | Distance within your job location or geo id |
| level | `&f_E=<level filter tag>` | Job level filter tag (for ex: Associate Level, Entry Level, etc.) |
| work_type | `&f_WT=<work type filter tag>` | Work type filter tag (for ex: Full-time, Part-time, etc.) |


For example:

```python
settings_list = [
    {
        "keywords": "Python+(Programmiersprache)", 
        "location": "Karlsruhe%2C+Baden-Württemberg%2C+Germany", 
        "geo_id": "106523486"
    }
]
```

#### Filter
You can also set a filter dictionary. The filter dictionary contains the filter tag as key and a list of filter options as value.
```
Seniority level     ["Associate", "Entry level", "Mid-Senior level", "Director", "Executive"]
Employment type     ["Full-time", "Part-time", "Temporary", "Contract", "Internship", "Volunteer", "Other"]
Job function        ["Engineering", "Information Technology"....] Check the website for all options
Industries          ["Computer Software", "Information Technology & Services"...] Check the website for all options
```

For example: 

```python
filter = {"Seniority level": ["Associate", "Entry level"]}
```

### 3. Run the code

**You can adjust the main.py script to your requirements and run it**

#### How it works

Run the `simple_search` function with the target URLs and the job URL. The function returns a dataframe with the job offers and the job descriptions.

```python
job_df = w.simple_search(target_urls, job_url, filter=filter, number_of_jobs=100, do_max=None)
```

Where:

- `target_urls` is a list of URLs to scrape for multiple query options. You can create this list with the `create_target_url_list()` function.

- `job_url` is a URL to the job description which points to LinkedIn's job description API endpoint. You can adjust this as necessary at the top of this provided script.

- `filter` is a dictionary of filter tags and filter options. You can set this to None if you don't want to filter the results.

- `number_of_jobs` is the number of jobs found in each query. You can enter the max number of jobs found for one query which reduces run time when there are not a lot of jobs for each query. If you expect many job results for a query, you can set this to a higher number.

- `do_max` is for testing purposes only. If you want to test the code, set this to a low number. Set this to None for actual use. The script will stop requesting job descriptions after reaching the do_max threshold.

The results will be saved in a csv in the `outputs` folder. The file name is specified at the top within this script.
