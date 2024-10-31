import discord
from discord.ext import commands
import ratemyprofessor
import asyncio
import logging
from queue import Queue
import json
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_professor_rating(school, professor_name):
    if not professor_name:
        return {
            'rating': 'N/A',
            'difficulty': 'N/A',
            'would_take_again': 'N/A',
            'num_ratings': 'N/A'
        }
    
    asyncio.sleep(1)  # Rate limiting
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
        with open('data.txt', 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        grade_to_gpa = {
            'A+': 4.33, 'A': 4.00, 'A-': 3.67,
            'B+': 3.33, 'B': 3.00, 'B-': 2.67,
            'C+': 2.33, 'C': 2.00, 'C-': 1.67,
            'D': 1.00, 'F': 0.00
        }
        
        base_course_code = ' '.join(course_code.upper().split()[:2])
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 4:
                file_course = f"{parts[0]} {parts[1]}"
                if file_course == base_course_code:
                    median_grade = parts[2]
                    fail_percentage = float(parts[3])
                    
                    try:
                        gpa_value = grade_to_gpa.get(median_grade, 0)
                        difficulty = str(round((4.33 - gpa_value) / 4.33 * 5, 1))
                    except (KeyError, TypeError):
                        difficulty = 'N/A'
                    
                    return {
                        'median_grade': median_grade,
                        'fail_percentage': f"{fail_percentage}%",
                        'course_difficulty': difficulty
                    }
        
        return default_response
                
    except Exception as e:
        logger.error(f"Error reading course data for {course_code}: {str(e)}")
        return default_response


async def process_course_info(course_data):
    """Process a single course entry and return formatted information"""
    try:
        # Replace '\t' with actual tabs and handle multiple spaces
        course_data = course_data.replace('\\t', '\t')
        
        # Split by either tabs or multiple spaces
        parts = re.split(r'\t+|\s{2,}', course_data.strip())
        
        # Reconstruct the parts considering the course code might have spaces
        processed_parts = []
        i = 0
        while i < len(parts):
            if i == 1:  # Course code position
                # Combine course code parts (e.g., "ACMA", "101", "D100")
                code_parts = []
                while i < len(parts) and not parts[i].lower().startswith('introduction'):
                    code_parts.append(parts[i])
                    i += 1
                processed_parts.append(' '.join(code_parts))
                if i < len(parts):
                    processed_parts.append(parts[i])
            else:
                processed_parts.append(parts[i])
            i += 1
            
        if len(processed_parts) < 6:
            return "Error: Invalid course data format. Please provide: Semester, Course Code, Course Name, Capacity, Professor Name, Campus"
            
        semester = processed_parts[0]
        course_code = processed_parts[1]
        course_name = processed_parts[2]
        capacity = processed_parts[3]
        professor_name = processed_parts[4]
        campus = processed_parts[5]
        
        # Get school
        school = ratemyprofessor.get_school_by_name("Simon Fraser University")
        if not school:
            return "Error: Could not find Simon Fraser University"
            
        # Get professor rating
        prof_data = get_professor_rating(school, professor_name)
        
        # Get course information
        course_info = get_course_digger_info(course_code)
        
        # Parse capacity
        try:
            current, maximum = capacity.split('/')
            if not current:
                current = '0'
        except ValueError:
            current = '0'
            maximum = '0'
            
        # Format response as an embedded message
        embed = discord.Embed(
            title=f"{course_code} - {course_name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Semester", value=semester, inline=True)
        embed.add_field(name="Professor", value=professor_name, inline=True)
        embed.add_field(name="Campus", value=campus, inline=True)
        embed.add_field(name="Enrollment", value=f"{current}/{maximum}", inline=True)
        
        # Professor ratings
        embed.add_field(name="Professor Rating", value=prof_data['rating'], inline=True)
        embed.add_field(name="Professor Difficulty", value=prof_data['difficulty'], inline=True)
        embed.add_field(name="Would Take Again", value=prof_data['would_take_again'], inline=True)
        embed.add_field(name="Number of Ratings", value=prof_data['num_ratings'], inline=True)
        
        # Course statistics
        embed.add_field(name="Median Grade", value=course_info['median_grade'], inline=True)
        embed.add_field(name="Fail Percentage", value=course_info['fail_percentage'], inline=True)
        embed.add_field(name="Course Difficulty", value=course_info['course_difficulty'], inline=True)
        
        return embed
        
    except Exception as e:
        logger.error(f"Error processing course: {str(e)}")
        return f"Error processing course: {str(e)}"

@bot.command(name='course')
async def course(ctx, *, course_data: str):
    """Process course information"""
    async with ctx.typing():
        result = await process_course_info(course_data)
        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)
        else:
            await ctx.send(result)

@bot.command(name='course_help')
async def help_command(ctx):
    help_text = """
**Course Information Bot Commands**
`!course [course_data]` - Get information about a course

Example:
`!course Spring 2025  ACMA 101 D100  Introduction to Insurance  0/105  Ng, Cherie  Burnaby`

Note: Separate fields with either two or more spaces or use '\\t'
Fields needed: Semester, Course Code, Course Name, Capacity, Professor Name, Campus
    """
    embed = discord.Embed(title="Help", description=help_text, color=discord.Color.blue())
    await ctx.send(embed=embed)


if __name__ == "__main__":
    #Delete when pushing to github
    bot.run('placeholder')
