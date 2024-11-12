# SFU Course Information Discord Bot

A comprehensive Discord bot that provides detailed information about Simon Fraser University courses, including course descriptions, professor ratings, and section details.

## Features

- **Course Information Lookup**
  - Course descriptions
  - Section details (instructor, time, location)
  - Grade statistics (median grade, fail percentage)
  - Professor ratings from RateMyProfessor
  
- **Interactive Commands**
  - `/courses` - Interactive course selection and information display
  - `/dispdept` - Browse departments and their courses
  - `/update` - Update course data (admin only)
  - `/course_help` - Display help information

- **Real-time Data**
  - Automatic course data updates
  - Cached professor ratings for improved performance
  - Parallel processing for faster response times

## Prerequisites

```bash
pip install discord.py
pip install RateMyProfessorAPI
pip install fuzzywuzzy
pip install google-generativeai
pip install playwright
```

## Environment Setup

1. Create a Discord Application and Bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Configure the following variables in `CourseBotv3.py`:
```python
GeminiAIKey = "your_gemini_ai_key"
OWNER_ID = "your_discord_user_id"
bot.run('your_discord_bot_token')
```

## File Structure

```
├── CourseBotv3.py          # Main bot file
├── CoursetoJSON.py         # Course data scraper
├── MajorRequirementScrape.py   # Major requirements scraper
├── sfu_courses2.json       # Course data
└── data.txt               # Grade statistics data
```

## Usage

1. Start the bot:
```bash
python CourseBotv3.py
```

2. In Discord, use the following commands:
```
/courses - Start interactive course selection
/dispdept - View all departments
/course_help - Display help information
```

## Features in Detail

### Course Information
- Complete course descriptions
- Section-specific information
- Professor ratings including:
  - Overall rating
  - Difficulty rating
  - Would take again percentage
  - Number of ratings

### Performance Optimizations
- Professor rating caching
- Parallel processing for batch operations
- Rate limiting protection
- Error handling and logging

### Administrative Features
- Course data update command
- Logging system for debugging
- Owner-only administrative commands

## Error Handling

The bot includes comprehensive error handling:
- Timeout protection for user interactions
- API failure recovery
- Invalid input handling
- Detailed logging for troubleshooting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainer.

---

*Note: This bot is not officially affiliated with Simon Fraser University.*
