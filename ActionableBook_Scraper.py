from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import unidecode
import csv
import sys
import numpy as np

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_actionablebooks(path):

    start = time.time()
    print('-'*75)
    print('Scraping actionablebooks.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'actionablebooks_data.xlsx'
        # getting the books under each category
        driver.get('https://www.actionablebooks.com/en-ca/search-results/?search=&limit=summaries')
        time.sleep(3)
        links = []

        for _ in range(3):
            try:
                # scraping books urls
                spans = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.booktitle")))
                nbooks = len(spans)
                for i, span in enumerate(spans):
                    print("-"*75)
                    print(f'Scraping the url for book : {i+1}/{nbooks}')
                    link = wait(span, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                    links.append(link)


                # saving the links to a csv file
                print('-'*75)
                print('Exporting links to a csv file ....')
                with open('actionablebooks_links.csv', 'w', newline='\n', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Link'])
                    for row in links:
                        writer.writerow([row])

                break
            except Exception as err:
                print('The below error occurred during the scraping from actionablebooks.com, retrying ..')
                print('-'*50)
                print(err)
                print('-'*50)
                driver.quit()
                time.sleep(10)
                driver = initialize_bot()

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        links = df_links['Link'].values.tolist()
        name = path.split('\\')[-1][:-4]
        name = name + '_data.csv'
        try:
            data = pd.read_excel(name)
            scraped = data['Title Link'].values.tolist()
        except:
            pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h2"))).get_attribute('textContent').title() 
                #title = unidecode.unidecode(title)
            except:
                print(f'Warning: failed to scrape the title for book: {link}')            
                
            details['Title'] = title
            details['Title Link'] = title_link

            # author
            author = ''           
            try:
                sec = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//section[@id='book-author']")))
                headers = wait(sec, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "h4")))
                for header in headers:
                    author += header.get_attribute('textContent').title()
                    author += ', '
                author = author[:-2]
                #author = unidecode.unidecode(author)
            except:
                print(f'Warning: failed to scrape the author for book: {link}')            
                
            details['Author'] = author             
            
            # Amazon link
            amazon = ''           
            try:
                sec = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//section[@id='promo-book']")))
                amazon = wait(sec, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
            except:
                print(f'Warning: failed to scrape the Amazon link for book: {link}')            
                
            if 'www.amazon.com' in amazon:
                details['Amazon link'] = amazon  
            else:
                details['Amazon link'] = ''

            # summrized by
            summarized = ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.post-extras")))
                summarized = div.get_attribute('textContent').replace('Summary written by: ', '').strip()
            except:
                print(f'Warning: failed to scrape the summerized by info for book: {link}')            
                
            details['Summarized By'] = summarized             
            
            # summary
            summary = ''
            try:
                try:
                    sec = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.box-grey")))
                except:
                    sec = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.entry-content")))

                summary = sec.get_attribute('textContent').replace('The Big Idea: The biggest takeaway from the book', '').replace('The Big Idea', '').strip()
            except:
                print(f'Warning: failed to scrape the summary for book: {link}')            
                
            details['Summary'] = summary                                   
            # appending the output to the datafame            
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'actionablebooks.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_actionablebooks(path)

