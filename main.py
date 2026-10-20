#!/usr/bin/env python3
"""
Blogger Agent - Automatically writes and publishes blog posts to Google Blogger.
Uses Groq API for content generation, Serper for search, Pixabay for images,
and Google Blogger API v3 for publishing.

Environment variables required (set as GitHub Actions Secrets):
- GROQ_API_KEY
- SEARCH_API_KEY
- PIXABAY_API_KEY
- BLOGGER_BLOG_ID
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- GOOGLE_REFRESH_TOKEN
"""

import os
import sys
import json
import time
import logging
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests
from groq import Groq
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================
# Configuration & Constants
# ============================
TOPICS_FILE = "topics.txt"
USED_TOPICS_FILE = "used_topics.txt"
MAX_RETRIES = 2  # Try once, then retry once = 2 attempts total
RETRY_DELAY = 5  # seconds between retries

# Blogger API scopes
BLOGGER_SCOPES = ["https://www.googleapis.com/auth/blogger"]


# ============================
# Helper Functions
# ============================
def get_env_var(name: str) -> str:
    """Get environment variable or exit with error."""
    value = os.getenv(name)
    if not value:
        logger.error(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def retry_request(func, *args, **kwargs):
    """
    Retry a function call up to MAX_RETRIES times.
    Returns the result on success, exits on failure.
    """
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    logger.error(f"All {MAX_RETRIES} attempts failed. Last error: {last_exception}")
    sys.exit(1)


def run_git_command(args: List[str]) -> str:
    """Run a git command and return output."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Git command failed: {' '.join(args)}")
        logger.error(result.stderr)
        sys.exit(1)
    return result.stdout.strip()


# ============================
# Topic Management
# ============================
def get_next_topic() -> str:
    """
    Read topics.txt and used_topics.txt, return the first unused topic.
    """
    # Read all topics
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        all_topics = [line.strip() for line in f if line.strip()]

    # Read used topics
    with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
        used_topics = set(line.strip() for line in f if line.strip())

    # Find first unused topic
    for topic in all_topics:
        if topic not in used_topics:
            logger.info(f"Selected topic: {topic}")
            return topic

    logger.error("No unused topics found!")
    sys.exit(1)


def mark_topic_used(topic: str):
    """Append topic to used_topics.txt and commit to git."""
    with open(USED_TOPICS_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
    logger.info(f"Marked topic as used: {topic}")

    # Commit the change
    run_git_command(["add", USED_TOPICS_FILE])
    run_git_command(["config", "user.name", "github-actions[bot]"])
    run_git_command(["config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    run_git_command(["commit", "-m", f"Add used topic: {topic}"])
    run_git_command(["push"])
    logger.info("Committed and pushed used_topics.txt")


# ============================
# Search API (Serper)
# ============================
def search_web(query: str) -> List[Dict[str, Any]]:
    """
    Search the web using Serper API.
    Returns list of search results with title, snippet, link.
    """
    api_key = get_env_var("SEARCH_API_KEY")
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 10}

    def _do_search():
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("organic", [])
        logger.info(f"Found {len(results)} search results")
        return results

    return retry_request(_do_search)


# ============================
# Groq API - Content Generation
# ============================
def generate_blog_post(topic: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a blog post using Groq API (Llama 3.3 70B).
    Returns dict with: title, html_content, labels
    """
    api_key = get_env_var("GROQ_API_KEY")
    client = Groq(api_key=api_key)

    # Prepare search context
    search_context = "\n\n".join([
        f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}\nLink: {r.get('link', '')}"
        for r in search_results[:8]  # Use top 8 results
    ])

    prompt = f"""You are an expert digital marketing blogger. Write a comprehensive blog post about:

**Topic:** {topic}

**Reference Information (use as background only, write in your own words):**
{search_context}

**Requirements:**
- Word count: 800-1200 words
- Original wording (do not copy from references)
- Clean HTML for Blogger: use <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Catchy SEO-optimized title
- Short engaging introduction (2-3 paragraphs)
- 4-6 main sections with descriptive <h2> headings
- Use bullet points (<ul><li>) where appropriate
- Conclusion with key takeaways
- Professional, informative tone
- 4-5 relevant labels/tags (comma-separated)

**Output Format (JSON only):**
{{
  "title": "Catchy SEO Title Here",
  "html_content": "<h2>Section 1</h2><p>Content...</p>...",
  "labels": "tag1, tag2, tag3, tag4, tag5"
}}"""

    def _generate():
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert digital marketing blogger. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        result = json.loads(content)

        # Validate required fields
        if not all(k in result for k in ("title", "html_content", "labels")):
            raise ValueError("Missing required fields in Groq response")

        word_count = len(result["html_content"].split())
        logger.info(f"Generated post: {word_count} words, title: {result['title'][:60]}...")
        return result

    return retry_request(_generate)


# ============================
# Pixabay API - Image Fetching
# ============================
def fetch_pixabay_image(topic: str) -> Dict[str, str]:
    """
    Fetch a relevant free image from Pixabay.
    Returns dict with: image_url, alt_text, credit_line
    """
    api_key = get_env_var("PIXABAY_API_KEY")
    url = "https://pixabay.com/api/"
    params = {
        "key": api_key,
        "q": topic,
        "image_type": "photo",
        "orientation": "horizontal",
        "min_width": 1200,
        "per_page": 10,
        "safesearch": "true"
    }

    def _fetch():
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])
        if not hits:
            raise ValueError("No images found on Pixabay")

        # Pick first image
        image = hits[0]
        image_url = image.get("largeImageURL") or image.get("webformatURL")
        alt_text = image.get("tags", topic).split(",")[0].strip()
        credit = "Image from Pixabay"

        logger.info(f"Selected Pixabay image: {image_url}")
        return {"image_url": image_url, "alt_text": alt_text, "credit": credit}

    return retry_request(_fetch)


# ============================
# Google Blogger API - Publishing
# ============================
def get_blogger_service():
    """Create and return authenticated Blogger API service."""
    client_id = get_env_var("GOOGLE_CLIENT_ID")
    client_secret = get_env_var("GOOGLE_CLIENT_SECRET")
    refresh_token = get_env_var("GOOGLE_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=BLOGGER_SCOPES
    )
    service = build("blogger", "v3", credentials=creds)
    return service


def publish_to_blogger(title: str, html_content: str, labels: List[str], image_info: Dict[str, str]) -> str:
    """
    Publish the blog post to Blogger as a live post.
    Returns the post URL.
    """
    blog_id = get_env_var("BLOGGER_BLOG_ID")
    service = get_blogger_service()

    # Prepend image to content
    image_html = (
        f'<div style="text-align: center; margin-bottom: 20px;">'
        f'<img src="{image_info["image_url"]}" alt="{image_info["alt_text"]}" '
        f'style="max-width: 100%; height: auto; border-radius: 8px;">'
        f'<br><small><em>{image_info["credit"]}</em></small>'
        f'</div>'
    )
    full_content = image_html + html_content

    post_body = {
        "kind": "blogger#post",
        "title": title,
        "content": full_content,
        "labels": labels,
        "status": "LIVE"
    }

    def _publish():
        request = service.posts().insert(blogId=blog_id, body=post_body, isDraft=False)
        response = request.execute()
        post_url = response.get("url")
        post_id = response.get("id")
        logger.info(f"Published post ID: {post_id}, URL: {post_url}")
        return post_url

    return retry_request(_publish)


# ============================
# Main Flow
# ============================
def main():
    logger.info("=" * 50)
    logger.info("Blogger Agent - Starting")
    logger.info("=" * 50)

    # Step 1: Pick next unused topic
    topic = get_next_topic()

    # Step 2: Search the topic
    logger.info("Searching web for topic...")
    search_results = search_web(topic)

    # Step 3: Generate blog post with Groq
    logger.info("Generating blog post with Groq...")
    post_data = generate_blog_post(topic, search_results)

    # Step 4: Fetch image from Pixabay
    logger.info("Fetching image from Pixabay...")
    image_info = fetch_pixabay_image(topic)

    # Step 5: Publish to Blogger
    logger.info("Publishing to Blogger...")
    post_url = publish_to_blogger(
        title=post_data["title"],
        html_content=post_data["html_content"],
        labels=[label.strip() for label in post_data["labels"].split(",")],
        image_info=image_info
    )

    # Step 6: Mark topic as used and commit
    logger.info("Marking topic as used...")
    mark_topic_used(topic)

    logger.info("=" * 50)
    logger.info(f"SUCCESS! Post published: {post_url}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()