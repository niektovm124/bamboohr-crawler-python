import collections
import csv
import math
import zipfile
import requests

from time import sleep
from io import BytesIO, StringIO

from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CSV_URL = 'https://stratatest.bamboohr.com/reports/timesheet-entries/-64?calendarFilter\[start]=2022-08-01&calendarFilter[end]=2022-08-31&format=csv'
LOGIN_URL = 'https://stratatest.bamboohr.com/login.php'
PEOPLE_URL = 'https://stratatest.bamboohr.com/employees/list?pin='

EMAIL = 'shane+test@strata.co.jp'
PASSWORD = 'StrataTest1'

LOGIN_BUTTON_XPATH = "//button[@type='submit']"
EMAIL_INPUT_XPATH = "//input[@id='lemail']"
PASSWORD_INPUT_XPATH = "//input[@id='password']"
TRUST_BROWSER_XPATH = "//span[contains(text(), 'Yes, Trust this Browser')]"

PROFILE_TITLE_XPATH = "//h1[@class='PageHeader__title']"
COMPANY_COUNT_XPATH = "//p[@class='jss-u96']"


def login(driver: WebDriver):
    print("Loading login page")
    driver.get('https://stratatest.bamboohr.com/login.php')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH)))
    email_input = driver.find_element(By.XPATH, EMAIL_INPUT_XPATH)
    email_input.send_keys(EMAIL)

    password_input = driver.find_element(By.XPATH, PASSWORD_INPUT_XPATH)
    password_input.send_keys(PASSWORD)
    driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH).click()

    print("Logged in!")

    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, TRUST_BROWSER_XPATH)))
    driver.find_element(By.XPATH, TRUST_BROWSER_XPATH).click()

    print("Set Browser Trusted")


def download_csv(driver: WebDriver):
    s = requests.Session()
    for cookie in driver.get_cookies():
        s.cookies.set(cookie['name'], cookie['value'])

    resp = s.get(CSV_URL)
    zip_file = zipfile.ZipFile(BytesIO(resp.content))
    print("Got files from ZIP : %s" % str(zip_file.namelist()))

    required_file_name = next(filter(lambda x: x.endswith("_1.csv"), zip_file.namelist()))
    print("Extracting file : %s" % required_file_name)

    file = zip_file.read(required_file_name)
    file = StringIO(file.decode())

    csv_data = csv.reader(file, delimiter=",")
    print("Printing CSV lines")

    for line in csv_data:
        print([e.replace('\ufeff', "").replace('"', '') for e in line])


def get_profile_urls(driver: WebDriver) -> [str]:

    driver.get(PEOPLE_URL)
    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, COMPANY_COUNT_XPATH)))
    sleep(2)  # Allow number element to be populated

    number_of_people = int(driver.find_element(By.XPATH, COMPANY_COUNT_XPATH).text)
    print("Got %d people" % number_of_people)
    pages = math.ceil(number_of_people / 50)

    # https://stratatest.bamboohr.com/employees/list?pin=&page=1
    links = []

    for page_no in range(1, pages+1):
        if page_no != 1:
            next_page_url = "".join([PEOPLE_URL, "&page=", str(page_no)])
            print("Loading next URL : %s" % next_page_url)
            driver.get(next_page_url)

        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.TAG_NAME, "tbody")))
        rows = driver.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")
        print("Got %d rows to parse" % len(rows))

        for tr in rows:
            profile_href = tr.find_elements(By.TAG_NAME, "td")[2].find_element(By.TAG_NAME, "a").get_property('href')
            links.append(profile_href)

    return links


profile_data = collections.namedtuple('profile_data', 'url name')


def parse_profile_page(driver: WebDriver, url: str) -> profile_data:
    driver.get(url)

    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, PROFILE_TITLE_XPATH)))
    title_name = driver.find_element(By.XPATH, PROFILE_TITLE_XPATH).text

    print("Got name : %s" % title_name)

    return profile_data(url=url, name=title_name)


def run():
    print("Starting WebDriver..")

    driver = webdriver.Chrome(ChromeDriverManager().install())
    login(driver)
    download_csv(driver)

    profile_urls = get_profile_urls(driver)

    print("Got %d profiles to scrape" % len(profile_urls))

    for link in profile_urls:
        data = parse_profile_page(driver, url=link)

    print("Script finished execution, closing webdriver")
    driver.close()




if __name__ == '__main__':
    run()