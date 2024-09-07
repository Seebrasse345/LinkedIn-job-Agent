import os
import time
import json
import random
from playwright.sync_api import sync_playwright
from pdfminer.high_level import extract_text
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
# Credentials
LINKEDIN_EMAIL = "matthaiosmarkatis@gmail.com"
LINKEDIN_PASSWORD = "Bakumonsuno45!"

STATE_FILE = "linkedin_state.json"  # File to save the browser state
MAX_LOGIN_ATTEMPTS = 3  # Maximum number of login attempts

class LinkedInJobApplier:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False
        self.user_data = json.load(open("user_data.json"))
        self.job_title = None

    def safe_navigate(self, url):
        try:
            self.page.goto(url)
            self.page.wait_for_load_state('domcontentloaded')
        except Exception as e:
            print(f"Error navigating to {url}: {str(e)}")

    def handle_consent(self):
        try:
            consent_button = self.page.query_selector('button[action-type="ACCEPT"]')
            if consent_button:
                consent_button.click()
                print("Clicked consent button")
        except Exception as e:
            print(f"Error handling consent: {str(e)}")

    def print_debug_info(self):
        print("Current URL:", self.page.url)
        print("Page title:", self.page.title())
        
        elements = self.page.query_selector_all('*')
        for elem in elements[:10]:  # Print info for first 10 elements
            tag = elem.evaluate('el => el.tagName')
            id_attr = elem.get_attribute('id')
            class_attr = elem.get_attribute('class')
            print(f"Tag: {tag}, ID: {id_attr}, Class: {class_attr}")

    def check_login_status(self):
        self.safe_navigate("https://www.linkedin.com/feed/")
        time.sleep(1.5)
        nav_bar = self.page.query_selector('div[data-test-id="nav-bar"]')
        profile_button = self.page.query_selector('div[data-control-name="nav.settings"]')
        feed_content = self.page.query_selector('div.feed-shared-update-v2')

        if nav_bar or profile_button or feed_content:
            print("User is logged in (Feed page check).")
            return True
        else:
            print("User might not be logged in or feed page didn't load properly.")
            self.print_debug_info()
            
            login_form = self.page.query_selector('form.login__form')
            if login_form:
                print("Login form detected. User is not logged in.")
                return False
            
            print("Unable to determine login status conclusively. Assuming logged in.")
            return True

    def login(self):
        print("Navigating to LinkedIn login page...")
        self.safe_navigate("https://www.linkedin.com/login")
        self.handle_consent()
        
        print("Filling in credentials...")
        self.page.fill("#username", LINKEDIN_EMAIL)
        self.page.fill("#password", LINKEDIN_PASSWORD)
        
        print("Clicking login button...")
        self.page.click('button[type="submit"]')
        
        time.sleep(2.5)
        return self.check_login_status()

    def ensure_login(self):
        if os.path.exists(STATE_FILE):
            self.browser = self.playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context(storage_state=STATE_FILE)
            self.page = self.context.new_page()
            if self.check_login_status():
                self.logged_in = True
                print("Successfully logged in using saved state!")
                return
        else:
            self.browser = self.playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()

        for attempt in range(MAX_LOGIN_ATTEMPTS):
            if self.check_login_status():
                self.logged_in = True
                print(f"Successfully logged in on attempt {attempt + 1}!")
                self.context.storage_state(path=STATE_FILE)
                return
            else:
                print(f"Login attempt {attempt + 1} of {MAX_LOGIN_ATTEMPTS}")
                self.login()

        print(f"Failed to log in after {MAX_LOGIN_ATTEMPTS} attempts.")
        self.logged_in = False

    def search_jobs(self, job_title):
        self.safe_navigate("https://www.linkedin.com/jobs/")
        self.page.fill('input[aria-label="Search by title, skill, or company"]', job_title)
        self.page.press('input[aria-label="Search by title, skill, or company"]', "Enter")
        time.sleep(2.5)

    def apply_distance_filter(self, distance):
        try:
            distance_button = self.page.query_selector('button[aria-label="Distance filter. Choose a distance radius"]')
            if distance_button:
                distance_button.click()
                print("Clicked distance filter dropdown")

                self.page.wait_for_selector('input#distance-filter-bar-slider', timeout=2500)

                distance_slider = self.page.query_selector('input#distance-filter-bar-slider')
                if distance_slider:
                    distance_slider.fill(str(distance))
                    print(f"Set distance to {distance}")

                    show_results_button = self.page.query_selector('button[aria-label="Apply current filter to show results"]')
                    if show_results_button:
                        show_results_button.click()
                        print("Clicked 'Show results' button")
                    else:
                        print("'Show results' button not found")
                else:
                    print("Distance slider not found")
            else:
                print("Distance filter button not found")

            self.page.wait_for_timeout(1500)

        except Exception as e:
            print(f"Error applying distance filter: {str(e)}")

    def scroll_to_load_jobs(self, index):
        self.page.evaluate(f"window.scrollTo(0, {index * 100})")
        self.page.wait_for_timeout(500)
    
    def print_form_elements(self):
        print("Printing all labels and select elements in the diversity form:")
        labels = self.page.query_selector_all('label')
        for label in labels:
            label_text = label.inner_text().strip()
            print(f"Label text: {label_text}")
            associated_element = label.evaluate('''(label) => {
                const el = document.getElementById(label.getAttribute("for"));
                return el ? {
                    tagName: el.tagName,
                    options: el.tagName === "SELECT" ? Array.from(el.options).map(option => option.text) : null
                } : null;
            }''')
            if associated_element:
                print(f"  Associated element type: {associated_element.get('tagName')}")
                if associated_element.get('tagName') == 'SELECT':
                    print(f"  Select options: {associated_element.get('options')}")
            else:
                print("  No associated element found")
        print("End of form elements")

    def apply_to_jobs(self, num_applications=5, location=None, distance=None, user_data_file='user_data.json'):
        if location:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location={location}")
            if distance:
                self.apply_distance_filter(distance)
        else:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location=United Kingdom")

        self.page.wait_for_selector('div.job-card-container', timeout=15000)

        with open(user_data_file, 'r') as f:
            user_data = json.load(f)

        job_cards = self.page.query_selector_all('div.job-card-container')
        
        job_data_list = []

        for i in range(min(num_applications, len(job_cards))):
            try:
                if i > 0:
                    self.scroll_to_load_jobs(i)
                    job_cards = self.page.query_selector_all('div.job-card-container')
                
                job_card = job_cards[i]
                
                job_card.click()
                self.page.wait_for_selector('.job-details-jobs-unified-top-card__job-title', timeout=5000)
                
                job_title_elem = self.page.query_selector('.job-details-jobs-unified-top-card__job-title')
                job_title = job_title_elem.inner_text() if job_title_elem else "Unknown Title"
                
                job_id = job_card.get_attribute('data-job-id') or "Unknown ID"
                
                easy_apply_button = self.page.query_selector('button.jobs-apply-button span.artdeco-button__text')
                
                simple_apply_button = self.page.query_selector('button.jobs-apply-button[aria-label^="Apply to"]')
                
                if easy_apply_button and 'Easy Apply' in easy_apply_button.inner_text():
                    easy_apply = True
                elif simple_apply_button:
                    easy_apply = False
                else:
                    easy_apply = False
                
                job_description_elem = self.page.query_selector('.jobs-description-content__text')
                job_description = job_description_elem.inner_text() if job_description_elem else "No description available"
                
                job_data = {
                    "job_id": job_id,
                    "job_title": job_title,
                    "easy_apply": easy_apply,
                    "job_description": job_description
                }
                
                job_data_list.append(job_data)
                
                print(json.dumps(job_data, indent=2))

                if job_id == "4012676794":
                    print(f"Found target job with ID: {job_id}")
                    
                    easy_apply_button = self.page.query_selector('button.jobs-apply-button')
                    if easy_apply_button:
                        easy_apply_button.click()
                        print("Clicked Easy Apply button")
                        
                        self.page.wait_for_selector('div.jobs-easy-apply-content', timeout=2500)
                        
                        self.fill_application_form(user_data, job_data_list)
                    else:
                        print("Easy Apply button not found for the target job")
                
            except Exception as e:
                print(f"Error analyzing job {i+1}: {str(e)}")
            
            self.page.wait_for_timeout(1000)

        print("Job card analysis complete.")
        return job_data_list

    def fill_application_form(self, user_data, job_data_list):
        while True:
            try:
                # Step 1: Check for and fill UK diversity form
                equal_opps_section = self.page.query_selector('span.jobs-easy-apply-form-section__label:has-text("Equal Opportunities")')
                if equal_opps_section:
                    print("UK diversity form detected. Filling out...")
                    self.fill_uk_diversity_form(user_data)
                    continue

                # Step 2: Fill known fields
                self.fill_field('select[id^="text-entity-list-form-component-formElement-"][id$="-multipleChoice"]', 
                                user_data['email'], 'email', select=True)
                self.fill_field('select[id^="text-entity-list-form-component-formElement-"][id$="-phoneNumber-country"]', 
                                user_data['phone_country_code'], 'phone country code', select=True)
                self.fill_field('input[id^="single-line-text-form-component-formElement-"][id$="-phoneNumber-nationalNumber"]', 
                                user_data['phone_number'], 'phone number')
                self.fill_city(user_data['city'])
                self.fill_driving_license(user_data.get('driving_license', 'Prefer not to say'))
                self.fill_years_of_experience()
                self.fill_salary(user_data.get('salary', '25000'))

                # Step 3: Try to proceed
                if self.try_proceed():
                    continue

                # Step 4: Handle unfilled fields
                unfilled_fields = self.page.query_selector_all('input:not([type="hidden"]):not([type="submit"]):not(:checked):not([value]), select:not([value]), textarea:empty')
                for field in unfilled_fields:
                    field_type = field.get_attribute('type') or field.tag_name.lower()
                    if field_type in ['text', 'textarea']:
                        field.fill('N/A')
                    elif field_type == 'checkbox':
                        if random.choice([True, False]):
                            field.check()
                    elif field_type == 'radio':
                        name = field.get_attribute('name')
                        options = self.page.query_selector_all(f'input[type="radio"][name="{name}"]')
                        random.choice(options).check()
                    elif field_type == 'select-one':
                        options = field.query_selector_all('option')
                        if options:
                            valid_options = [opt for opt in options if opt.get_attribute('value') and not self.is_default_option(opt)]
                            if valid_options:
                                random_option = random.choice(valid_options)
                                field.select_option(value=random_option.get_attribute('value'))
                    print(f"Filled unfilled field: {field.get_attribute('id') or field.get_attribute('name')}")

                # Step 5: Try to proceed again
                if self.try_proceed():
                    continue

                # Step 6: If still unsuccessful, log and break
                print("Unable to proceed after filling all fields. Moving on.")
                break

            except Exception as e:
                print(f"Error filling application form: {str(e)}")
                break

        print("Application process completed.")

    def fill_uk_diversity_form(self, user_data):
        print("Checking for UK diversity form...")
        
        equal_opps_section = self.page.query_selector('span.jobs-easy-apply-form-section__label:has-text("Equal Opportunities")')
        
        if not equal_opps_section:
            print("UK diversity form not detected. Skipping...")
            return False
        
        print("UK diversity form detected. Filling out...")
        
        try:
            self.print_form_elements()

            hear_about_input = self.page.query_selector('input[id^="single-line-text-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-"][id$="-text"]')
            if hear_about_input:
                hear_about_input.fill(user_data.get('hear_about_job', ''))
                print("Filled 'How did you hear about this job?'")

            dropdowns = [
                ("What Right to Work in the UK documents do you hold?", "right_to_work"),
                ("Are you currently living in the UK?", "living_in_uk"),
                ("What is your notice period/availability?", "notice_period"),
                ("What category would you consider your experience-level to be for the role you're applying for?", "experience_level")
            ]

            for label, key in dropdowns:
                try:
                    self.select_dropdown(label, key, user_data)
                except Exception as e:
                    print(f"Error selecting dropdown for '{label}': {str(e)}")

            def select_checkbox(legend_text, user_data_key):
                try:
                    fieldset = self.page.query_selector(f'fieldset:has(legend:has-text("{legend_text}"))')
                    if fieldset:
                        value = user_data.get(user_data_key, '')
                        if value:
                            option = fieldset.query_selector(f'label:has-text("{value}")')
                            if option:
                                option.click()
                                print(f"Selected '{legend_text}': {value}")
                            else:
                                print(f"Option '{value}' not found for '{legend_text}', skipping...")
                        else:
                            print(f"No value provided for '{legend_text}', skipping...")
                    else:
                        print(f"Fieldset for '{legend_text}' not found, skipping...")
                except Exception as e:
                    print(f"Error selecting checkbox for '{legend_text}': {str(e)}")

            select_checkbox("Gender", "gender")
            select_checkbox("Ethnicity", "ethnicity")
            select_checkbox("Sexual Orientation", "sexual_orientation")

            try:
                disability_fieldset = self.page.query_selector('fieldset:has(legend:has-text("Disability"))')
                if disability_fieldset:
                    disability_status = user_data.get('disability', {}).get('status', '').capitalize()
                    print(f"Attempting to select disability status: {disability_status}")
                    if disability_status:
                        option = disability_fieldset.query_selector(f'label:has-text("{disability_status}")')
                        if option:
                            option.click()
                            print(f"Selected disability status: {disability_status}")
                            
                            if disability_status == "Yes":
                                description_input = self.page.query_selector('textarea[aria-label="If yes, please could you describe the nature of your disability (e.g. visual impairment)"]')
                                if description_input:
                                    description = user_data.get('disability', {}).get('description', '')
                                    description_input.fill(description)
                                    print(f"Filled disability description: {description}")
                                else:
                                    print("Disability description input not found")
                        else:
                            print(f"Option '{disability_status}' not found for disability")
                    else:
                        print("No disability status provided, skipping...")
                else:
                    print("Disability fieldset not found, skipping...")
            except Exception as e:
                print(f"Error handling disability section: {str(e)}")

            return True

        except Exception as e:
            print(f"Error filling UK diversity form: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def fill_field(self, selector, value, field_name, select=False, timeout=3000, max_attempts=5):
        for attempt in range(max_attempts):
            try:
                element = self.page.wait_for_selector(selector, state="visible", timeout=timeout)
                if element:
                    if select:
                        element.select_option(value=value)
                    else:
                        element.fill(value)
                    print(f"Filled {field_name}: {value}")
                    return
                else:
                    print(f"{field_name.capitalize()} field not found, attempt {attempt + 1}/{max_attempts}")
            except Exception as e:
                print(f"Error filling {field_name}, attempt {attempt + 1}/{max_attempts}: {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(1)  # Short wait before next attempt
        
        print(f"Failed to fill {field_name} after {max_attempts} attempts")

    def fill_city(self, city):
        try:
            city_input = self.page.wait_for_selector('input[id^="single-typeahead-entity-form-component-formElement-"][id$="-city-HOME-CITY"]', 
                                                     state="visible", timeout=3000)
            if city_input:
                city_input.fill(city)
                self.page.wait_for_selector('div.basic-typeahead__triggered-content div[role="option"]', timeout=2000)
                self.page.click('div.basic-typeahead__triggered-content div[role="option"]:first-child')
                print(f"Filled city: {city}")
            else:
                print("City input not found, skipping...")
        except Exception as e:
            print(f"Error filling city: {e}")

    def fill_driving_license(self, license_value):
        try:
            fieldset = self.page.wait_for_selector('fieldset:has(legend)', state="visible", timeout=3000)
            if fieldset:
                legend_text = fieldset.evaluate('(el) => el.querySelector("legend").textContent')
                if 'driving license' in legend_text.lower():
                    options = fieldset.query_selector_all('label')
                    for option in options:
                        if license_value.lower() in option.inner_text().lower():
                            option.click()
                            print(f"Selected driving license: {license_value}")
                            break
                    else:
                        print(f"Option '{license_value}' not found for driving license")
                else:
                    print("Driving license question not found in this fieldset")
            else:
                print("No fieldset with legend found, skipping driving license")
        except Exception as e:
            print(f"Error handling driving license: {e}")

    def fill_years_of_experience(self):
        try:
            experience_inputs = self.page.query_selector_all('input[id^="single-line-text-form-component-formElement-"][id$="-numeric"]')
            for input in experience_inputs:
                label = self.page.evaluate('(el) => el.labels[0].textContent', input)
                if label and label.lower().startswith("how many years"):
                    input.fill('0')
                    print(f"Filled '0' for: {label}")
        except Exception as e:
            print(f"Error handling years of experience: {e}")

    def fill_salary(self, salary_value):
        try:
            salary_input = self.page.wait_for_selector('input[id*="salary" i], input[aria-label*="salary" i]', 
                                                       state="visible", timeout=3000)
            if salary_input:
                salary_input.fill(str(salary_value))
                print(f"Filled salary: {salary_value}")
            else:
                print("Salary input not found, skipping...")
        except Exception as e:
            print(f"Error handling salary: {e}")

    def is_default_option(self, option):
        default_phrases = ['select an option', 'choose', 'select', 'please select']
        option_text = option.inner_text().lower().strip()
        return any(phrase in option_text for phrase in default_phrases) or option_text == ''

    def try_proceed(self):
        buttons = [
            ('button[aria-label="Review your application"]', "Review"),
            ('button[aria-label="Continue to next step"]', "Next"),
            ('button[aria-label="Submit application"]', "Submit")
        ]

        for selector, button_type in buttons:
            button = self.page.query_selector(selector)
            if button:
                button.click()
                print(f"Clicked '{button_type}' button.")
                time.sleep(2)  # Wait for potential form change
                return True
        
        return False

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        self.playwright.stop()

def main():
    applier = LinkedInJobApplier()
    try:
        applier.ensure_login()
        if applier.logged_in:
            job_title = "Data architect"
            location = "Sheffield"
            distance = "25"
            applier.job_title = job_title  # Store job title as an instance variable
            applier.apply_to_jobs(location=location, distance=distance, user_data_file='user_data.json', num_applications=10)
        else:
            print("Failed to log in. Cannot proceed with job applications.")
    finally:
        applier.close()

if __name__ == "__main__":
    main()