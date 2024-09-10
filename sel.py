import os
import time
import json
import random
from playwright.sync_api import sync_playwright
from pdfminer.high_level import extract_text
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from Agent import Agent
import PyPDF2
import os
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
        self.agent = Agent(api_key="sk-vMxk-Z_yIcJhqOaK-GE2GoutLsw050TWhJWz1H-sazT3BlbkFJQgZUueDhTOvSX2jWBfBXVOQLpmBppxhG3reY68ZXYA", model="gpt-4o-mini")

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
    def extract_text_from_pdf(self,pdf_filename):
        # Check if the file exists in the current directory
        if not os.path.exists(pdf_filename):
            print(f"Error: The file '{pdf_filename}' does not exist in the current directory.")
            return None

        try:
            # Open the PDF file
            with open(pdf_filename, 'rb') as pdf_file:
                # Create a PDF reader object
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Initialize an empty string to store the extracted text
                extracted_text = ""
                
                # Iterate through all pages and extract text
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text()
                
            return extracted_text

        except Exception as e:
            print(f"An error occurred while processing the PDF: {str(e)}")
            return None
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
        time.sleep(2)
        if self.page.url != "https://www.linkedin.com/login":
            print("Already logged in.")
            return True
        else:
            print("Logging in...")
            self.handle_consent()
            
            print("Filling in credentials...")
            self.page.fill("#username", LINKEDIN_EMAIL)
            self.page.fill("#password", LINKEDIN_PASSWORD)
            
            print("Clicking login button...")
            self.page.click('button[type="submit"]')
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
            distance_button = self.page.wait_for_selector("button[aria-label^='Distance filter.'][id^='ember']",timeout=5000)
            if distance_button:
                distance_button.click()
                print("Clicked distance filter dropdown")

                self.page.wait_for_selector('input#distance-filter-bar-slider', timeout=2500)

                distance_slider = self.page.wait_for_selector('input#distance-filter-bar-slider', timeout=5000)
                if distance_slider:
                    distance_slider.fill(str(distance))
                    print(f"Set distance to {distance}")

                    show_results_button = self.page.wait_for_selector('button[aria-label="Apply current filter to show results"]', timeout=2500)
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
    def create_cover_letter(self,job_data):
        cv = self.extract_text_from_pdf("cv.pdf")
        job_desc = job_data[-1]["job_title"] + job_data[-1]["job_description"]
        self.agent.autobot(f"Create me a cover letter for the following job description {job_desc} using the cv {cv}")
        
        


    def apply_to_jobs(self, num_applications=5, location=None, distance=None, user_data_file='user_data.json'):
        if location:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location={location}")
            if distance:
                self.apply_distance_filter(distance)
        else:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location=United Kingdom")

        with open(user_data_file, 'r') as f:
            user_data = json.load(f)

        job_data_list = []
        applications_submitted = 0
        page_number = 1

        while applications_submitted < num_applications:
            self.page.wait_for_selector('div.job-card-container', timeout=15000)
            self.page.wait_for_load_state('domcontentloaded')
            time.sleep(5)
            self.press_easy_apply_button()
            time.sleep(5)

            job_cards = self.page.query_selector_all('div.job-card-container')
            
            for i, job_card in enumerate(job_cards):
                if applications_submitted >= num_applications:
                    break

                try:
                    self.scroll_to_load_jobs(i)
                    
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

                    easy_apply_button = self.page.wait_for_selector('button.jobs-apply-button', timeout=5000)
                    if easy_apply and "intern" not in job_title.lower() and "internship" not in job_title.lower():
                        easy_apply_button.click()
                        print("Clicked Easy Apply button")
                        
                        self.page.wait_for_selector('div.jobs-easy-apply-content', timeout=2500)
                        
                        self.fill_application_form(user_data, job_data_list)
                        applications_submitted += 1
                    else:
                        print("Easy Apply button not found or job not suitable")
                    
                except Exception as e:
                    print(f"Error analyzing job {i+1} on page {page_number}: {str(e)}")
                
                self.page.wait_for_timeout(1000)

            if applications_submitted < num_applications:
                if self.go_to_next_page():
                    page_number += 1
                    print(f"Moving to page {page_number}")
                else:
                    print("No more pages available")
                    break

        print("Job application process complete.")
        return job_data_list

    def go_to_next_page(self):
        try:
            next_button = self.page.wait_for_selector('button.artdeco-pagination__button--next:not(:disabled)', timeout=5000)
            if next_button:
                next_button.click()
                print("Clicked next page button")
                self.page.wait_for_load_state('domcontentloaded')
                time.sleep(3)  # Wait for the new page to load
                return True
            else:
                print("Next page button not found or disabled")
                return False
        except Exception as e:
            print(f"Error navigating to next page: {str(e)}")
            return False

    def scroll_to_load_jobs(self, index):
        self.page.evaluate(f"document.querySelectorAll('div.job-card-container')[{index}].scrollIntoView()")
        self.page.wait_for_timeout(1000)  # Wait for any dynamic content to load

    def fill_application_form(self, user_data, job_data_list):
        stuck_attempts = 0
        max_stuck_attempts = 3
        last_progress_value = -1
        progressing = True

        while progressing == True:
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
                self.cover_letter_check(job_data_list)
                progress_bar = self.page.query_selector('progress.artdeco-completeness-meter-linear__progress-element')
                progress_value = int(progress_bar.get_attribute('value'))
                                    # Step 5: Try to proceed again
                test = self.try_proceed()
                if test == True:
                    progressing = False
                else:
                    current_val = test

                    if progress_value == int(current_val):
                        self.fill_unfilled_fields()



                test_2 = self.try_proceed()
                if test_2 == True:
                    break
                else:
                    new_val = test_2




                if int(new_val) == int(current_val):
                            stuck_attempts += 1
                            print(f"Stuck attempt {stuck_attempts}/{max_stuck_attempts}")
                else:
                            stuck_attempts = 0  # Reset if progress is detected
                if stuck_attempts >= max_stuck_attempts:
                        print("Failed to complete application after multiple attempts. Exiting application process.")
                        dismiss_button = self.page.query_selector('button.artdeco-modal__dismiss')
                        if dismiss_button:
                            dismiss_button.click()
                            print("Clicked 'Dismiss' button to close the application modal.")
                        self.press_discard_button()
                        progressing = False

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
    def cover_letter_check(self,job_data_list):
                # Try to find the upload button
        try:
            upload_button = self.page.wait_for_selector('label[for^="jobs-document-upload-file-input-upload-cover-letter"]', timeout=3000)
            
            if upload_button:
                print("Cover letter upload button found.")
                
                # Check if the button is visible
                if not upload_button.is_visible():
                    print("Upload button is not visible. Attempting to make it visible...")
                    self.page.evaluate("""
                        () => {
                            const button = document.querySelector('label[for^="jobs-document-upload-file-input-upload-cover-letter"]');
                            if (button) {
                                button.style.display = 'block';
                                button.style.visibility = 'visible';
                                const parentContainer = button.closest('.js-jobs-document-upload__container');
                                if (parentContainer) {
                                    parentContainer.style.display = 'flex';
                                    parentContainer.style.visibility = 'visible';
                                }
                            }
                        }
                    """)
                
                # Find the associated file input
                file_input = self.page.query_selector('input[id^="jobs-document-upload-file-input-upload-cover-letter"]')
                if self.user_data["used_cover"] == False:
                    self.create_cover_letter(job_data_list)
                
                if file_input:
                    # Upload the file
                    file_input.set_input_files("cover.pdf")
                    print("Cover letter uploaded successfully!")
                else:
                    print("File input not found!")
            else:
                print("Cover letter upload button not found.")
        except Exception as e:
            print("Error handling cover letter upload:")
    def fill_unfilled_fields(self):
        try:
            easy_apply_container = self.wait_for_and_scroll_to_element('div.jobs-easy-apply-content')
            if not easy_apply_container:
                print("Easy Apply container not found or not visible.")
                return

            # Find all input fields, including those that are checked
            all_fields = easy_apply_container.query_selector_all(
                'input:not([type="hidden"]):not([type="submit"]), '
                'select, textarea'
            )

            # Keep track of radio button groups we've already processed
            processed_radio_groups = set()

            for field in all_fields:
                field_type = field.get_attribute('type') or field.tag_name.lower()
                field_id = field.get_attribute('id') or field.get_attribute('name')
                
                # Scroll the field into view and wait a short time
                field.scroll_into_view_if_needed()
                time.sleep(0.5)

                if field_type in ['text', 'textarea']:
                    if not field.input_value().strip():
                        is_numeric = 'numeric' in (field_id or '').lower() or 'number' in (field_id or '').lower()
                        field.fill('0' if is_numeric else 'N/A')
                        print(f"Filled {'numeric' if is_numeric else 'text'} field: {field_id}")
                elif field_type == 'checkbox':
                    label_text = self.get_label_text(field).lower()
                    if "visa" in label_text or "sponsorship" in label_text:
                        # Uncheck for visa/sponsorship questions
                        if field.is_checked():
                            self.click_element_safely(field)
                            print(f"Unchecked visa/sponsorship checkbox: {field_id}")
                    elif not field.is_checked() and random.choice([True, False]):
                        self.click_element_safely(field)
                        print(f"Checked checkbox: {field_id}")
                elif field_type == 'radio':
                    name = field.get_attribute('name')
                    if name not in processed_radio_groups:
                        radio_group = easy_apply_container.query_selector_all(f'input[type="radio"][name="{name}"]')
                        
                        # Get the label for the entire radio group
                        group_label = self.get_group_label(radio_group[0])
                        print(f"Processing radio group: {group_label}")

                        if "visa" in group_label.lower() or "sponsorship" in group_label.lower():
                            # Find and select the "No" option
                            no_option = next((radio for radio in radio_group if self.get_label_text(radio).strip().lower() == 'no'), None)
                            if no_option:
                                self.click_element_safely(no_option)
                                print("Selected 'No' for visa/sponsorship question")
                            else:
                                print("Could not find 'No' option for visa/sponsorship question")
                        if "legally authorized" in group_label.lower():
                            # Find and select the "Yes" option
                            yes_option = next((radio for radio in radio_group if self.get_label_text(radio).strip().lower() == 'yes'), None)
                            if yes_option:
                                self.click_element_safely(yes_option)
                                print("Selected 'Yes' for legally authorized question")
                            else:
                                print("Could not find 'Yes' option for legally authorized question")
                        elif not any(radio.is_checked() for radio in radio_group):
                            selected_radio = random.choice(radio_group)
                            self.click_element_safely(selected_radio)
                            print(f"Selected radio button: {selected_radio.get_attribute('id')} from group {name}")
                        else:
                            print(f"Radio group {name} already has a selection. Skipping.")
                        
                        processed_radio_groups.add(name)
                elif field_type == 'select-one':
                    # Only change if no option is selected
                    if not field.evaluate('(el) => el.value'):
                        options = field.query_selector_all('option')
                        valid_options = [opt for opt in options if opt.get_attribute('value') and not self.is_default_option(opt)]
                        if valid_options:
                            random_option = random.choice(valid_options)
                            field.select_option(value=random_option.get_attribute('value'))
                            print(f"Selected option for select field: {field_id}")
                    else:
                        print(f"Select field {field_id} already has a selection. Skipping.")

        except Exception as e:
            print("Error filling unknown fields:")
            print(e)

    def get_label_text(self, field):
        # Try to find an associated label
        label = field.evaluate('''
            (el) => {
                const label = el.labels[0] || document.querySelector(`label[for="${el.id}"]`);
                return label ? label.textContent.trim() : '';
            }
        ''')
        return label or ''

    def get_group_label(self, field):
        # Try to find the group label for radio buttons
        group_label = field.evaluate('''
            (el) => {
                const fieldset = el.closest('fieldset');
                if (fieldset) {
                    const legend = fieldset.querySelector('legend');
                    if (legend) return legend.textContent.trim();
                }
                // If no fieldset/legend, try to find a common parent with a label-like element
                let parent = el.parentElement;
                while (parent) {
                    const possibleLabel = parent.querySelector('label, div[class*="label"], span[class*="label"]');
                    if (possibleLabel) return possibleLabel.textContent.trim();
                    parent = parent.parentElement;
                }
                return '';
            }
        ''')
        return group_label or ''

    def click_element_safely(self, element):
        try:
            # Try regular click
            element.click()
        except Exception as e:
            print(f"Regular click failed: {e}")
            try:
                # Try forcing click with JavaScript
                self.page.evaluate("(element) => element.click()", element)
            except Exception as e:
                print(f"Forced click failed: {e}")
                # If both methods fail, try clicking the label if it exists
                label = element.query_selector("label")
                if label:
                    try:
                        label.click()
                    except Exception as e:
                        print(f"Label click failed: {e}")
                        # If all else fails, try to select the radio button programmatically
                        if element.get_attribute('type') == 'radio':
                            self.page.evaluate("(element) => element.checked = true", element)
        
        # Wait a short time after clicking to allow any animations or state changes
        time.sleep(0.5)

    def wait_for_and_scroll_to_element(self, selector, timeout=1000):
        element = self.page.wait_for_selector(selector, timeout=timeout)
        if element:
            element.scroll_into_view_if_needed()
            return element
        return None
    def is_default_option(self, option):
        default_phrases = ['select an option', 'choose', 'select', 'please select']
        option_text = option.inner_text().lower().strip()
        return any(phrase in option_text for phrase in default_phrases) or option_text == ''
    def fill_field(self, selector, value, field_name, select=False, timeout=1000, max_attempts=1):
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
    def press_discard_button(self):
        # Locate the discard button using its text content and role
        discard_button_selector = 'button[data-test-dialog-secondary-btn]:has-text("Discard")'
        
        try:
            # Wait for the button to be visible and clickable
            discard_button = self.page.wait_for_selector(discard_button_selector, state="visible", timeout=5000)
            
            # Click the discard button
            discard_button.click()
            
            print("Discard button clicked successfully.")
        except TimeoutError:
            print("Discard button not found or not clickable within the timeout period.")
    def fill_city(self, city):
        try:
            city_input = self.page.wait_for_selector('input[id^="single-typeahead-entity-form-component-formElement-"][id$="-city-HOME-CITY"]', 
                                                     state="visible", timeout=500)
            if city_input:
                city_input.fill(city)
                self.page.wait_for_selector('div.basic-typeahead__triggered-content div[role="option"]', timeout=500)
                self.page.click('div.basic-typeahead__triggered-content div[role="option"]:first-child')
                print(f"Filled city: {city}")
            else:
                print("City input not found, skipping...")
        except Exception as e:
            print(f"Error filling city: {e}")

    def fill_driving_license(self, license_value):
        try:
            fieldset = self.page.wait_for_selector('fieldset:has(legend)', state="visible", timeout=500)
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
            salary_input = self.page.query_selector_all('input[id^="single-line-text-form-component-formElement-"][id$="-numeric"]')
            for input in salary_input:
                label = self.page.evaluate('(el) => el.labels[0].textContent', input)
                if label and label.lower().startswith("salary") or "salary" in label.lower():
                    input.fill('25000')
                    print(f"Filled '25000' for: {label}")
                else:
                    print("Salary input not found, skipping...")
        except Exception as e:
            print(f"Error handling salary")

    def press_easy_apply_button(self):
      easy_apply_selector = 'button[aria-label="Easy Apply filter."][role="radio"]'
      
      try:
          easy_apply_button = self.page.wait_for_selector(easy_apply_selector, state="visible", timeout=5000)
          
          if easy_apply_button:
              easy_apply_button.click()
              print("Easy Apply button clicked successfully.")
          else:
              print("Easy Apply button not found.")
      except TimeoutError:
          print("Easy Apply button not found or not clickable within the timeout period.")
      except Exception as e:
          print(f"An error occurred while trying to click the Easy Apply button: {str(e)}")

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
                time.sleep(1)  # Wait for potential form change

                if button_type in ["Review", "Next"]:
                    # Check progress bar to ensure it has moved
                    progress_bar = self.page.query_selector('progress.artdeco-completeness-meter-linear__progress-element')
                    if progress_bar:
                        progress_value = int(progress_bar.get_attribute('value'))
                        print(f"Progress bar value after clicking '{button_type}': {progress_value}")
                            
                        return progress_value


                if button_type == "Submit":
                    # Wait for the "Done" button to appear
                    done_button_selector = 'button.artdeco-button--primary:has-text("Done")'
                    self.page.wait_for_selector(done_button_selector, timeout=5000)
                    done_button = self.page.query_selector(done_button_selector)
                    if done_button:
                        done_button.click()
                        print("Clicked 'Done' button. Application successfully submitted.")
                        return True
                    else:
                        print("Failed to find 'Done' button after submission.")
                        return False

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
            job_title = "Data"
            location = "Sheffield"
            distance = "4"
            applier.job_title = job_title  # Store job title as an instance variable
            applier.apply_to_jobs(location=location, distance=distance, user_data_file='user_data.json', num_applications=10)
        else:
            print("Failed to log in. Cannot proceed with job applications.")
    finally:
        applier.close()

if __name__ == "__main__":
    main()