# LinkedIn Job Application Automator

This project automates the process of applying to jobs on LinkedIn using Python and Playwright. It handles the entire application process including login, job search, and form filling.

## Features

- Automated LinkedIn login with session persistence
- Job search with customizable filters (location, distance, etc.)
- Automatic form filling for job applications
- Support for UK diversity forms
- Automatic cover letter generation using GPT
- Smart handling of various application fields
- Progress tracking and error handling

## Prerequisites

- Python 3.8+
- A LinkedIn account
- OpenAI API key (for cover letter generation)
- Chrome/Chromium browser

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/linkedin-job-automator.git
cd linkedin-job-automator
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Create a `.env` file in the project root (see Configuration section)

5. Create a `user_data.json` file with your profile information (see User Data section)

## Configuration

Create a `.env` file in the project root with the following variables:

```env
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password
OPENAI_API_KEY=your_openai_api_key
```

## User Data

Create a `user_data.json` file with your profile information:

```json
{
    "email": "your.email@example.com",
    "phone_country_code": "+44",
    "phone_number": "1234567890",
    "address": "Your Full Address",
    "city": "Your City",
    "driving_license": "Yes",
    "salary": "25000",
    "used_cover": false,
    "right_to_work": "British Citizen",
    "living_in_uk": "Yes",
    "notice_period": "Immediately",
    "experience_level": "Entry Level",
    "sc_clearance": "No",
    "willing": "Yes",
    "gender": "Prefer not to say",
    "ethnicity": "Prefer not to say",
    "sexual_orientation": "Prefer not to say",
    "disability": {
        "status": "No",
        "description": ""
    },
    "hear_about_job": "LinkedIn"
}
```

## Required Files

1. Place your CV in the project directory as `cv.pdf`
2. The script will generate a `cover.pdf` automatically for each application

## Usage

Run the script:
```bash
python sel.py
```

The script will:
1. Log into LinkedIn using your credentials
2. Search for jobs based on configured criteria
3. Apply to jobs that match your preferences
4. Generate and attach cover letters automatically
5. Fill in application forms with your provided information

## Customization

You can modify the following in `sel.py`:
- Job search criteria (title, location, distance)
- Number of applications to submit
- Application preferences and behaviors

## Notes

- The script uses session persistence to avoid frequent logins
- It includes smart error handling and retry mechanisms
- The cover letter generation uses GPT for customization
- The script respects LinkedIn's UI/UX patterns and includes delays to avoid detection

## Security

- Never commit your `.env` file or `user_data.json` to version control
- Keep your API keys and credentials secure
- The script stores session data locally for persistence

## Troubleshooting

If you encounter issues:
1. Ensure all environment variables are set correctly
2. Check that your LinkedIn credentials are valid
3. Verify your OpenAI API key is active
4. Make sure your CV file is present and readable
5. Check the console output for specific error messages

## Contributing

Feel free to submit issues and enhancement requests!

## License

[MIT License](LICENSE)

## Disclaimer

This tool is for educational purposes only. Use it responsibly and in accordance with LinkedIn's terms of service. 