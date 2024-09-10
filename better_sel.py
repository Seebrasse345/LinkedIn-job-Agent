import json
import time
from playwright.sync_api import sync_playwright
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

LINKEDIN_EMAIL = "matthaiosmarkatis@gmail.com"
LINKEDIN_PASSWORD = "Bakumonsuno45!"

STATE_FILE = "linkedin_state.json"  # File to save the browser state

class LinkedInJobBot:
  def __init__(self):
      self.playwright = sync_playwright().start()
      self.browser = self.playwright.chromium.launch(headless=False)
      self.context = self.browser.new_context(storage_state = "linkedin_state.json")
      self.page = self.context.new_page()
      self.state = self.load_state()
      self.job_title = None

  def __del__(self):
      self.save_state()
      self.context.close()
      self.browser.close()
      self.playwright.stop()

  def save_state(self):
      with open(STATE_FILE, 'w') as f:
          json.dump(self.state, f)

  def load_state(self):
      try:
          with open(STATE_FILE, 'r') as f:
              return json.load(f)
      except FileNotFoundError:
          return {"logged_in": False, "last_url": ""}

  def handle_consent(self):
      try:
          consent_button = self.page.query_selector('button[action-type="ACCEPT"]')
          if consent_button:
              consent_button.click()
              print("Clicked consent button")
      except Exception as e:
          print(f"Error handling consent: {str(e)}")

  def login(self):
      print("Navigating to LinkedIn...")
      self.page.goto("https://www.linkedin.com/feed/")
      time.sleep(2)

      current_url = self.page.url
      if "login" in current_url or "checkpoint" in current_url:
          print("Not logged in. Proceeding with login...")
          self.handle_consent()
          
          print("Filling in credentials...")
          self.page.fill("#username", LINKEDIN_EMAIL)
          self.page.fill("#password", LINKEDIN_PASSWORD)
          
          print("Clicking login button...")
          self.page.click('button[type="submit"]')
          
          # Wait for navigation and check for successful login
          try:
              time.sleep(3)
              # Wait for either the feed page or an error message
              #self.page.wait_for_selector('div[data-test-id="feed-nav-item"], div[error-for="username"]', timeout=5000)
              
              if "feed" in self.page.url:
                  print("Login successful!")
                  self.state["logged_in"] = True
              else:
                  print("Login failed. Please check your credentials.")
                  self.state["logged_in"] = False
          except Exception as e:
              print(f"Error during login: {str(e)}")
              self.state["logged_in"] = False
      else:
          print("Already logged in.")
          self.state["logged_in"] = True

      self.state["last_url"] = self.page.url
      self.save_state()
  def safe_navigate(self, url):
        try:
            self.page.goto(url)
            self.page.wait_for_load_state('domcontentloaded')
        except Exception as e:
            print(f"Error navigating to {url}: {str(e)}")
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

            self.page.wait_for_timeout(500)

        except Exception as e:
            print(f"Error applying distance filter: {str(e)}")
  def label_contains(label, *keywords):
    label = label.lower()
    return any(keyword.lower() in label for keyword in keywords) or any(label in keyword.lower() for keyword in keywords)
  def get_options(self, element, element_type, element_tag):
    options = []
    if element_type in ['radio', 'checkbox']:
        option_elements = element.evaluate('el => el.closest("fieldset").querySelectorAll("input[type=\'' + element_type + '\']")')
    elif element_tag == 'select':
        option_elements = element.query_selector_all('option')
    else:  # for other group types
        option_elements = element.query_selector_all('input')
    
    for option in option_elements:
        option_id = option.get_attribute('id')
        option_label = self.page.query_selector(f'label[for="{option_id}"]')
        option_text = option_label.inner_text() if option_label else "No label"
        option_value = option.get_attribute('value')
        options.append({"id": option_id, "label": option_text, "value": option_value})
    
    return options
  def scroll_to_load_jobs(self, index):
        self.page.evaluate(f"window.scrollTo(0, {index * 100})")
        self.page.wait_for_timeout(500)
  def find_label(self, element):
    # First, try to find a label associated with the element's ID
    element_id = element.get_attribute('id')
    label = self.page.query_selector(f'label[for="{element_id}"]')
    if label:
        return label.inner_text()

    # If no label is found, look for a parent fieldset with a legend
    parent_fieldset = element.evaluate('el => el.closest("fieldset")')
    if parent_fieldset:
        legend = parent_fieldset.query_selector('legend')
        if legend:
            return legend.inner_text()

    # If still no label, look for any preceding label or div that might contain label text
    preceding_label = element.evaluate('el => el.previousElementSibling')
    if preceding_label:
        if preceding_label.get_attribute('tagName').lower() == 'label':
            return preceding_label.inner_text()
        elif preceding_label.get_attribute('tagName').lower() == 'div':
            label_div = preceding_label.query_selector('label, span')
            if label_div:
                return label_div.inner_text()

    # If all else fails, return a default message
    return "No label found"  

  def scan_application(self):
    print("Scanning application form...")
    form_data = []
    
    try:
        easy_apply_overlay = self.page.query_selector('div[class="jobs-easy-apply-content"]')
        
        if not easy_apply_overlay:
            print("Easy Apply overlay not found.")
            return form_data

        form_elements = easy_apply_overlay.query_selector_all('input, textarea, select, div[role="radiogroup"], div[role="group"]')
        print(f"Found {len(form_elements)} form elements.")

        for index, element in enumerate(form_elements, 1):
            try:
                element_id = element.get_attribute('id')
                element_tag = element.evaluate('el => el.tagName.toLowerCase()')
                element_type = element.get_attribute('type') or element_tag

                print(f"\nProcessing element {index}/{len(form_elements)}:")
                print(f"Element ID: {element_id}")
                print(f"Element Tag: {element_tag}")
                print(f"Element Type: {element_type}")

                # Find the label
                label_text = self.find_label(element)

                # Handle groups (radio, checkbox, select)
                if element_type in ['radio', 'checkbox'] or element_tag == 'select' or element.get_attribute('role') in ['radiogroup', 'group']:
                    options = self.get_options(element, element_type, element_tag)
                else:
                    options = None

                element_data = {
                    "element_id": element_id,
                    "element_tag": element_tag,
                    "element_type": element_type,
                    "label": label_text,
                    "options": options
                }

                if element_type in ['radio', 'checkbox']:
                    element_data["access_method"] = f"self.page.check('#{options[0]['id']}')" if options else "No options found"
                elif element_type in ['text', 'textarea', 'email', 'tel', 'url']:
                    element_data["access_method"] = f"self.page.fill('#{element_id}', 'Your text here')"
                elif element_tag == 'select':
                    element_data["access_method"] = f"self.page.select_option('#{element_id}', value='{options[0]['value']}')" if options else "No options found"
                else:
                    element_data["access_method"] = f"Unsupported element type: {element_type}"

                print(f"Label: {label_text}")
                print(f"Access method: {element_data['access_method']}")
                if options:
                    print(f"Options: {options}")
                print("---")

                form_data.append(element_data)

            except Exception as e:
                print(f"Error processing element {index}: {str(e)}")


            # Check for file upload inputs
            file_inputs = easy_apply_overlay.query_selector_all('input[type="file"]')
            print(f"\nFound {len(file_inputs)} file upload inputs.")
            for index, file_input in enumerate(file_inputs, 1):
                try:
                    file_input_id = file_input.get_attribute('id')
                    print(f"\nFile Upload Input {index}:")
                    print(f"ID: {file_input_id}")
                    print(f"Access method: self.page.set_input_files('#{file_input_id}', 'path/to/your/file.pdf')")
                except Exception as e:
                    print(f"Error processing file input {index}: {str(e)}")

            # Check for submit button
            submit_button = easy_apply_overlay.query_selector('button[type="submit"]')
            if submit_button:
                try:
                    submit_button_text = submit_button.inner_text()
                    print(f"\nSubmit Button found: {submit_button_text}")
                    print(f"Access method: self.page.click('button[type=\"submit\"]')")
                except Exception as e:
                    print(f"Error processing submit button: {str(e)}")
            else:
                print("\nNo submit button found.")

            # Check for Review button
            review_button = easy_apply_overlay.query_selector('button[aria-label="Review your application"]')
            if review_button:
                try:
                    review_button_text = review_button.inner_text()
                    print(f"\nReview Button found: {review_button_text}")
                    print(f"Access method: self.page.click('button[aria-label=\"Review your application\"]')")
                except Exception as e:
                    print(f"Error processing review button: {str(e)}")
            else:
                print("\nNo review button found.")

            # Check for Next button
            next_button = easy_apply_overlay.query_selector('button[aria-label="Continue to next step"]')
            if next_button:
                try:
                    next_button_text = next_button.inner_text()
                    print(f"\nNext Button found: {next_button_text}")
                    print(f"Access method: self.page.click('button[aria-label=\"Continue to next step\"]')")
                except Exception as e:
                    print(f"Error processing next button: {str(e)}")
            else:
                print("\nNo next button found.")

    except Exception as e:
            print(f"Error scanning application: {str(e)}")

    return form_data

  def fill_application(self):
    # Load user data
    with open('user_data.json', 'r') as f:
        user_data = json.load(f)

    while True:
        # Scan the current page of the application
        form_elements = self.scan_application()

        # Flag to check if any field was filled
        filled_any = False

        for element in form_elements:
            label = element['label'].lower()
            element_type = element['element_type']
            element_tag = element['element_tag']
            options = element.get('options', [])

            def label_contains(*keywords):
                return any(keyword.lower() in label for keyword in keywords) or any(label in keyword.lower() for keyword in keywords)

            try:
                if label_contains('email') and 'email' in user_data:
                    if element_tag == 'select':
                        self.select_option_by_value(element, user_data['email'])
                    else:
                        self.page.fill(f"#{element['element_id']}", user_data['email'])
                    filled_any = True
                    print(f"Filled email: {user_data['email']}")

                elif label_contains('phone', 'country', 'code') and 'phone_country_code' in user_data:
                    self.select_option_by_value(element, user_data['phone_country_code'])
                    filled_any = True
                    print(f"Selected phone country code: {user_data['phone_country_code']}")

                elif label_contains('phone', 'number', 'mobile') and 'phone_number' in user_data:
                    self.page.fill(f"#{element['element_id']}", user_data['phone_number'])
                    filled_any = True
                    print(f"Filled phone number: {user_data['phone_number']}")

                elif label_contains('follow', 'company') and 'follow_company' in user_data:
                    if user_data['follow_company']:
                        self.page.check(f"#{element['element_id']}")
                    filled_any = True

                elif label_contains('city', 'location') and 'city' in user_data:
                    self.page.fill(f"#{element['element_id']}", user_data['city'])
                    filled_any = True

                elif label_contains('cover', 'letter'):
                    if element_type == 'file' and 'cover_letter_path' in user_data:
                        self.page.set_input_files(f"#{element['element_id']}", user_data['cover_letter_path'])
                    elif element_type == 'checkbox' and 'used_cover' in user_data:
                        if user_data['used_cover']:
                            self.page.check(f"#{element['element_id']}")
                    filled_any = True

                elif label_contains('disability', 'impairment') and 'disability' in user_data:
                    if options:
                        self.select_option_by_label(element, user_data['disability']['status'])
                    elif element_type == 'textarea' and label_contains('describe'):
                        self.page.fill(f"#{element['element_id']}", user_data['disability']['description'])
                    filled_any = True

                elif label_contains('hear', 'about', 'job') and 'hear_about_job' in user_data:
                    self.select_option_by_label(element, user_data['hear_about_job'])
                    filled_any = True

                elif label_contains('right', 'to', 'work') and 'right_to_work' in user_data:
                    self.select_option_by_label(element, user_data['right_to_work'])
                    filled_any = True

                elif label_contains('living', 'in', 'uk') and 'living_in_uk' in user_data:
                    self.select_option_by_label(element, user_data['living_in_uk'])
                    filled_any = True

                elif label_contains('notice', 'period') and 'notice_period' in user_data:
                    self.select_option_by_label(element, user_data['notice_period'])
                    filled_any = True

                elif label_contains('experience', 'level') and 'experience_level' in user_data:
                    self.select_option_by_label(element, user_data['experience_level'])
                    filled_any = True

                elif label_contains('gender') and 'gender' in user_data:
                    self.select_option_by_label(element, user_data['gender'])
                    filled_any = True

                elif label_contains('ethnicity') and 'ethnicity' in user_data:
                    self.select_option_by_label(element, user_data['ethnicity'])
                    filled_any = True

                elif label_contains('sexual', 'orientation') and 'sexual_orientation' in user_data:
                    self.select_option_by_label(element, user_data['sexual_orientation'])
                    filled_any = True

                elif label_contains('driving', 'license') and 'driving_license' in user_data:
                    self.select_option_by_label(element, user_data['driving_license'])
                    filled_any = True

                elif (label_contains('years', 'experience') or label_contains('years', 'work', 'experience')) and ('years_of_experience' in user_data or 'years of work experience' in user_data):
                    value = user_data.get('years_of_experience') or user_data.get('years of work experience')
                    if element_tag == 'select':
                        self.select_option_by_value(element, value)
                    elif element_type == 'text':
                        self.page.fill(f"#{element['element_id']}", value)
                    filled_any = True

                else:
                    # Default behavior for unmatched fields
                    if options:
                        default_option = next((opt for opt in options if opt['label'].lower() in ['no', '0', 'none', 'prefer not to say']), options[0])
                        if element_type in ['radio', 'checkbox']:
                            self.page.check(f"#{default_option['id']}")
                        elif element_tag == 'select':
                            self.page.select_option(f"#{element['element_id']}", value=default_option['value'])
                        print(f"Filled unmatched field '{label}' with default option: {default_option['label']}")
                        filled_any = True

            except Exception as e:
                print(f"Error filling field {element['label']}: {str(e)}")

        # Check for next or review button
        next_button = self.page.query_selector('button[aria-label="Continue to next step"]')
        if next_button:
            next_button.click()
            print("Clicked Next button")
            # Wait for navigation to complete
            self.page.wait_for_load_state('networkidle')
            continue

        # Check for submit button
        submit_button = self.page.query_selector('button[type="submit"]')
        if submit_button:
            submit_button.click()
            print("Clicked Submit button")
            # Wait for navigation to complete
            self.page.wait_for_load_state('networkidle')
            break

        # If no fields were filled and no buttons were found, we're done
        if not filled_any:
            print("No more fields to fill")
            break

    print("Application submission complete")

  def select_option_by_label(self, element, user_value):
        options = element.get('options', [])
        if not options:
            print(f"No options found for element: {element['label']}")
            return

        matching_option = next((opt for opt in options if user_value.lower() in opt['label'].lower()), None)
        if not matching_option:
            print(f"No matching option found for {user_value} in {element['label']}")
            return

        if element['element_type'] in ['radio', 'checkbox']:
            self.page.check(f"#{matching_option['id']}")
        elif element['element_tag'] == 'select':
            self.page.select_option(f"#{element['element_id']}", value=matching_option['value'])
        
        print(f"Selected option '{matching_option['label']}' for field '{element['label']}'")

  def select_option_by_value(self, element, user_value):
        options = element.get('options', [])
        if not options:
            print(f"No options found for element: {element['label']}")
            return

        matching_option = next((opt for opt in options if user_value.lower() in opt['value'].lower()), None)
        if not matching_option:
            print(f"No matching option found for {user_value} in {element['label']}")
            return

        if element['element_type'] in ['radio', 'checkbox']:
            self.page.check(f"#{matching_option['id']}")
        elif element['element_tag'] == 'select':
            self.page.select_option(f"#{element['element_id']}", value=matching_option['value'])
        
        print(f"Selected option '{matching_option['value']}' for field '{element['label']}'")
  def apply_to_jobs(self, num_applications=5, location=None, distance=None, user_data_file='user_data.json'):
        if location:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location={location}")
            if distance:
                self.apply_distance_filter(distance)
        else:
            self.safe_navigate(f"https://www.linkedin.com/jobs/search/?keywords={self.job_title}&location=United Kingdom")

        self.page.wait_for_selector('div.job-card-container', timeout=3000)

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
                self.page.wait_for_selector('.job-details-jobs-unified-top-card__job-title', timeout=2000)
                
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
                

                if job_id == "4000479714" or job_id == "4014337142":
                    print(f"Found target job with ID: {job_id}")
                    
                    easy_apply_button = self.page.query_selector('button.jobs-apply-button')
                    if easy_apply_button:
                        easy_apply_button.click()
                        print("Clicked Easy Apply button")
                        
                        self.page.wait_for_selector('div.jobs-easy-apply-content', timeout=2500)
                        time.sleep(1)
                        
                        self.fill_application()
                    else:
                        print("Easy Apply button not found for the target job")
                
            except Exception as e:
                print(f"Error analyzing job {i+1}: {str(e)}")
            
            self.page.wait_for_timeout(1000)

        print("Job card analysis complete.")
        return job_data_list

  def run(self):
    self.login()
    job_title = "Data architect"
    location = "Sheffield"
    distance = "25"
    self.job_title = job_title
    self.apply_to_jobs(num_applications=10, location=location, distance=distance, user_data_file='user_data.json')

      

# Usage
if __name__ == "__main__":
  bot = LinkedInJobBot()
  bot.run()

# Created/Modified files during execution:
print("linkedin_bot_state.json")