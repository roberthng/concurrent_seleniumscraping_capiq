import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from time import sleep, time
from lxml import html
import settings
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pickle
from scrapers.scraper import get_driver, try_login, goto_screenpage, parse_screen, goto_custpage2, parse_custpage2, write_to_file2, BASE_DIR
from concurrent.futures import ProcessPoolExecutor, wait
from itertools import repeat
from multiprocessing import Pool, cpu_count




uname = settings.username
pword = settings.password
download_folder = BASE_DIR.joinpath('/downloads')


class SeleniumDriver(object):
    def __init__(
        self,
        driver_path=Path(BASE_DIR).joinpath('chromedriver.exe'),# chromedriver path
        cookies_file_path=Path(BASE_DIR).joinpath('cookies_concurrent.pkl'),# pickle file path to store cookies
        cookies_websites=["https://capitaliq.com"]# list of websites to reuse cookies with
    ):
        self.driver_path = driver_path
        self.cookies_file_path = cookies_file_path
        self.cookies_websites = cookies_websites
        chrome_options = webdriver.ChromeOptions()
        p = {"download.default_directory": download_folder.mkdir(parents=True, exist_ok=True), 
            "safebrowsing.enabled":"false"
            }
        chrome_options.add_experimental_option("prefs",p)
        chrome_options.add_argument('--no-sandbox')
        #chrome_options.add_argument("--headless") #if headless
        self.driver = webdriver.Chrome(
            executable_path=self.driver_path,
            options=chrome_options
        )
        try:
            # load cookies for given websites
            cookies = pickle.load(open(self.cookies_file_path, "rb"))
            for website in self.cookies_websites:
                self.driver.get(website)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                self.driver.refresh()
        except Exception as e:
            # it'll fail for the first time, when cookie file is not present
            print(str(e))
            print("Error loading cookies")

    def save_cookies(self):
        # save cookies
        cookies = self.driver.get_cookies()
        pickle.dump(cookies, open(self.cookies_file_path, "wb"))

    def close_all(self):
        # close all open tabs
        if len(self.driver.window_handles) < 1:
            return
        for window_handle in self.driver.window_handles[:]:
            self.driver.switch_to.window(window_handle)
            self.driver.close()
        
def login_gotoscreen(browser, usn, psw):
    browser.get('https://capitaliq.com')
    try_login(browser,usn,psw)
    screening_page_name = "Singapore Banks Screening"
    bank_dict = goto_screenpage(browser, screening_page_name)
    return bank_dict

def crawl_cust_pages(bank_dict, bank_id, filename):
    bank_url = f"https://www.capitaliq.com/CIQDotNet/BusinessRel/Customers.aspx?CompanyId={bank_id}"
    selenium_object = SeleniumDriver()
    browser = selenium_object.driver
    browser.get(bank_url)
    try_login(browser,usn,psw)
    bank_custlistPD = goto_custpage2(bank_dict, bank_id, browser, concurrent=True)
    write_to_file2(bank_dict,bank_custlistPD,filename)
            
if __name__ == "__main__":
    # headless mode?
    headless = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "headless":
            print("Running in headless mode")
            headless = True

    # set variables
    start_time = time()
    output_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename =  f"SG-Bank-Screening-Concurrent_{output_timestamp}.csv"
    total_cust = []

    # browser = get_driver(headless=headless)
    # bank_dict = run_process(browser, uname, pword)
    selenium_object = SeleniumDriver()
    browser = selenium_object.driver    
    bank_dict = login_gotoscreen(browser, uname, pword)
    bank_dict = dict(list(bank_dict.items())[0:6])
    selenium_object.save_cookies()
    total_cust =[]

    with ThreadPoolExecutor() as executor: #
        for ciq_bankid in list(bank_dict.keys()):
            total_cust.append(
                executor.submit(crawl_cust_pages, bank_dict, ciq_bankid, output_filename)
            )

    # with Pool(cpu_count() - 1) as p:
    #     p.starmap(crawl_cust_pages, zip(repeat(bank_dict), range(len(bank_dict)), repeat(output_filename), repeat(browser)))
    # p.close()
    # p.join() 
    # crawl_cust_pages(bank_dict, bank_id, filename)
    wait(total_cust)
    selenium_object.close_all()
    end_time = time()
    elapsed_time = end_time - start_time
    print(f"Elapsed run time: {elapsed_time} seconds")


# def login_gotoscreen(browser, usn, psw):
#     browser.get('https://capitaliq.com')
#     if need_login(browser):
#         try_login(browser,usn,psw)
#     else:
#         sleep(2)
#     screening_page_name = "Singapore Banks Screening"
#     bank_dict = goto_screenpage(browser, screening_page_name)
#     return bank_dict
