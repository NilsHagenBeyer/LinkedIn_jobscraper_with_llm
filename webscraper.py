import requests
from bs4 import BeautifulSoup
import math
import pandas as pd
import json
from openai import OpenAI


headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}
target_url='https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Python+(Programmiersprache)&location=Karlsruhe%2C+Baden-Württemberg%2C+Germany&geoId=106523486&start={}'
#target_url='https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=schreiner&location=Karlsruhe%2C+Baden-Württemberg%2C+Germany&geoId=106523486&start={}'

job_url='https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}'

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

def get_job_ids(target_url):
    job_id_list=[]
    for i in range(0,math.ceil(250/25)):    #TODO change 117 to the number of jobs you want to scrape
        res = requests.get(target_url.format(i))
        soup=BeautifulSoup(res.text,'html.parser')
        alljobs_on_this_page=soup.find_all("li")
        print(len(alljobs_on_this_page))

        for x in range(0,len(alljobs_on_this_page)):
            try:
                jobid = alljobs_on_this_page[x].find("div",{"class":"base-card"}).get('data-entity-urn').split(":")[3]
                print(jobid)
                job_id_list.append(jobid)
            except:
                print()
    
    return job_id_list

def get_job_content(job_url, job_ids):
    job_conten_list=[]
    c = 0
    for job in job_ids:
        print(job)
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
        
        c+=1
        if c>=10:
            pass
            #break

    return job_conten_list

def filter_jobs(job_content_list, constraints):
    filtered_jobs=[]
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


def promt_llm(api_key, system, vita, job_description):

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system},
        
        {"role": "user", "content": f"[[[YOU]]]\n{vita}\n\n[[[JOB]]]\n{job_description}"}
    ]
    )

    print(completion.choices[0].message.content)
    return completion.choices[0].message.content

def simple_search():
    job_ids=get_job_ids(target_url)
    k=get_job_content(job_url, job_ids)
    filtered_jobs = filter_jobs(k, {"Seniority level": ["Associate", "Entry level"]})

    api_key = get_api_key()
    
    system = read_file_content("system.txt")
    vita = read_file_content("vita.txt")

    for job_description in filtered_jobs:
        if not job_description["company"] == None:
            print(job_description["jobid"])
            print(job_description["company"])
            print(job_description["job-title"])
            print()
            output = promt_llm(api_key, system, vita, job_description)
            print()

            # append to output.txt
            with open("output.txt", "a", encoding="utf8") as file:
                file.write(f"{job_description['jobid']}\n")
                file.write(f"{job_description['company']}\n")
                file.write(f"{job_description['job-title']}\n")
                file.write("\n")
                file.write(output)
                file.write("\n")
                file.write("\n")



if __name__=="__main__":
    ''' job_ids=get_job_ids(target_url)
    k=get_job_content(job_url, job_ids)
    
    filtered = filter_jobs(k, {"Seniority level": ["Associate", "Entry level"]})
    
    df = pd.DataFrame(k)
    df.to_csv('linkedinjobs.csv', index=False, encoding='utf-8')
    dump_dict_to_file(k, "dings.txt")'''

    
    
    '''api_key = get_api_key()
    vita = read_file_content("vita.txt")
    print(vita)
    system = read_file_content("system.txt")
    vita = read_file_content("vita.txt")
    job_description = read_file_content("job_description.txt")    
    promt_llm(api_key, system, vita, job_description)'''

    simple_search()