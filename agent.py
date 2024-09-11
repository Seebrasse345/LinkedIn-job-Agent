import os
import subprocess
from openai import OpenAI
import sys
import datetime
import logging
from pdfminer.high_level import extract_text
import json
import markdown
import pdfkit
import PyPDF2
import io
import io
import re
def run_cmd(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Agent:
  def __init__(self, api_key=None, model="gpt-4o-mini", additional_tools=None):
      self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
      if not self.api_key:
          raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable")
      self.model = model
      self.additional_tools = additional_tools or []
      self.client = OpenAI(api_key=self.api_key)

      # Set up logging with UTF-8 encoding
      self.logger = logging.getLogger('Agent')
      self.logger.setLevel(logging.INFO)
      file_handler = logging.FileHandler('agent.log', encoding='utf-8')
      file_handler.setLevel(logging.INFO)
      
      formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
      file_handler.setFormatter(formatter)
      self.logger.addHandler(file_handler)

      # Add a stream handler for console output
      console_handler = logging.StreamHandler(sys.stdout)
      console_handler.setLevel(logging.INFO)
      console_handler.setFormatter(formatter)
      self.logger.addHandler(console_handler)
      self.system_prompt = f"""
        You are an expert AI agent specializing in crafting outstanding, ATS-optimized cover letters. Your goal is to create compelling, tailored cover letters that showcase the applicant's qualifications and increase their chances of securing an interview. Follow these comprehensive guidelines:

        1. Analysis and Preparation:
        - Thoroughly analyze the job description, identifying key requirements, skills, and company values.
        - Carefully review the applicant's CV/resume to identify relevant experiences and achievements.
        - Research the company to understand its culture, mission, and recent developments.

        2. Cover Letter Structure and Format:
        - Never include empty brackets or templates for the user to fill in fill this in yourself  in the cover letter or if the information is not provided just leave it and move on
        - Never include the following empty fields[Date] [Hiring Manager's Name][Company Name][Company Address] 
        - Use a clean, professional format with clear sections.
        - Include the applicant's contact information at the top.
        - Address the letter to a specific person if possible, or use "Dear Hiring Manager,".
        - Organize content into 3-4 concise paragraphs.
        - End with "Sincerely," followed by the applicant's full name.
        - Aim for 250-400 words to maintain readability and impact.


        3. Content Strategy:
        - Opening: Start with a strong, attention-grabbing statement that shows enthusiasm for the position.
        - Body:
          * Paragraph 1: Clearly state the position you're applying for and how you learned about it.
          * Paragraph 2-3: Highlight 2-3 key achievements or experiences that directly relate to the job requirements. Use specific metrics and outcomes where possible.
          * Final Paragraph: Express enthusiasm for the role and company, and request an interview.
        - Closing: Thank the reader for their time and consideration.

        4. ATS Optimization:
        - Incorporate key job-specific keywords and phrases naturally throughout the letter.
        - Use standard section headings that ATS can easily parse.
        - Avoid using tables, images, or complex formatting that may confuse ATS.
        - Use common fonts like Arial, Calibri, or Times New Roman.

        5. Language and Tone:
        - Use clear, concise, and professional language.
        - Strike a balance between confidence and humility.
        - Tailor the tone to match the company's culture (e.g., formal for traditional industries, more casual for startups).
        - Use active voice and strong action verbs.
        - Avoid clichés and generic statements; focus on unique value proposition.
        - Make sure the language sounds natural and not robotic or unnaturally worded. Make it sound human.

        6. Customization and Relevance:
        - Demonstrate knowledge of the company and explain why you're interested in this specific role.
        - Align your skills and experiences with the job requirements and company values.
        - Address any potential concerns (e.g., career changes, employment gaps) proactively and positively.

        7. Proofreading and Refinement:
        - Ensure perfect grammar, spelling, and punctuation.
        - Eliminate redundancies and filler words for maximum impact.
        - Verify that all company and position details are accurate.
        - Make sure all the skills and information in the cover letter alings with that of the cv information
        

        8. Markdown Formatting:
        - Use markdown to structure the cover letter for clarity and ATS-friendliness:
          * # for the applicant's name at the top
          * ## for main section headings (if used)
          * **bold** for emphasis on key points (use sparingly)
          * Ensure proper line breaks between paragraphs


        Remember, your ultimate goal is to create a cover letter that not only passes ATS screening but also compels human readers to invite the applicant for an interview. Tailor each letter to showcase the applicant as the ideal candidate for the specific position and company.
        """

      self.assistant_no_tools = self.client.beta.assistants.create(
            name="Advanced Cover Letter Generator Agent",
            instructions=self.system_prompt,
            model=model,
            tools=[]
        )
      self.system_prompt_2 = self.system_prompt + " 9. Use tools to formalize and submit the document in pdf, Make SURE THAT ONCE THE TASK IS FINISHED YOU USE THE FINISH TASK TOOL "
      self.assistant_with_tools = self.client.beta.assistants.create(
          name="Cover Letter Generator Agent (With Tools)",
          instructions=self.system_prompt_2,  # Add your own instructions here
          model=model,
          tools=[
              {"type": "function", "function": {"name": "file_operations", "description": "Performs file operations like read, write, list, or delete", "parameters": {"type": "object", "properties": {"operation": {"type": "string", "enum": ["read", "write", "list", "delete"], "description": "The operation to perform"}, "path": {"type": "string", "description": "The file or directory path"}, "content": {"type": "string", "description": "Content to write (for write operation)"}}, "required": ["operation", "path"]}}},
              {"type": "function", "function": {"name": "markdown_to_pdf", "description": "Converts markdown content to PDF and saves it as cover.pdf in the current directory", "parameters": {"type": "object", "properties": {"markdown_content": {"type": "string", "description": "The markdown content to convert"}}, "required": ["markdown_content"]}}},
              {"type": "function", "function": {"name": "finish_task", "description": "Signals that the current task is finished", "parameters": {"type": "object", "properties": {"message": {"type": "string", "description": "A message summarizing task completion"}}, "required": ["message"]}}},
          ]
      )
      self.thread = None
      self.task_finished = False

  def log_and_print(self, message):
        timestamp = get_timestamp()
        full_message = f"[{timestamp}] {message}"
        try:
            self.logger.info(full_message)
        except UnicodeEncodeError:
            # If encoding fails, try to encode as UTF-8 and replace problematic characters
            encoded_message = full_message.encode('utf-8', errors='replace').decode('utf-8')
            self.logger.info(encoded_message)

  def file_operations(self, operation, path, content=None):
        try:
            if operation == "read":
                with open(path, 'r', encoding='utf-8') as file:
                    return file.read()
            elif operation == "write":
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return f"Successfully wrote to {path}"
            elif operation == "list":
                return str(os.listdir(path))
            elif operation == "delete":
                os.remove(path)
                return f"Successfully deleted {path}"
        except Exception as e:
            return f"Error in file operation: {str(e)}"

  def markdown_to_pdf(self, markdown_content):
        output_path = "cover.pdf"
        try:
            # Remove empty fields enclosed in brackets, including bolded ones
            cleaned_content = re.sub(r'\*?\*\[.*?\]\*?\*', '', markdown_content)
            cleaned_content = re.sub(r'\[.*?\]', '', cleaned_content)

            # Remove any remaining empty lines
            #cleaned_content = '\n'.join([line for line in cleaned_content.split('\n') if line.strip()])

            html_content = markdown.markdown(cleaned_content)
            # Use UTF-8 encoding for pdfkit
            pdfkit.from_string(html_content, output_path, options={'encoding': "UTF-8"})
            return f"Successfully created PDF at {output_path}"
        except Exception as e:
            return f"Error in creating PDF: {str(e)}"

  def autobot(self, initial_input=None):
    if not self.thread:
        self.thread = self.client.beta.threads.create()

    self.log_and_print("Cover Letter Generator Agent is running. Type 'exit' to quit.")

    if initial_input:
        user_input = initial_input
    else:
        user_input = input("You: ")

    # Automatic message to double-check the cover letter after the initial input
    double_check_message = """
        Please review the initial cover letter draft. Analyze and critique it based on the following criteria:
        - Is the cover letter appropriate for the job?
        - Are there any improvements that can be made in terms of language, structure, or content?
        - Are all facts accurate?
        - Is the formatting for markdown correctly done?
        - Is the formatting ATS-friendly and visually appealing?
        - Could any more appropriate skills or achievements be added?
        - Is all the information factual, Additionally have you matched the right project to the right qualification?
        - Have you used the right keywords and phrases? 
        - Does it sound human and not robotic? Natural and proffesional

        After analyzing, implement the improvements required and finalize the document.
    """

    try:
        self.log_and_print(f"User: {user_input}")
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=user_input
        )

        # Run the assistant for the first draft (without tool access)
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_no_tools.id
        )

        # Wait for the assistant to finish the first draft
        while run.status not in ["completed", "failed"]:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )

        # Fetch the first assistant message (cover letter draft)
        messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
        first_draft = ""
        for message in reversed(messages.data):
            if message.role == "assistant":
                first_draft = message.content[0].text.value
                self.log_and_print(f"Assistant (First Draft): {first_draft}")
                break

        # Automatically send the double-check message
        self.log_and_print(f"Sending automatic double-check request: {double_check_message}")
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=double_check_message
        )

        # Now, the assistant will critique and suggest improvements (WITH tool access)
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_with_tools.id
        )

        tool_outputs = []
        expected_tool_call_ids = set()

        # Wait for the assistant to critique and suggest changes
        while run.status not in ["completed", "failed"]:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )

            # Execute tool calls after critique, as tools are now enabled
            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                expected_tool_call_ids = set(tool_call.id for tool_call in tool_calls)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name == "file_operations":
                        output = self.file_operations(**function_args)
                    elif function_name == "markdown_to_pdf":
                        output = self.markdown_to_pdf(**function_args)
                    elif function_name == "finish_task":
                        self.task_finished = True
                        output = f"Task finished: {function_args['message']}"
                    else:
                        output = f"Unknown function: {function_name}"

                    self.log_and_print(f"Executing {function_name}: {function_args}")
                    self.log_and_print(f"Output: {output}")

                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": output
                    })

                # Filter tool outputs to only include expected call IDs
                filtered_tool_outputs = [
                    output for output in tool_outputs 
                    if output["tool_call_id"] in expected_tool_call_ids
                ]

                # Submit the tool outputs after all tools have been run
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=filtered_tool_outputs
                )

                # Clear tool outputs after submission
                tool_outputs = []

        # Fetch all messages after the second agent has completed
        messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
        full_conversation = ""
        for message in messages.data:
            role = message.role
            content = message.content[0].text.value
            full_conversation += f"{role.capitalize()}: {content}\n\n"

        self.log_and_print("Full conversation after second agent completion:")
        self.log_and_print(full_conversation)

        # Exit the loop and function once the task is finished
        if self.task_finished:
            self.log_and_print("Task finished. Exiting the autobot function.")
            return

        if not initial_input:
            user_input = input("You: ")
        else:
            return

    except Exception as e:
        self.log_and_print(f"An error occurred: {str(e)}")
        if not initial_input:
            user_input = input("You: ")
        else:
            return

                
                
                
                
    
     
#def main():
  #  agent = Agent(api_key="sk-vMxk-Z_yIcJhqOaK-GE2GoutLsw050TWhJWz1H-sazT3BlbkFJQgZUueDhTOvSX2jWBfBXVOQLpmBppxhG3reY68ZXYA", model="gpt-4o-mini")
   # agent.create_cover_letter()
    

#if __name__ == "__main__":
    #main()
