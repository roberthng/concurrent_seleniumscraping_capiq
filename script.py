import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from time import sleep, time
from lxml import html
import settings
from pathlib import Path
from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
import pickle
from scrapers.scraper import get_driver, try_login, goto_screenpage, parse_screen, BASE_DIR
from scrapers.scraper import goto_custpage2, parse_custpage2, write_to_file2


uname = settings.username
pword = settings.password
download_folder = BASE_DIR.joinpath('/downloads')


class SeleniumDriver(object):
    def __init__(
        self,
        driver_path=Path(BASE_DIR).joinpath('chromedriver.exe'),# chromedriver path
        cookies_file_path=Path(BASE_DIR).joinpath('cookies.pkl'),# pickle file path to store cookies
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
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--headless") #for headless browser, please uncomment
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

# def login_gotoscreen(browser, usn, psw):
#     browser.get('https://capitaliq.com')
#     if need_login(browser):
#         try_login(browser,usn,psw)
#     else:
#         sleep(2)
#     screening_page_name = "Singapore Banks Screening"
#     bank_dict = goto_screenpage(browser, screening_page_name)
#     return bank_dict

def crawl_cust_pages(bank_dict,num,filename,browser):
    bank_id = list(bank_dict)[num]
    Bank_CustPD = goto_custpage2(bank_dict, bank_id, browser)
    return Bank_CustPD

if __name__ == "__main__":

    # set variables
    start_time = time()
    current_page = 1
    output_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename =  f"SG-Bank-Screening_{output_timestamp}.csv"

    # init browser
    #browser = get_driver(headless=headless)
    selenium_object = SeleniumDriver()
    browser = selenium_object.driver    
    bank_dict = login_gotoscreen(browser, uname, pword)
    bank_dict = dict(list(bank_dict.items())[57:58]) 
    selenium_object.save_cookies()

    # scrape and crawl
    for number in range(len(bank_dict)): 
        Bank_ID = list(bank_dict)[number]
        print(f"Processing Bank no. {str(bank_dict[Bank_ID]['Num_Bank'])} from the original Singapore Screening Page")
        bank_custlistPD = crawl_cust_pages(bank_dict,number,output_filename,browser)
        if bank_custlistPD is not None:
            print(bank_custlistPD.head(20))
            write_to_file2(bank_custlistPD, output_filename)

    selenium_object.close_all()
    end_time = time()
    elapsed_time = end_time - start_time
    print(f"Elapsed run time: {elapsed_time} seconds")
    
    
######################################################
# def run_process(browser, usn, psw):
#     if login_ciq(browser, usn, psw):
#         sleep(2)
#         if goto_screenpage(browser,"Singapore Banks Screening"):
#             sleep(3)
#             tree = html.fromstring(browser.page_source)
#             bank_dict = parse_screen(tree)
#             return bank_dict
#         else:
#             print("Error Parsing Singapore Banks Screening")
#             browser.quit()
#     else:
#         print("Error Logging In")
#         browser.quit()