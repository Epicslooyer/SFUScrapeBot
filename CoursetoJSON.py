import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_department_links(base_url):
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        department_links = []

        # Find all ul elements that contain department links
        for ul in soup.find_all('ul'):
            # Look for links within each ul
            for link in ul.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if it's a valid department link
                if (href.startswith('/students/calendar/2025/spring/courses/') and 
                    href.endswith('.html') and
                    len(href.split('/')) == 7):  # Ensure it's a department page
                    
                    # Create full URL
                    full_url = urljoin('https://www.sfu.ca', href)
                    
                    if full_url not in department_links:
                        department_links.append(full_url)
                        logger.info(f"Found department: {text}")

        logger.info(f"Found {len(department_links)} unique department links")
        return department_links
    except Exception as e:
        logger.error(f"Error getting department links: {str(e)}")
        return []

def get_course_links(department_url):
    try:
        response = requests.get(department_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        course_links = []

        # Find all option elements with data-href attributes
        for option in soup.find_all('option', attrs={'data-href': True}):
            href = option.get('data-href', '')
            course_text = option.get_text(strip=True)
            
            if href and '/courses/' in href:
                # Create full URL
                course_url = urljoin('https://www.sfu.ca', href)
                if course_url not in course_links:
                    course_links.append(course_url)
                    logger.info(f"Found course: {course_text}")

        if not course_links:
            logger.warning(f"No course links found in {department_url}")
            
        return course_links
    except Exception as e:
        logger.error(f"Error getting course links from {department_url}: {str(e)}")
        return []

def get_course_details(course_url):
    try:
        response = requests.get(course_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the main section using section tag with class "main"
        main_section = soup.find('section', class_='main')
        if not main_section:
            logger.error(f"Could not find main section for {course_url}")
            return None

        course_details = {}

        # Get course name - need to combine the h1 text and the course number
        course_title = main_section.find('h1')
        if not course_title:
            logger.error(f"Could not find course title (h1) for {course_url}")
            return None

        # Get the main title (excluding the small tag content)
        title_text = ''.join(text for text in course_title.stripped_strings if text not in course_title.small.stripped_strings) if course_title.small else course_title.text
        
        # Get the course number from small tag
        course_number = course_title.find('small', class_='course_number')
        course_code = f"[{' '.join(course_number.stripped_strings)}]" if course_number else ""
        
        course_details['course_name'] = f"{title_text.strip()} {course_code}".strip()
        logger.info(f"Successfully extracted course name: {course_details['course_name']}")

        # Get course description - it's the first p tag after h1
        description = main_section.find('h1').find_next_sibling('p')
        if not description:
            logger.error(f"Could not find course description for {course_url}")
            return None
            
        course_details['description'] = description.text.strip()
        logger.info(f"Successfully extracted course description (length: {len(course_details['description'])})")

        # Get course sections
        course_details['sections'] = []
        sections_div = main_section.find('div', class_='course-sections')
        if sections_div:
            table = sections_div.find('table')
            if table:
                rows = table.find_all('tr')[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        section = {
                            'section': cells[0].text.strip(),
                            'instructor': cells[1].text.strip(),
                            'day/time': cells[2].text.strip(),
                            'location': cells[3].text.strip()
                        }
                        course_details['sections'].append(section)
            
            logger.info(f"Successfully extracted {len(course_details['sections'])} course sections")
        else:
            logger.warning(f"No course sections found for {course_url}")

        return course_details

    except Exception as e:
        logger.error(f"Error processing course {course_url}: {str(e)}")
        return None

def scrape_sfu_courses():
    #If using in a different semester, replace "2025" with the desired year and corresponding semester, SHOLD WORK
    base_url = "https://www.sfu.ca/students/calendar/2025/spring/courses.html"
    all_courses = []
    
    try:
        # Load existing data if any
        try:
            with open('sfu_courses.json', 'r', encoding='utf-8') as f:
                all_courses = json.load(f)
            logger.info(f"Loaded {len(all_courses)} existing courses from file")
        except FileNotFoundError:
            logger.info("No existing courses file found, starting fresh")

        # Get all department links
        department_links = get_department_links(base_url)
        
        # Process each department
        for department_url in department_links:
            logger.info(f"Processing department: {department_url}")
            time.sleep(1)  # Polite delay between requests
            
            # Get all course links for this department
            course_links = get_course_links(department_url)
            
            # Process each course
            for course_url in course_links:
                # Skip if we already have this course
                if any(course.get('url') == course_url for course in all_courses):
                    logger.info(f"Skipping already processed course: {course_url}")
                    continue
                
                logger.info(f"Processing course: {course_url}")
                time.sleep(1)  # Polite delay between requests
                
                course_details = get_course_details(course_url)
                if course_details:
                    all_courses.append(course_details)
                    logger.info(f"Added course details. Total courses: {len(all_courses)}")
                    
                    # Save progress periodically (every 10 courses)
                    if len(all_courses) % 10 == 0:
                        with open('sfu_courses.json', 'w', encoding='utf-8') as f:
                            json.dump(all_courses, f, indent=2, ensure_ascii=False)
                else:
                    logger.warning(f"Skipped course {course_url} due to missing details")

        # Final save
        with open('sfu_courses.json', 'w', encoding='utf-8') as f:
            json.dump(all_courses, f, indent=2, ensure_ascii=False)

        logger.info(f"Scraping complete. Total courses collected: {len(all_courses)}")
        return all_courses

    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}")
        # Save whatever we have so far
        if all_courses:
            with open('sfu_courses.json', 'w', encoding='utf-8') as f:
                json.dump(all_courses, f, indent=2, ensure_ascii=False)
        return all_courses

if __name__ == "__main__":
    courses = scrape_sfu_courses()
    
