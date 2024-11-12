import discord
from discord.ext import commands
import ratemyprofessor
import asyncio
import logging
from queue import Queue
import json
import re
from fuzzywuzzy import process
from collections import defaultdict
import os
import aiohttp
from typing import Optional, Dict, Any
import concurrent.futures
import subprocess
from functools import partial
import google.generativeai as ga

GeminiAIKey = ""
ModelName= "gemini-1.5-flash"
ga.configure(api_key=GeminiAIKey)
model=ga.GenerativeModel(ModelName)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

departments = defaultdict(list)
course_descriptions = {}

professor_cache = {}
rate_limit_lock=asyncio.Semaphore(1)
OWNER_ID = ""
THREAD_COUNT=6

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    load_course_data()
    logger.info(f'Loaded {len(departments)} departments: {sorted(departments.keys())}')


def process_course_batch(batch):
    results = {}
    for course in batch:
        match = re.search(r'\[([A-Z]+)\s*(\d+)', course['course_name'])
        if match:
            dept, number = match.groups()
            dept = dept.strip()
            number = number.strip()
            course_code = f"{dept} {number}"
            results[course_code] = {
                'name': course['course_name'].split('[')[0].strip(),
                'description': course['description'],
                'sections': course['sections']
            }
    return results


def load_course_data():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'sfu_courses2.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            courses = json.load(f)
        
        batch_size = len(courses) // THREAD_COUNT + 1
        batches = [courses[i:i + batch_size] for i in range(0, len(courses), batch_size)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            results = list(executor.map(process_course_batch, batches))
        
        # Combine results
        departments.clear()
        course_descriptions.clear()
        
        for result in results:
            for course_code, info in result.items():
                dept = course_code.split()[0]
                departments[dept].append(course_code)
                course_descriptions[course_code] = info
        
        logger.info(f"Loaded {len(departments)} departments")
        logger.info(f"Loaded {len(course_descriptions)} courses")
        
    except Exception as e:
        logger.error(f"Error loading course data: {str(e)}")


def get_professor_rating(school, professor_name):
    if not professor_name:
        return {
            'rating': 'N/A',
            'difficulty': 'N/A',
            'would_take_again': 'N/A',
            'num_ratings': 'N/A'
        }
    
    asyncio.sleep(1)
    try:
        prof = ratemyprofessor.get_professor_by_school_and_name(school, professor_name)
        
        if prof:
            return {
                'rating': prof.rating if prof.rating else 'N/A',
                'difficulty': prof.difficulty if prof.difficulty else 'N/A',
                'would_take_again': f"{round(prof.would_take_again, 1)}%" if prof.would_take_again is not None else 'N/A',
                'num_ratings': prof.num_ratings
            }
    except Exception as e:
        logger.error(f"Error getting professor rating for {professor_name}: {str(e)}")
    
    return {
        'rating': 'Not Found',
        'difficulty': 'Not Found',
        'would_take_again': 'Not Found',
        'num_ratings': 'Not Found'
    }

def get_course_digger_info(course_code):
    """Get course information from local data.txt file"""
    logger.info(f"Fetching course data for {course_code}")
    
    default_response = {
        'median_grade': 'N/A',
        'fail_percentage': 'N/A',
        'course_difficulty': 'N/A'
    }
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'data.txt')
        
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        base_course_code = ' '.join(course_code.split()[:2])
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                file_course = f"{parts[0]} {parts[1]}"
                if file_course == base_course_code:
                    return {
                        'median_grade': parts[2],
                        'fail_percentage': f"{float(parts[3]):.1f}%",
                        'course_difficulty': parts[4] if len(parts) > 4 else 'N/A'
                    }
        
        return default_response
                
    except Exception as e:
        logger.error(f"Error reading course data for {course_code}: {str(e)}")
        return default_response

async def display_departments(ctx):
    """Display all available departments in a formatted message"""
    dept_list = sorted(departments.keys())
    
    if not dept_list:
        await ctx.send("Error: No departments loaded. Please check the course data.")
        return
        
    chunks = [dept_list[i:i + 10] for i in range(0, len(dept_list), 10)]
    
    embed = discord.Embed(
        title="Available Departments",
        description="Please enter the department code from the list below:",
        color=discord.Color.blue()
    )
    
    for i, chunk in enumerate(chunks):
        embed.add_field(
            name=f"Departments {i*10 + 1}-{i*10 + len(chunk)}",
            value="\n".join(chunk),
            inline=True
        )
    
    await ctx.send(embed=embed)

async def display_courses(ctx, dept):
    """Display all courses for a given department"""
    dept = dept.upper().strip()
    if dept not in departments:
        await ctx.send(f"Department '{dept}' not found. Please try again with a valid department code.")
        return None

    courses = sorted(departments[dept])
    embed = discord.Embed(
        title=f"Courses in {dept}",
        description="Please enter the complete course code (e.g., 'ACMA 101'):",
        color=discord.Color.blue()
    )
    
    chunks = [courses[i:i + 15] for i in range(0, len(courses), 15)]
    for i, chunk in enumerate(chunks):
        embed.add_field(
            name=f"Courses {i*15 + 1}-{i*15 + len(chunk)}",
            value="\n".join(chunk),
            inline=True
        )
    
    await ctx.send(embed=embed)
    return dept

def check_author(ctx):
    """Create a check function for waiting for messages"""
    def inner(message):
        return message.author == ctx.author and message.channel == ctx.channel
    return inner

async def get_professor_rating(professor_name: str) -> dict:
    if not professor_name or professor_name.lower() in ['tba', 'staff']:
        return {
            'rating': 'N/A',
            'difficulty': 'N/A',
            'would_take_again': 'N/A',
            'num_ratings': 'N/A'
        }

    if professor_name in professor_cache:
        return professor_cache[professor_name]

    async with rate_limit_lock:
        try:
            await asyncio.sleep(1)
            
            # Get professor rating
            school = ratemyprofessor.get_school_by_name("Simon Fraser University")
            professor = ratemyprofessor.get_professor_by_school_and_name(school, professor_name)
            
            if professor:
                rating = {
                    'rating': f"{professor.rating:.1f}/5.0" if professor.rating else 'N/A',
                    'difficulty': f"{professor.difficulty:.1f}/5.0" if professor.difficulty else 'N/A',
                    'would_take_again': f"{professor.would_take_again}%" if professor.would_take_again is not None else 'N/A',
                    'num_ratings': professor.num_ratings if professor.num_ratings else 0
                }
                professor_cache[professor_name] = rating
                return rating
            
            # Professor not found
            not_found = {
                'rating': 'Not Found',
                'difficulty': 'Not Found',
                'would_take_again': 'Not Found',
                'num_ratings': 0
            }
            professor_cache[professor_name] = not_found
            return not_found

        except Exception as e:
            logger.error(f"Error getting professor rating for {professor_name}: {e}")
            error_rating = {
                'rating': 'Error',
                'difficulty': 'Error',
                'would_take_again': 'Error',
                'num_ratings': 'Error'
            }
            return error_rating

@bot.command(name='dispdept')
async def display_department(ctx):
    await display_departments(ctx)
    
    try:
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        dept_msg = await bot.wait_for('message', timeout=60.0, check=check)
        dept = dept_msg.content.upper().strip()
        
        if dept not in departments:
            await ctx.send(f"Department '{dept}' not found. Please try again with a valid department code.")
            return
        
        courses = sorted(departments[dept])
        
        # Process courses in parallel
        async def process_course(course_code):
            if course_code in course_descriptions:
                course_info = course_descriptions[course_code]
                stats = get_course_digger_info(course_code)
                
                embed = discord.Embed(
                    title=f"{course_code} - {course_info['name']}",
                    description=course_info['description'] or "No description available",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="Median Grade", value=stats['median_grade'], inline=True)
                embed.add_field(name="Fail Percentage", value=stats['fail_percentage'], inline=True)
                
                if course_info['sections']:
                    for section in course_info['sections']:
                        prof_rating = await get_professor_rating(section['instructor'])
                        section_text = (
                            f"**Section {section['section']}**\n"
                            f"Instructor: {section['instructor']}\n"
                            f"Time: {section['day/time']}\n"
                            f"Location: {section['location']}\n"
                            f"\nProfessor Ratings:\n"
                            f"• Rating: {prof_rating['rating']}\n"
                            f"• Difficulty: {prof_rating['difficulty']}\n"
                            f"• Would Take Again: {prof_rating['would_take_again']}\n"
                            f"• Number of Ratings: {prof_rating['num_ratings']}\n"
                        )
                        embed.add_field(name=f"Section Information", value=section_text, inline=False)
                
                return embed
            return None
        
        # Process courses in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(courses), batch_size):
            batch = courses[i:i + batch_size]
            tasks = [process_course(course) for course in batch]
            embeds = await asyncio.gather(*tasks)
            
            for embed in embeds:
                if embed:
                    await ctx.send(embed=embed)
                    await asyncio.sleep(1)
        
    except asyncio.TimeoutError:
        await ctx.send("Selection timed out. Please try again with !dispdept")
    except Exception as e:
        logger.error(f"Error in display_department: {str(e)}")
        await ctx.send("An error occurred while processing your request.")

@bot.command(name='update')
async def update_courses(ctx):
    if ((ctx.message.author.id != "333711357260070914") and (ctx.message.type=="APPLICATION_COMMAND") and (ctx.message.interaction.commandName=="update")):
        await ctx.send("Sorry, only the bot owner can use this command.")
        return
    
    try:
        await ctx.send("Starting course data update...")
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, 'CoursetoJSON.py')
        python_executable = sys.executable

        
        process = await asyncio.create_subprocess_exec(
            python_executable,
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            load_course_data()
            await ctx.send("Course data updated successfully!")
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            await ctx.send(f"Error updating course data: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in update_courses: {str(e)}")
        await ctx.send(f"An error occurred while updating course data: {str(e)}")

@bot.command(name='courses')
async def courses(ctx):
    """Interactive course selection command"""
    try:
        await display_departments(ctx)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            dept_msg = await bot.wait_for('message', timeout=60.0, check=check)
            dept = dept_msg.content.upper()
            
            valid_dept = await display_courses(ctx, dept)
            if not valid_dept:
                return
            
            course_msg = await bot.wait_for('message', timeout=60.0, check=check)
            course_code = course_msg.content.upper()
            
            if course_code in course_descriptions:
                course_info = course_descriptions[course_code]
                stats = get_course_digger_info(course_code)
                
                embed = discord.Embed(
                    title=f"{course_code} - {course_info['name']}",
                    description=course_info['description'] or "No description available",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="Median Grade", value=stats['median_grade'], inline=True)
                embed.add_field(name="Fail Percentage", value=stats['fail_percentage'], inline=True)
                
                if course_info['sections']:
                    for section in course_info['sections']:
                        # Get professor rating using the simplified function
                        prof_rating = await get_professor_rating(section['instructor'])
                        
                        section_text = (
                            f"**Section {section['section']}**\n"
                            f"Instructor: {section['instructor']}\n"
                            f"Time: {section['day/time']}\n"
                            f"Location: {section['location']}\n"
                            f"\nProfessor Ratings:\n"
                            f"• Rating: {prof_rating['rating']}\n"
                            f"• Difficulty: {prof_rating['difficulty']}\n"
                            f"• Would Take Again: {prof_rating['would_take_again']}\n"
                            f"• Number of Ratings: {prof_rating['num_ratings']}\n"
                        )
                        embed.add_field(name=f"Section Information", value=section_text, inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Course '{course_code}' not found. Please try again.")
                
        except asyncio.TimeoutError:
            await ctx.send("Selection timed out. Please try again with !courses")
            
    except Exception as e:
        logger.error(f"Error in courses command: {str(e)}")
        await ctx.send(f"An error occurred while processing your request. Please try again later.")


@bot.command(name='course_help')
async def help_command(ctx):
    help_text = """
**Course Information Bot Commands**

`/courses`
Interactive course selection:
1. View list of departments
2. Enter department code (e.g., "ACMA")
3. View list of courses in department
4. Enter course code (e.g., "ACMA 101")
5. View complete course information:
   • Course name and description
   • Grade statistics (median grade, fail percentage)
   • Section information:
     - Section number
     - Instructor
     - Day/Time
     - Location

`/dispdept`
Display all available departments. Follow the prompt to select a department.

`/update`
Update the course data. Only the bot owner can use this command. You will be prompted to provide the owner's ID if not set.

`/course_help`
Display this help message with information on how to use the bot commands.

Example interaction:
```
/courses
> [Bot shows department list]
ACMA
> [Bot shows ACMA courses]
ACMA 101
> [Bot shows course information]
```
"""
    embed = discord.Embed(
        title="SFUCourseBot",
        description=help_text,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    load_course_data()
    logger.info(f'Loaded {len(departments)} departments: {sorted(departments.keys())}')


if __name__ == "__main__":
    bot.run('') 