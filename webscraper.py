
#%%
import requests
from bs4 import BeautifulSoup
import math
import pandas as pd
import json
from openai import OpenAI
from IPython.display import display

# search adress without login
#https://www.linkedin.com/jobs/search/?currentJobId=3272687552&f_WT=2&refresh=true&ref=nubela.co

headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}
#target_url='https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Python+(Programmiersprache)&location=Karlsruhe%2C+Baden-Württemberg%2C+Germany&geoId=106523486&start={}'
#target_url='https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=schreiner&location=Karlsruhe%2C+Baden-Württemberg%2C+Germany&geoId=106523486&start={}'



def get_api_key():
    with open("api_key.txt", "r") as file:
        api_key = file.readline().strip()  # remove newline if present
    return api_key

def read_file_content(name):
    try:
        with open(name, "r", encoding="utf8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print("File not found.")
        return ""

def dump_text(text, filename="soup.txt"):
    #dump soupt into a text file called soup.txt
    with open(filename, 'w', encoding="utf-8") as file:
        file.write(str(text))

def dump_dict_to_file(dict_obj, file_name):
    with open(file_name, 'w') as file:
        if isinstance(dict_obj, dict):
            dict_obj = [dict_obj]
        for dict_item in dict_obj:
            for key, value in dict_item.items():
                if isinstance(value, list):
                    value = ', '.join([str(x) for x in value])
                file.write(f'{key}: {value}\n')

def get_job_ids(target_url, number_of_jobs=2000):
    job_id_list=[]
    for i in range(0,math.ceil(number_of_jobs/25)):    #TODO change 117 to the number of jobs you want to scrape
        res = requests.get(target_url.replace("&start=", f"&start={i}"))
        soup=BeautifulSoup(res.text,'html.parser')
        alljobs_on_this_page=soup.find_all("li")
        print(len(alljobs_on_this_page))

        for x in range(0,len(alljobs_on_this_page)):
            try:
                jobid = alljobs_on_this_page[x].find("div",{"class":"base-card"}).get('data-entity-urn').split(":")[3]
                job_id_list.append(jobid)
            except:
                print("No job id found")
    print(job_id_list)
    return job_id_list

def get_job_content(job_url, job_ids, do_max=None):
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
                #continue
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

# get a llm responst to system, vita and job description (ranking and explanation, dependent on system.txt input)
def promt_llm(api_key, system, vita, job_description):
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system},
        
        {"role": "user", "content": f"[[[YOU]]]\n{vita}\n\n[[[JOB]]]\n{job_description}"}
    ]
    )
    return completion.choices[0].message.content

def extract_llm_contents(llm_output):
    #split string into ranking and explanation
    ranking = float(llm_output.split("\n")[0].replace("Ranking: ", ""))   # convert to float, somtimes the model outputs a float like ranking e.g. 6.5    
    explanation = llm_output.split("\n")[1].replace("Comment: ", "")
    return ranking, explanation

def simple_search(target_urls, job_url, filter, number_of_jobs=2000, do_max=None):
    job_id_list=[]
    jobs_df = pd.DataFrame()
    # request jobs
    for target_url in target_urls:
        print(f"Scraping: {target_url}")
        job_ids=get_job_ids(target_url, number_of_jobs=number_of_jobs) #TODO relocate number of jobs input
        #append job ids to list
        job_id_list.extend(job_ids)
    
    print(f"Found {len(job_id_list)} jobs.")
    # remove duplicates in job id list
    job_id_list = list(set(job_id_list))
    print(f"Found {len(job_id_list)} unique jobs.")
    # get job description and metadata
    job_description=get_job_content(job_url, job_id_list, do_max=do_max)
    # filter jobs
    filtered_jobs = filter_jobs(job_description, filter)

    api_key = get_api_key()
    system = read_file_content("system.txt")
    vita = read_file_content("vita.txt")

    print(f"Found {len(filtered_jobs)} jobs. Starting ranking...")
    for job_description in filtered_jobs:
        if not job_description["company"] == None:
            # get llm output
            output = promt_llm(api_key, system, vita, job_description)            
            
            job_string = f"{job_description['jobid']}\n{job_description['company']}\n{job_description['job-title']}\n{output}\n\n"
            ranking, explanation = extract_llm_contents(output)
            # add all data to dataframe
            job_description["ranking"] = ranking
            job_description["explanation"] = explanation
            # add job_description dict to dataframe without .append
            jobs_df = pd.concat([jobs_df, pd.DataFrame(job_description, index=[0])], ignore_index=True)            

            # sort dataframe by ranking 
            jobs_df = jobs_df.sort_values(by=['ranking'], ascending=False)
            
            # append to output.txt
            with open("output.txt", "a", encoding="utf8") as file:
                file.write(job_string)
            print(job_string)    
    
    return jobs_df

def create_url(args, url_template):
    keywords = args.pop("keywords", "")
    location = args.pop("location", "")
    geo_id = args.pop("geo_id", "")
    distance = args.pop("distance", "")
    employment_type = args.pop("employment_type", "")
    level = args.pop("level", "")
    url = url_template.format(keywords=keywords, location=location, geo_id=geo_id, distance=distance, employment_type=employment_type, level=level)
    return url

def create_target_url_list(query_list, url_template):
    target_urls = []
    for args in query_list:
        target_urls.append(create_url(args, url_template))
    return target_urls

if __name__=="__main__":
    pass
