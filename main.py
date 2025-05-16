from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time, random, yaml
import os

# Load Config
config = yaml.safe_load(open("config.yaml"))
resume_path = os.path.abspath(config['resume_path'])  # e.g. "./My_Resume.pdf"
phone_number = config.get('phone')  # e.g. "+911234567890"

driver = webdriver.Chrome()
driver.get("https://www.linkedin.com/login")

# Login
driver.find_element(By.ID, "username").send_keys(config['email'])
driver.find_element(By.ID, "password").send_keys(config['password'])
driver.find_element(By.XPATH, "//button[@type='submit']").click()

# Navigate to filtered Jobs page
time.sleep(5)
job_url = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords=Data+Scientist"
    "&location=Gurugram"
    "&f_AL=true"
)
driver.get(job_url)

wait = WebDriverWait(driver, 20, poll_frequency=0.5,
                     ignored_exceptions=[NoSuchElementException])
wait.until(EC.presence_of_all_elements_located(
    (By.CSS_SELECTOR, ".jobs-search-results__list-item")
))

# Scroll to load more
for _ in range(5):
    driver.execute_script("window.scrollBy(0, window.innerHeight);")
    wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, ".jobs-search-results__list-item")
    ))

cards = driver.find_elements(By.CSS_SELECTOR, ".jobs-search-results__list-item")
for card in cards:
    try:
        # 1) Click Easy Apply
        btn = card.find_element(
            By.XPATH,
            ".//div[contains(@class,'jobs-apply-button')]//button"
        )
        btn.click()
        
        # 2) Wait for modal
        wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.jobs-easy-apply-modal")
        ))
        
        modal = driver.find_element(By.CSS_SELECTOR, "div.jobs-easy-apply-modal")

        # 3) Fill phone if empty
        try:
            phone_input = modal.find_element(By.CSS_SELECTOR, "input[aria-label*='Phone']")
            if not phone_input.get_attribute("value").strip():
                phone_input.clear()
                phone_input.send_keys(phone_number)
        except NoSuchElementException:
            pass  # sometimes it's pre-filled or not requested

        # 4) Upload resume
        try:
            upload_input = modal.find_element(By.CSS_SELECTOR, "input[type='file']")
            upload_input.send_keys(resume_path)
        except NoSuchElementException:
            pass  # if already uploaded by default

        # 5) Answer simple screening questions (yes/no or short answer)
        # Example: pick the first radio‑group question and choose the first option
        questions = modal.find_elements(By.CSS_SELECTOR, "fieldset")
        for q in questions:
            # radio buttons
            radios = q.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if radios:
                radios[0].click()
            else:
                # text inputs
                txt = q.find_elements(By.CSS_SELECTOR, "input[type='text']")
                if txt:
                    txt[0].send_keys("Yes")  # or any placeholder
        time.sleep(1)

        # 6) Navigate through steps until Submit
        while True:
            try:
                # Continue button
                nxt = modal.find_element(
                    By.CSS_SELECTOR, "[aria-label='Continue to next step']")
                nxt.click()
                # wait for next content
                time.sleep(random.uniform(1, 2))
            except NoSuchElementException:
                # Submit button
                submit_btn = modal.find_element(
                    By.CSS_SELECTOR, "[aria-label='Submit application']")
                submit_btn.click()
                break

        # 7) Wait a moment then close modal or move on
        time.sleep(random.uniform(2, 4))
        # Close the modal (if close button exists)
        try:
            close_btn = driver.find_element(
                By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
            close_btn.click()
        except NoSuchElementException:
            pass

    except TimeoutException as e:
        driver.save_screenshot(f"timeout_{int(time.time())}.png")
        print(f"[Timeout] failed on job card: {e}")
        continue

driver.quit()
