import requests
import json
import logging

# Configure logging to output to the terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)

BASE_URL = 'https://www.sfu.ca/bin/wcm/course-outlines'
API_PARAMS = {
    'year': '2025',
    'term': 'spring'
}

def fetch_json(url):
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            logging.error(f'Failed to parse JSON from {url}')
            return None
    else:
        logging.error(f'Failed to fetch data from {url}: {response.status_code}')
        return None

def main():
    data = {}

    # Fetch departments
    departments_url = f'{BASE_URL}?{API_PARAMS["year"]}/{API_PARAMS["term"]}'
    departments = fetch_json(departments_url)

    if departments:
        for department in departments:
            department_name = department.get('text', 'unknown')
            logging.info(f'Processing department: {department_name}')
            data[department_name] = {}

            # Fetch courses
            courses_url = f'{BASE_URL}?{API_PARAMS["year"]}/{API_PARAMS["term"]}/{department_name}'
            courses = fetch_json(courses_url)

            if courses:
                for course in courses:
                    course_number = course.get('value', 'unknown')
                    course_title = course.get('text', 'unknown')
                    logging.info(f'Processing course: {course_title} ({course_number}) under {department_name}')
                    data[department_name][f'{course_title} ({course_number})'] = {}

                    # Fetch sections
                    sections_url = f'{BASE_URL}?{API_PARAMS["year"]}/{API_PARAMS["term"]}/{department_name}/{course_number}'
                    sections = fetch_json(sections_url)

                    if sections:
                        for section in sections:
                            section_code = section.get('value', 'unknown')
                            section_title = section.get('text', 'unknown')
                            logging.info(f'Processing section: {section_title} ({section_code}) under {course_title} ({course_number})')
                            section_url = f'{BASE_URL}?{API_PARAMS["year"]}/{API_PARAMS["term"]}/{department_name}/{course_number}/{section_code}'
                            section_details = fetch_json(section_url)

                            if section_details:
                                data[department_name][f'{course_title} ({course_number})'][section_code] = section_details

    with open('sfu_courses_api.json', 'w') as f:
        json.dump(data, f, indent=4)
        logging.info('Data successfully written to sfu_courses_api.json')

if __name__ == '__main__':
    main()
