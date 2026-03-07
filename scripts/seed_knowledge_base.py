#!/usr/bin/env python3
"""
TechCorp FTE Knowledge Base Seeding Script
Loads product-docs.md into PostgreSQL with embeddings
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add production directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import google.generativeai as genai
from database.connection import init_db_pool, close_db_pool
from database import queries

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_product_docs():
    """Load and parse product documentation"""
    docs_path = Path(__file__).parent.parent / "context" / "product-docs.md"
    
    if not docs_path.exists():
        logger.error(f"Product docs not found at {docs_path}")
        return []
    
    try:
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by lines starting with "## "
        sections = []
        current_section = {"title": "", "content": "", "lines": []}
        
        for line in content.split('\n'):
            if line.startswith('## '):
                # Save previous section if exists
                if current_section["title"] and current_section["content"]:
                    current_section["content"] = '\n'.join(current_section["lines"])
                    sections.append(current_section)
                
                # Start new section
                title = line[3:].strip()
                current_section = {
                    "title": title,
                    "content": "",
                    "lines": [line]
                }
            else:
                current_section["lines"].append(line)
        
        # Add the last section
        if current_section["title"] and current_section["content"]:
            current_section["content"] = '\n'.join(current_section["lines"])
            sections.append(current_section)
        
        logger.info(f"Loaded {len(sections)} sections from product documentation")
        return sections
        
    except Exception as e:
        logger.error(f"Error loading product docs: {e}")
        return []

def detect_category(title):
    """Detect category from title keywords"""
    title_lower = title.lower()
    
    category_keywords = {
        'billing': ['billing', 'invoice', 'payment', 'price', 'cost', 'refund', 'subscription', 'plan'],
        'api': ['api', 'integration', 'webhook', 'endpoint', 'sdk', 'developer', 'technical'],
        'troubleshooting': ['troubleshoot', 'issue', 'problem', 'error', 'fix', 'debug', 'broken'],
        'user-management': ['user', 'account', 'profile', 'permissions', 'roles', 'admin', 'invite'],
        'features': ['feature', 'functionality', 'capability', 'option', 'setting'],
        'getting-started': ['getting', 'started', 'beginner', 'new', 'setup', 'install', 'onboarding'],
        'security': ['security', 'password', 'login', 'authentication', '2fa', 'privacy']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            return category
    
    return 'general'

def generate_embedding(title, content):
    """Generate embedding for knowledge base entry"""
    try:
        # Combine title and content for better embeddings
        combined_text = f"{title} {content[:1000]}"
        
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=combined_text,
            task_type="retrieval_document"
        )
        
        return response["embedding"]
        
    except Exception as e:
        logger.error(f"Error generating embedding for '{title}': {e}")
        return None

async def seed_knowledge_base():
    """Main function to seed the knowledge base"""
    logger.info("🌱️ Starting knowledge base seeding...")
    
    try:
        # Initialize database connection
        await init_db_pool()
        logger.info("✅ Database connection initialized")
        
        # Load product documentation
        sections = load_product_docs()
        
        if not sections:
            logger.error("❌ No sections found to seed")
            return
        
        seeded_count = 0
        
        for section in sections:
            title = section["title"]
            content = section["content"]
            
            if not title or not content:
                logger.warning(f"⚠️ Skipping empty section: {title[:50]}...")
                continue
            
            # Detect category
            category = detect_category(title)
            
            # Generate embedding
            embedding = generate_embedding(title, content)
            
            if embedding is None:
                logger.error(f"❌ Failed to generate embedding for: {title}")
                continue
            
            # Insert into database
            try:
                entry_id = await queries.insert_knowledge_entry(
                    title=title,
                    content=content,
                    category=category,
                    embedding=embedding
                )
                logger.info(f"📚 Seeded: {title}")
                seeded_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to insert '{title}': {e}")
        
        logger.info(f"✅ Done. {seeded_count} entries seeded into knowledge base.")
        
    except Exception as e:
        logger.error(f"❌ Knowledge base seeding failed: {e}")
    
    finally:
        # Close database connection
        await close_db_pool()
        logger.info("🔒 Database connection closed")

def main():
    """Main entry point"""
    try:
        # Check if Gemini API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            logger.error("Please set GEMINI_API_KEY in your .env file")
            sys.exit(1)
        
        # Run seeding
        asyncio.run(seed_knowledge_base())
        
    except KeyboardInterrupt:
        logger.info("🛑 Knowledge base seeding interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
