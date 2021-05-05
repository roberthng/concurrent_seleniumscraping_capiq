from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from lxml import html
import requests
import csv
import re
import time
from time import sleep
import os
import datetime
import operator
import pickle
import sys
# [sys.path.append(i) for i in ['.', '..']]
# from settings import username, password

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
screen_url = 'https://www.capitaliq.com/CIQDotNet/Screening/MySavedScreens.aspx?tab=3'
company_url = 'https://www.capitaliq.com/CIQDotNet/Financial/{}.aspx?companyId={}'
custlist_url = 'https://www.capitaliq.com/CIQDotNet/BusinessRel/Customers.aspx?CompanyId={}'
driver_path = Path(BASE_DIR).joinpath('chromedriver.exe')

def get_driver(headless):
    output_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    download_folder = BASE_DIR.joinpath('/downloads')
    p = {"download.default_directory": download_folder.mkdir(parents=True, exist_ok=True), "safebrowsing.enabled":"false"}
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs",p)
    if headless:
        options.add_argument("--headless")
    # initialize driver
    driver_path = Path(BASE_DIR).joinpath('chromedriver.exe')
    driver = webdriver.Chrome(driver_path,chrome_options=options)
    return driver

def screenshot(browser):
    browser.set_window_size(1920, 1500)      #the trick
    time.sleep(2)
    browser.save_screenshot("screenshot.png")
    filename = "screenshot_{}.png".format(int(time.time()))
    browser.save_screenshot(Path(BASE_DIR).joinpath(filename))
    print("Screenshot of Failed Login Attempt Has Been Saved to: "+str(Path(BASE_DIR).joinpath(filename)))

def wait_clickretry(browser, xpathelement, xpathelement2=None):
    if xpathelement2 is None:
        xpathelement2 = xpathelement
    load_attempt = 0    
    while load_attempt<5:
        try:
            WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH,xpathelement)))
            browser.find_element_by_xpath(xpathelement).click()
            WebDriverWait(browser, 30).until_not(EC.presence_of_element_located((By.XPATH,xpathelement2)))
            load_attempt=5
        except Exception as e:
            print(f"Error: {e}, browser will reload for {load_attempt+1}th time")
            browser.refresh()
            sleep(2)
            load_attempt+=1

def try_login(browser,username,password):
    try:
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH,'//*[@id="TopIconTable"]/a[text()="Logout"]')))
        sleep(2)
    except Exception:
        print("No login cookie found, browser will login to the website")
        #login_ciq2(browser,usn,psw)
        browser.find_element_by_id('username').send_keys(username)
        if browser.find_element_by_id('PersistentLogin').get_attribute("value") == "false":
            browser.execute_script("arguments[0].click();",browser.find_element_by_id('chkPersistentLogin'))
            WebDriverWait(browser, 5)
        browser.find_element_by_id('password').send_keys(password)
        browser.find_element_by_id('password').send_keys(Keys.RETURN)
        WebDriverWait(browser, 50).until(EC.presence_of_element_located((By.XPATH,'//*[@id="TopIconTable"]/a[text()="Logout"]')))
        print("Login Successful")
    
def goto_screenpage(browser, screening_page_name):
    browser.get(screen_url)
    screening_page_element = f'//*[contains(text(),"{screening_page_name}")]'
    link = browser.find_elements_by_xpath(screening_page_element)
    if len(link)>0:
        browser.find_element_by_xpath(screening_page_element).click()
        print(f"\n\n{screening_page_name} page has been loaded.")
        wait_clickretry(browser, '//*[@id="sdg_h_RG_viewall"]')
        print(f"Full page of {screening_page_name} has been loaded")
        bank_dict = parse_screen(browser)
        return bank_dict
    else:
        print(f"{screening_page_name} page cannot be loaded properly")

def parse_screen(browser):
    bank_dict = {}
    bank_element = '//*[@id="sdg_h_RG"]/tbody/tr/td[3]/a{}'
    parent_element = '//*[@id="sdg_h_RG"]/tbody/tr/td[7]/span/text()'
    tree = html.fromstring(browser.page_source)
    banks_entry = tree.xpath(bank_element.format(""))
    print(str(len(banks_entry))+" Banks Found")
    print("Parsing screening page")
    num_bank = 0
    for count in range(len(banks_entry)):
        num_bank+=1
        href = tree.xpath(bank_element.format('/@href'))[count]
        Bank_ID = href[href.index("companyId=")+len("companyId="):href.index("&UniqueScreenId")]
        Bank_Name = tree.xpath(bank_element.format('/text()'))[count]
        parent_hq = tree.xpath(parent_element)[count]
        custlist_url_bank = custlist_url.format(Bank_ID)
        bank_dict[Bank_ID] = {}
        bank_dict[Bank_ID]['Name']=Bank_Name
        bank_dict[Bank_ID]['Parent_HQ']=parent_hq
        bank_dict[Bank_ID]['Num_Bank']=num_bank
    print("Dictionary of Banks Filled\n\n")
    return bank_dict

def goto_custpage2(bank_dict, Bank_ID, browser, concurrent=False):
    Bank_Name = bank_dict[Bank_ID]['Name']
    print("Processing to parse the customers list of bank: {} (id: {})".format(Bank_Name,Bank_ID))
    viewall_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid_viewall"]'
    view250_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid_viewMore" and text()="View 250 Per Page"]'
    custname_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr[1]/td[2]/a'
    if concurrent is False:
        custpage_url = custlist_url.format(Bank_ID)
        browser.get(custpage_url)
    bank_custlist = {}
    cust_numlist=list()
    cust_idlist=list()
    cust_namelist=list()
    cust_typelist=list()
    supplier_idlist=list()
    supplier_namelist=list()
    if len(browser.find_elements_by_xpath(custname_element))>0: #There are customers recorded on Capital IQ for the Bank
        n_custtext = browser.find_element_by_xpath('//*[@id="myCustomersGrid_gridSection_myDataGrid_pager"]/nobr').text
        n_custsplit = n_custtext.split()
        n_cust = int(n_custsplit[n_custsplit.index('Customers')-1])
        print(f"{n_cust} customers found for {Bank_Name}.")
        if len(browser.find_elements_by_xpath(view250_element.format('250')))>0:  #Customer list can only be viewed by pages of 250 entries
            bank_custlist[Bank_ID]={}
            wait_clickretry(browser, view250_element)
            total_pagenum = (n_cust // 250)+1 #def number of pages needed to be scraped
            total_pagegroup = 1 + (total_pagenum // 6)
            print(f"{Bank_Name}'s {n_cust} customers of are spread over {total_pagenum} page(s) in {total_pagegroup} page group(s).")
            current_pagegroup = 1
            current_page = 1
            while current_pagegroup <= total_pagegroup: 
                current_pageingroup = 1
                total_pageinlastgroup = total_pagenum % 6
                total_pageingroup = len(browser.find_elements_by_xpath('*//a[contains(@id,"page")]'))+1
                total_pageingroup = total_pageingroup if current_pagegroup<total_pagegroup else total_pageinlastgroup
                if (current_pagegroup>1 and total_pageingroup>1 ): #Only executed IF browser goes to another page group, but NOT if the next page group only contains one page.
                    firstpageingroup_element = f'//*[@id="myCustomersGrid_gridSection_myDataGrid_page{str(current_page)}"]'
                    wait_clickretry(browser, firstpageingroup_element) 
                while current_pageingroup < total_pageingroup:
                    print(f"Parsing page {current_page} of {total_pagenum} || {current_pageingroup} of {total_pageingroup} in page group {current_pagegroup} of {total_pagegroup}")
                    tree = html.fromstring(browser.page_source)
                    cust_numlist_page, cust_idlist_page, cust_namelist_page, cust_typelist_page, supplier_idlist_page, supplier_namelist_page = parse_custpage2(Bank_ID,bank_dict,tree,n_custsplit)
                    cust_numlist.extend(cust_numlist_page)
                    cust_idlist.extend(cust_idlist_page)
                    cust_namelist.extend(cust_namelist_page)
                    cust_typelist.extend(cust_typelist_page)
                    supplier_idlist.extend(supplier_idlist_page)
                    supplier_namelist.extend(supplier_namelist_page)
                    next_page_element = f'//*[@id="myCustomersGrid_gridSection_myDataGrid_page{str(current_page+1)}"]'
                    wait_clickretry(browser, next_page_element) 
                    current_pageingroup+=1
                    current_page +=1
                else: #currently on the last page in the group, click next group
                    print(f"Parsing page {current_page} of {total_pagenum} || {current_pageingroup} of {total_pageingroup} in page group {current_pagegroup} of {total_pagegroup}")
                    tree = html.fromstring(browser.page_source)
                    cust_numlist_page, cust_idlist_page, cust_namelist_page, cust_typelist_page, supplier_idlist_page, supplier_namelist_page = parse_custpage2(Bank_ID,bank_dict,tree,n_custsplit)
                    cust_numlist.extend(cust_numlist_page)
                    cust_idlist.extend(cust_idlist_page)
                    cust_namelist.extend(cust_namelist_page)
                    cust_typelist.extend(cust_typelist_page)
                    supplier_idlist.extend(supplier_idlist_page)
                    supplier_namelist.extend(supplier_namelist_page)
                    if current_page==total_pagenum:
                        break
                    next_pagegroup_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid_RightOneSet"]'
                    prev_firstpage_element = f'//*[@id="myCustomersGrid_gridSection_myDataGrid_page{str(current_page-5)}"]'
                    wait_clickretry(browser, next_pagegroup_element, prev_firstpage_element)
                    current_pagegroup+=1                    
                    current_page +=1      
        else: #Only one page group
            if len(browser.find_elements_by_xpath(viewall_element))>0: #All customers can be viewed in one page but viewall needs to be clicked
                wait_clickretry(browser, viewall_element)
            tree = html.fromstring(browser.page_source)
            cust_numlist_page, cust_idlist_page, cust_namelist_page, cust_typelist_page, supplier_idlist_page, supplier_namelist_page = parse_custpage2(Bank_ID,bank_dict,tree,n_custsplit)
            cust_numlist.extend(cust_numlist_page)
            cust_idlist.extend(cust_idlist_page)
            cust_namelist.extend(cust_namelist_page)
            cust_typelist.extend(cust_typelist_page)
            supplier_idlist.extend(supplier_idlist_page)
            supplier_namelist.extend(supplier_namelist_page)
        #make a dictionary out of the lists
        len_cust = len(cust_numlist)
        Bank_IDlist = [Bank_ID for i in range(len_cust)]
        Bank_Namelist = [Bank_Name for i in range(len_cust)]        
        Bank_CustPD = pd.DataFrame({'Bank_ID':Bank_IDlist, 'Bank_Name':Bank_Namelist, 'Cust_Num':cust_numlist, 'Cust_ID':cust_idlist, 'Cust_Name':cust_namelist, 'Cust_Type':cust_typelist, 'Supplier_ID':supplier_idlist, 'Supplier_Name':supplier_namelist})
        return Bank_CustPD
        print(Bank_custPD.head(5))
    else: #No customers
        print("No customers Found for (bank): "+Bank_Name)
        pass

def parse_custpage2(Bank_ID, bank_dict,tree, n_custsplit):
    bank_custlist = {}
    Bank_Name = tree.xpath('//*[@id="myPageHeader"]/span/span[1]/text()')[0]
    print(f"Parsing the Customer Page of Bank: {Bank_Name} (id: {Bank_ID})")
    Bank_Name = bank_dict[Bank_ID]['Name']
    # colname_list = tree.xpath('//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr[1]/td/a/text()')
    # suppname_loc = colname_list.index("Supplier Name")
    # custtype_loc = colname_list.index("Relationship Type") 
    custname_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[@class="cColSortedBG"]/div/div/a{}'
    custtype_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[{}]/span/text()'
    supplier_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[4]/a{}'
    supplier_exists = True if len(tree.xpath('//a[contains(text(),"Supplier Name")]'))>0 else False
    cust_urllist = tree.xpath(custname_element.format("/@href"))
    bottom_texts = tree.xpath('//*[@id="myCustomersGrid_gridSection_myDataGrid_pager"]/nobr/text()')[0]
    n_custinpage = bottom_texts.split()[1]
    start_num = int(n_custinpage[0:n_custinpage.index('-')]) if len(cust_urllist)>1 else 1
    end_num = int(n_custinpage[n_custinpage.index('-')+1:]) if len(cust_urllist)>1 else 1
    len_page = end_num-start_num+1
    cust_numlist = list(range(start_num,end_num+1))
    cust_idlist = [cust_url[cust_url.index("companyid=")+len("companyid="):] for cust_url in cust_urllist]
    cust_namelist = tree.xpath(custname_element.format("/text()"))
    cust_typelist = tree.xpath(custtype_element.format(5)) if supplier_exists else tree.xpath(custtype_element.format(3))
    if supplier_exists:
        supplier_urllist = tree.xpath(supplier_element.format("/@href"))[1:]
        supplier_idlist = [supplier_url[supplier_url.index("companyid=")+len("companyid="):] for supplier_url in supplier_urllist]
        supplier_namelist = tree.xpath(supplier_element.format("/text()"))[1:]
    else:
        supplier_idlist = [Bank_ID for i in range(len_page)]
        supplier_namelist = [Bank_Name for i in range(len_page)]
    return cust_numlist, cust_idlist, cust_namelist, cust_typelist, supplier_idlist, supplier_namelist

def write_to_file2(Bank_CustPD, filename):
    nrows = len(Bank_CustPD.index)
    file_path = Path(BASE_DIR).joinpath(filename)
    if not os.path.isfile(file_path):
        Bank_CustPD.to_csv(file_path, header=True)
    else:
        Bank_CustPD.to_csv(file_path, mode='a', header=False)
    print("\n{} rows of customers appended to {} \n \n".format(nrows,file_path))


########################################################################

#Kalo jumlah halaman adalah kelipatan dari 6 ditambah 1, maka browser tidak dapat menemukan 'first page in group' element
#Hal ini dikarenakan halaman 7, 13, dst sudah merupakan first page in group
#Tolong akomodir kemungkinan ini 

# def parse_custpage(Bank_ID, bank_dict,tree):
#     bank_custlist = {}
#     Bank_Name = tree.xpath('//*[@id="myPageHeader"]/span/span[1]/text()')[0]
#     print(f"Parsing the Customer Page of Bank: {Bank_Name} (id: {Bank_ID})")
#     Bank_Name = bank_dict[Bank_ID]['Name']
#     # colname_list = tree.xpath('//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr[1]/td/a/text()')
#     # suppname_loc = colname_list.index("Supplier Name")
#     # custtype_loc = colname_list.index("Relationship Type") 
#     custname_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[@class="cColSortedBG"]/div/div/a{}'
#     custtype_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[{}]/span/text()'
#     supplier_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[4]/a{}'
#     supplier_exists = True if len(tree.xpath('//a[contains(text(),"Supplier Name")]'))>0 else False
#     for count, url in enumerate(tree.xpath(custname_element.format(""))):
#         cust_url = tree.xpath(custname_element.format("/@href"))[count]
#         cust_id = cust_url[cust_url.index("companyid=")+len("companyid="):]
#         cust_name = tree.xpath(custname_element.format("/text()"))[count]
#         cust_relationship = tree.xpath(custtype_element.format(5))[count] if supplier_exists else tree.xpath(custtype_element.format(3))[count]
#         supplier_url = tree.xpath(supplier_element.format("/@href"))[count+1] if supplier_exists else None
#         supplier_id = supplier_url[supplier_url.index("companyid=")+len("companyid="):] if supplier_exists else Bank_ID
#         supplier_name = tree.xpath(supplier_element.format("/text()"))[count] if supplier_exists else Bank_Name
#         bank_custlist[cust_id] = {'Cust_Name': cust_name, 'Cust_Relationship': cust_relationship} #, 'Supplier_Name':supplier_name, 'Supplier_ID':supplier_id
#     return bank_custlist


# def write_to_file(bank_dict, bank_custlist, filename):
#     bank_pd = pd.DataFrame.from_dict(bank_dict,orient='index')
#     bank_pd.index.name = "Bank_ID"
#     cust_pd = pd.DataFrame.from_dict({(i,j): bank_custlist[i][j] 
#                            for i in bank_custlist.keys() 
#                            for j in bank_custlist[i].keys()},
#                        orient='index')
#     cust_pd.index.names =["Bank_ID","Cust_ID"]
#     fullcust_pd = cust_pd.join(bank_pd, how='inner')
#     file_path = Path(BASE_DIR).joinpath(filename)
#     if not os.path.isfile(file_path):
#         fullcust_pd.to_csv(file_path, header=True)
#     else:
#         fullcust_pd.to_csv(file_path, mode='a', header=False)
#     print("Output saved to {} \n \n".format(file_path))
        
# def parse_customers(Bank_ID,Bank_Name,browser):
#     print("Processing to parse the customers list of bank: {} (id: {})".format(Bank_Name,Bank_ID))
#     bankname_element = '//*[@id="myPageHeader"]/span/span[1]/text()' 
#     viewall_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid_viewall"]'
#     custname_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr[1]/td[2]/a'
#     customerurl_element = '//*[@id="myCustomersGrid_gridSection_myDataGrid"]/tbody/tr/td[@class="cColSortedBG"]/div/div/a'
    
#     custpage_url = custlist_url.format(Bank_ID)
#     browser.get(custpage_url)
#     connection_attempts = 0
#     while connection_attempts < 3:
#         try:
#             len_cust =  len(browser.find_elements_by_xpath(custname_element.format("@href"))) 
#             if len_cust>0:
#                 bank_custlist[Bank_ID] = {}
#                 viewall_button = browser.find_element_by_xpath(viewall_element)
#                 if viewall_button:
#                     viewall_button.click()
#                     wait.until_not(EC.presence_of_element_located((By.XPATH, viewall_element)))
#                     tree = html.fromstring(browser.page_source)
#                 else:
#                     pass
#                 tree = html.fromstring(browser.page_source)
#                 for count, url in enumerate(tree.xpath(customerurl_element)):
#                     cust_url = tree.xpath(customerurl_element.format("@href"))[count]
#                     cust_id = cust_url[cust_url.index("companyId=")+len("companyId="):]
#                     bank_custlist[Bank_ID][cust_id] = {}
#                     bank_custlist[Bank_ID][cust_id]['Name']= tree.xpath(customerurl_element.format("text()"))[count]
#                 print(str(len(bank_custlist[Bank_ID]))+" Customers Found for (bank): "+Bank_Name)
#                 return True, bank_custlist
#             else:
#                 # wait.until(EC.presence_of_element_located((By.XPATH, bankname_element)))
#                 print("No customers Found for (bank): "+bankname_text)
#                 return False
#         except Exception as e:
#             print(e)
#             connection_attempts += 1
#             print(f"Error connecting to {custpage_url}.")
#             print(f"Attempt #{connection_attempts}.")
#             return False

# def get_load_time(article_url):
#     try:
#         # set headersm
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
#         }
#         # make get request to article_url
#         response = requests.get(
#             article_url, headers=headers, stream=True, timeout=3.000
#         )
#         # get page load time
#         load_time = response.elapsed.total_seconds()
#     except Exception as e:
#         print(e)
#         load_time = "Loading Error"
#     return load_time


# after this line in gotocustpage ---> bank_custlist[Bank_ID]={}
# if n_cust <= 1500: #There are max 1500 customers, hence only one page group
#     current_page = 1
#     while current_page <= total_pagenum:
#         tree = html.fromstring(browser.page_source)
#         bank_custlist_page = parse_custpage(Bank_ID,bank_dict,tree)
#         bank_custlist[Bank_ID].update(bank_custlist_page)
#         if current_page==total_pagenum:
#             break #If we are on the last page, we don't need to go to the next page, which is non-existent.
#         next_page_element = f'//*[@id="myCustomersGrid_gridSection_myDataGrid_page{str(current_page+1)}"]'
#         next_page = browser.find_element_by_xpath(next_page_element)
#         next_page.click()
#         WebDriverWait(browser, 25).until_not(EC.presence_of_element_located((By.XPATH, next_page_element)))
#         current_page +=1
#     return bank_custlist
# else: #more than 1500 customers, hence more than 1 page groups

# def download_custlist(Bank_ID, Bank_Name, browser):
#     browser.execute_script("javascript:getReport_myExcelReport(document.getElementById('mainForm'),3,2,-1,false,false);")
#     raw_input()
#     filename = max([BASE_DIR.joinpath('\downloads') + "\\" + f for f in os.listdir(BASE_DIR.joinpath('/downloads/'))],key=os.path.getctime)
#     shutil.move(filename,os.path.join(BASE_DIR.joinpath('\downloads\'),f"{Bank_ID}_{Bank_Name}.xls"))


# def wait_orreload(browser,element, untilelement=True):
#     if untilelement:
#         try:
#             WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH,element)))
#         except Exception as e: #(NoSuchElementException, TimeoutException, ElementClickInterceptedException)
#             print(f"Error: {e}, browser will reload")
#             browser.refresh()
#             sleep(2)
#             WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH,element)))
#     else:
#         try:
#             WebDriverWait(browser, 30).until_not(EC.presence_of_element_located((By.XPATH,element)))
#         except Exception as e:
#             print(f"Error: {e}, browser will reload")
#             browser.refresh()
#             sleep(2)
#             WebDriverWait(browser, 30).until_not(EC.presence_of_element_located((By.XPATH,element)))

# def need_login(browser):
#     if 'Log In | S&P Capital IQ' in browser.title:
#         return True
#     else:
#         return False

# def login_ciq(browser,username,password):
#     login_url = "https://www.capitaliq.com"
#     connection_attempts = 0
#     while connection_attempts < 6:
#         try:
#             browser.get(login_url)
#             print("Logging in...")
#             browser.find_element_by_id('username').send_keys(username)
#             browser.find_element_by_id('password').send_keys(password)
#             browser.find_element_by_id('password').send_keys(Keys.RETURN)
#             if len(browser.find_elements_by_xpath('//*[@id="TopIconTable"]/a[text()="Logout"]'))>0:
#                 return True
#                 print("Login Successful")
#             else:
#                 return False
#                 print("Login Unsuccessful, check for the screenshot")
#                 screenshot(browser)
#         except Exception as e:
#             print(e)
#             connection_attempts += 1
#             print(f"Error connecting to {login_url}.")
#             print(f"Attempt #{connection_attempts}.")
#             return False
