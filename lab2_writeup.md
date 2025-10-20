# Supabase Database Setup
## Project & Database Initialization
Visit [Supabase](https://supabase.com), complete registration, and create a new project (custom project name)  

After project creation, go to Settings → Database and copy the Connection String  

Navigate to SQL Editor, create new query, and execute the following SQL  

# Dependency Configuration & Environment Variables
## Adding Required Dependencies
Install python-dotenv (environment variable loader) and psycopg2-binary (Postgres driver)  

Update requirements.txt  

# Vercel Deployment Configuration
## Creating Deployment Files
Create api/index.py to expose Flask application  

Create vercel.json for deployment configuration  

## Deploying to Vercel
### Link GitHub repository to Vercel  

### Configure environment variables  
Environment Variables Configuration (Vercel Dashboard → Project → Settings → Environment Variables):  

DATABASE_URL: Supabase connection string  

OPENAI_API_KEY: LLM service API key  

SECRET_KEY: Same as local .env  

### Execute deployment

# challenges
Missing Variable Detection: The application initially failed silently when critical variables (like `DATABASE_URL`) were missing, defaulting to SQLite without warning. This required adding explicit validation checks that raise clear errors for missing required variables.  
Path Resolution Problems**: Vercel's execution environment uses different working directories than local development. This broke relative imports between `src/main.py` and the new `api/index.py` entry point, requiring explicit package path configuration.  






