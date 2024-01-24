
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

def get_api_key():
    # read api key from file
    with open("api_key.txt", "r") as file:
        api_key = file.readline().strip()  # remove newline if present
    return api_key

def read_file_content(name):
    # read text from file
    try:
        with open(name, "r", encoding="utf8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print("File not found.")
        return ""

def get_job_ids(target_url, number_of_jobs=1000):
    # read job ids from linkedin of given url, note that number_of_jobs is the expected total number of jobs for the query
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

def get_job_content(job_url, job_ids, do_max=None):
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
        if do_max != None:
            if c>=do_max:
                break

    return job_conten_list

def filter_jobs(job_content_list, constraints):
    # filter jobs by constraints    
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

def promt_llm(api_key, system, vita, job_description, model="gpt-3.5-turbo"):
    # get a llm responst to system, vita and job description (ranking and explanation, dependent on system.txt input)
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system},
        
        {"role": "user", "content": f"[[[YOU]]]\n{vita}\n\n[[[JOB]]]\n{job_description}"}
    ]
    )
    return completion.choices[0].message.content

def extract_llm_contents(llm_output, recursive=False):
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

def get_saved_jobs_from_file(filename):
    # read lines into a list
    with open(filename, "r") as file:
        job_id_list = file.readlines()
    # remove newline from each line
    job_id_list = [x.strip() for x in job_id_list]
    return job_id_list

def save_jobs_to_file(job_id_list, filename):
    # write lines into a file
    with open(filename, "w") as file:
        for job_id in job_id_list:
            file.write(f"{job_id}\n")

def scrape_jobs(target_urls, job_url, filter=None, number_of_jobs=2000, do_max=None, llm_iter=1, savefile="job_ids.txt"):    
    # main function
    
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

def create_target_url_list(query_list, url_template):
    target_urls = []
    for query_parameters in query_list:
        param = defaultdict(str) # set default value to empty string
        param.update(query_parameters)
        target_urls.append(url_template.format_map(param))
    return target_urls

# load csv into dataframe, sort for ranking and return top x jobs
def load_csv(filename, top=10):
    df = pd.read_csv(filename, sep=";")
    df = df.sort_values(by=['ranking'], ascending=False)    
    # print out all links in from top_link
    
    for link in df.head(top)["top_link"].values:
        print(link)
    
    return df.head(top)


if __name__=="__main__":
    pass
