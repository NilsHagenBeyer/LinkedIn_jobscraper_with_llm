
#%%
import requests
from bs4 import BeautifulSoup
import math
import pandas as pd
import json
from openai import OpenAI
from IPython.display import display
from collections import defaultdict

#headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}

def get_api_key() -> str:
    """Reads the openAI api key from a file.

    Returns:
        str: _description_
    """
    with open("api_key.txt", "r") as file:
        api_key = file.readline().strip()  # remove newline if present
    return api_key

def read_file_content(name: str) -> str:
    """Read content from file.

    Args:
        name (str): filename

    Returns:
        str: file content
    """
    try:
        with open(name, "r", encoding="utf8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print("File not found.")
        return ""

def get_job_ids(target_url: str, number_of_jobs=1000) -> list:
    """Get job ids from linkedin of given url.

    Args:
        target_url (str): job query url.
        number_of_jobs (int, optional): total number of jobs found for the query. Defaults to 1000.

    Returns:
        list: list of job ids.
    """
    job_id_list=[]
    for i in range(0,math.ceil(number_of_jobs/25)):     # get number of pages to scrape (usually 25 jobs per page)
        res = requests.get(target_url.replace("&start=", f"&start={i}"))
        soup=BeautifulSoup(res.text,'html.parser')
        alljobs_on_this_page=soup.find_all("li")
        

        for x in range(0,len(alljobs_on_this_page)):    # extract job id and save it to list
            try:
                jobid = alljobs_on_this_page[x].find("div",{"class":"base-card"}).get('data-entity-urn').split(":")[3]
                job_id_list.append(jobid)
                scrape = True
            except:
                scrape = False

            print(f"Page {i+1}, found {len(alljobs_on_this_page)} jobs. Able to scrape side: {scrape}             ", end="\r")


    return job_id_list

def get_job_content(job_url: str, job_ids: list, do_max=False) -> list:
    """Scrape job content from linkedin of given job ids.

    Args:
        job_url (str): url template to combine with job id to scrape job contents
        job_ids (list): list of job ids.
        do_max (_type_, optional): max number of jobs to scrape (reduce runtime for testing). Defaults to False.

    Returns:
        list: list of dictionaries each containing the job content of one job.
    """
    # get job content from linkedin of given job ids, do_max is the maximum number of jobs to scrape to limit the runtime for testing purposes
    job_conten_list=[]
    c = 0
    for job in job_ids:
        # print job id at same place
        print(f"Getting job content of Job: {job}", end="\r")
        
        job_dic={}
        resp = requests.get(job_url.format(job))
        soup=BeautifulSoup(resp.text,'html.parser')

        #jobId
        job_dic["jobid"]=job
        # top_link
        try:
            job_dic["top_link"]=soup.find("a",{"class":"topcard__link"}).get('href')
        except:
            job_dic["top_link"]=None
        # company
        try:
            job_dic["company"]=soup.find("div",{"class":"top-card-layout__card"}).find("a").find("img").get('alt')
        except:
            job_dic["company"]=None
        # job title
        try:
            job_dic["job-title"]=soup.find("div",{"class":"top-card-layout__entity-info"}).find("a").text.strip()
        except:
            job_dic["job-title"]=None
        
        # criteria
        try:
            items = soup.find_all("li", {"class": "description__job-criteria-item"})
            for item in items:
                header = item.find("h3", {"class": "description__job-criteria-subheader"}).get_text(strip=True)
                value = item.find("span", {"class": "description__job-criteria-text"}).get_text(strip=True)
                job_dic[header]=value
        except:
            job_dic["criteria"]=None
        
        # description
        try:
            text = soup.find("div",{"class":"description__text description__text--rich"}).get_text(separator="\n").replace("Show more", "").replace("Show less", "").lstrip('\n ').rstrip('\n ')
            job_dic["description"]=text
        except:
            job_dic["description"]=None
        
        # skip if no description is found
        if job_dic["description"] == None:
            continue
        
        job_conten_list.append(job_dic)

        # break if max is reached
        c+=1
        if do_max != False:
            if c>=do_max:
                break

    return job_conten_list

def filter_jobs(job_content_list: list, constraints: dict) -> list:
    """Filters jobs by constraints.

    Args:
        job_content_list (list): list of dictionaries each containing the job content of one job.
        constraints (dict): dictionary containing the constraints. Dict values can be a list of options or a single option.

    Returns:
        list: list of dictionaries each containing the job content of filtered jobs.
    """

    filtered_jobs=[]
    if constraints == None:
        return job_content_list
    
    for job in job_content_list:        
        for c_key, c_value in constraints.items():            
           
            # Filter options
            if c_key in job.keys():
                if type(c_value) == list:
                    if not job[c_key] in c_value:
                        print(f"Constraint not met! Constraint: {c_key} {c_value}   Job: {job[c_key]}")
                        break
                elif not job[c_key] == c_value:
                    print(f"Constraint not met! Constraint: {c_key} {c_value}   Job: {job[c_key]}")
                    break
            
            # Fixed criteria
            if job["description"] == None:
                print("No description found")
                break
            if job["company"] == None:
                print("No company found")
                break            
            
            filtered_jobs.append(job)
    print(f"From {len(job_content_list)} removed {len(job_content_list)-len(filtered_jobs)} jobs.")
    return filtered_jobs

def promt_llm(api_key: str, system: str, vita: str, job_description: str, model="gpt-3.5-turbo") -> str:
    """Promt the language model with the given inputs.

    Args:
        api_key (str): OpenAI API key.
        system (str): System input for the language model (General task description)
        vita (str): User input for the language model (Your vita)
        job_description (str): Description of the job offer, retrieved from linkedin.
        model (str, optional): Type of language model. See OpenAIs documentation. Defaults to "gpt-3.5-turbo".

    Returns:
        str: Response from the language model.
    """
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system},
        
        {"role": "user", "content": f"[[[YOU]]]\n{vita}\n\n[[[JOB]]]\n{job_description}"}
    ]
    )
    return completion.choices[0].message.content

def extract_llm_contents(llm_output: str, recursive=False) -> tuple:
    """Extract ranking and explanation from language model output.

    Args:
        llm_output (str): language model output.
        recursive (bool, optional): Flag to indicate if the function was called recursively, to prevent infinite loops. Defaults to False.

    Returns:
        tuple: ranking (float) and explanation (str)
    """
    # split string into ranking and explanation, note that the language model must output the ranking in the format: "Ranking: <your ranking> Comment: <your short explanation>"
    # if the language model does not output the ranking in the correct format, the function will try to extract the ranking once again
    try:
        ranking = float(llm_output.split("\n")[0].replace("Ranking: ", ""))   # convert to float, somtimes the model outputs a float like ranking e.g. 6.5
    except (ValueError, IndexError):
        if not recursive:
            print("Response Format Error: Ranking not found in llm response. Trying again...")
            ranking = extract_llm_contents(llm_output, recursive=True)
        else:
            ranking = 5.0
    try:
        explanation = llm_output.split("\n")[1].replace("Comment: ", "")
    except (ValueError, IndexError):
        explanation = "No explanation found."
    
    return ranking, explanation

def get_saved_jobs_from_file(filename: str) -> list:
    """Reads job ids from file.

    Args:
        filename (str): filename

    Returns:
        list: list of job ids
    """
    with open(filename, "r") as file:
        job_id_list = file.readlines()
    # remove newline from each line
    job_id_list = [x.strip() for x in job_id_list]
    return job_id_list

def save_jobs_to_file(job_id_list: list, filename: str):
    """Save job ids to file.

    Args:
        job_id_list (list): list of job ids
        filename (str): filename
    """
    with open(filename, "w") as file:
        for job_id in job_id_list:
            file.write(f"{job_id}\n")

def scrape_jobs(target_urls: list, job_url: str, filter=None, number_of_jobs=1000, do_max=None, llm_iter=1, savefile="job_ids.txt") -> pd.DataFrame:
    """Scrape jobs from linkedin for different query settings and rank them with the language model.

    Args:
        target_urls (list): list of urls to scrape for multiple query options.
        job_url (str): url template to combine with job id to scrape job contents
        filter (dict, optional): filter constraints. Defaults to None.
        number_of_jobs (int, optional): total number of jobs found for the query. Defaults to 1000.
        do_max (int, optional): max number of jobs to scrape (reduce runtime for testing). Defaults to None.
        llm_iter (int, optional): number of iterations for the language model to rank the job descriptions. The mean ranking is used for the final ranking. Defaults to 1.
        savefile (str, optional): filename to save job ids. Defaults to "job_ids.txt".

    Returns:
        pd.DataFrame: dataframe containing all job contents and ranking.
    """
    try:
        job_id_list=get_saved_jobs_from_file(savefile)  # load job ids from file
    except FileNotFoundError:
        job_id_list=[]
        print("No save file found. Making new one.")
    
    jobs_df = pd.DataFrame()
    # scrape job ids
    for target_url in target_urls:
        print(f"Scraping: {target_url}")
        job_ids=get_job_ids(target_url, number_of_jobs=number_of_jobs) #TODO relocate number of jobs input
        job_id_list.extend(job_ids)         # append job ids to list
    job_id_list = list(set(job_id_list))    # remove duplicates in job id list
    print(f"\nFound {len(job_id_list)} jobs.")    
    print(f"Found {len(job_id_list)} unique jobs.")
    
    save_jobs_to_file(job_id_list, savefile)    #save job ids to file
    
    job_description=get_job_content(job_url, job_id_list, do_max=do_max)    # get job description and metadata
    if not filter == None:
        job_description = filter_jobs(job_description, filter)    # filter jobs by constraints

    api_key = get_api_key()
    system = read_file_content("system.txt")
    vita = read_file_content("vita.txt")

    print(f"Found {len(job_description)} jobs. Starting ranking...")
    for job_description in job_description:
        if not job_description["company"] == None:
            
            # get ranking from llm
            rank_sum = 0
            for i in range(llm_iter):                
                output = promt_llm(api_key, system, vita, job_description)
                ranking, explanation = extract_llm_contents(output)
                rank_sum += ranking
                print(f"Itteration {i+1}/{llm_iter}     Current rating {ranking}", end="\r")                
            average_ranking = rank_sum / llm_iter            
            
            # add all data to dataframe
            job_description["ranking"] = average_ranking
            job_description["explanation"] = explanation
            jobs_df = pd.concat([jobs_df, pd.DataFrame(job_description, index=[0])], ignore_index=True)            

            # sort dataframe by ranking 
            jobs_df = jobs_df.sort_values(by=['ranking'], ascending=False)
            
            # save jobs to file
            job_string = f"{job_description['jobid']}\n{job_description['company']}\n{job_description['job-title']}\nAverage Ranking:{average_ranking}\nLLM Output:\n{output}\n\n"
            with open("output.txt", "a", encoding="utf8") as file:
                file.write(job_string)
            print(job_string)    
    
    return jobs_df

def create_target_url_list(query_list: list, url_template:str) -> list:
    """Create list of urls to scrape for each query.

    Args:
        query_list (list): list of dicts containing query parameters
        url_template (str): url template to combine with query parameters

    Returns:
        list: list of urls to scrape for each query
    """
    target_urls = []
    for query_parameters in query_list:
        param = defaultdict(str) # set default value to empty string
        param.update(query_parameters)
        target_urls.append(url_template.format_map(param))
    return target_urls

def load_csv(filename: str, top=10) -> pd.DataFrame:
    """Load csv into dataframe, sort for ranking and return top x jobs. Links to the top x jobs are printed.

    Args:
        filename (str): filename
        top (int, optional): number of top jobs to return. Defaults to 10.

    Returns:
        pd.DataFrame: dataframe containing top jobs
    """
    df = pd.read_csv(filename, sep=";")
    df = df.sort_values(by=['ranking'], ascending=False)    
    # print out all links in from top_link
    
    for link in df.head(top)["top_link"].values:
        print(link)
    
    return df.head(top)


if __name__=="__main__":
    pass
