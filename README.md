# Concurrent_Scraping_CapIQ
Concurrent webscraping of Capital IQ website using Selenium and Python

The code uses Selenium on Python to conduct webscraping on Capital IQ website, scraping the list of customers of banks from a list of banks.
The code directs the webdriver to do the following (all functions below in scraper.py file):
1. Login to Capital IQ and save/load the cookies. (try_login func - line 67)
2. Go to Singapore Banks Screening page to parse the list of banks in Singapore which customers are going to be scraped. (goto_screenpage & parse_screen functions - line 83 & 97)
3. Go to each of the bank's customer page to scrape the list of their customers. The webdriver will click next buttons if exists. (goto_custpage2 & parse_custpage2 functions - line 120 & 210)

The main script that works is "script.py" that go to each of the bank's customer page one by one. The script_concurrent.py file speeds up the process by running the crawling process of each customer page concurrently. The concurrency method being used is multiprocessing - Pool. Other concurrency methods - ProcessPoolExecutor and ThreadpoolExecutor are not working in this case. 


Credits to Caleb Pollman for the tutorial (https://testdriven.io/blog/building-a-concurrent-web-scraper-with-python-and-selenium/)
