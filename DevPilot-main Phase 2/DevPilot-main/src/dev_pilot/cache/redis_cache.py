import json
from typing import Optional
from src.dev_pilot.state.sdlc_state import CustomEncoder, SDLCState, UserStoryList, UserStories
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# In-memory storage for demo purposes
_memory_cache = {}
USE_REDIS = False
redis_client = None

logger.info("Using in-memory storage for caching (data will not persist between restarts)")

## For testing locally with docker
# redis_client = redis.Redis(
#     host='localhost',  # Replace with your Redis host
#     port=6379,         # Replace with your Redis port
#     db=0               # Replace with your Redis database number
# )

def save_state_to_redis(task_id: str, state: SDLCState):
    """Save the state to Redis or in-memory cache."""
    state_json = json.dumps(state, cls=CustomEncoder)
    
    if USE_REDIS and redis_client:
        redis_client.set(task_id, state_json)
        # Set expiration for 24 hours
        redis_client.expire(task_id, 86400)
    else:
        # Use in-memory storage
        _memory_cache[task_id] = state_json
        logger.debug(f"Saved state for task_id {task_id} in memory cache")

def get_state_from_redis(task_id: str) -> Optional[SDLCState]:
    """ Retrieves the state from redis or in-memory cache """
    state_json = None

    if USE_REDIS and redis_client:
        state_json = redis_client.get(task_id)
    else:
        # Use in-memory storage
        state_json = _memory_cache.get(task_id)
        logger.debug(f"Retrieved state for task_id {task_id} from memory cache")

    if not state_json:
        return None

    state_dict = json.loads(state_json)

    # Reconstruct UserStoryList from dict if present
    if "user_stories" in state_dict and isinstance(state_dict["user_stories"], dict):
        user_stories_dict = state_dict["user_stories"]
        if "user_stories" in user_stories_dict:
            stories_data = user_stories_dict["user_stories"]
            if isinstance(stories_data, list):
                user_story_objects = []
                for story_dict in stories_data:
                    if isinstance(story_dict, dict):
                        user_story_objects.append(UserStories(**story_dict))
                state_dict["user_stories"] = UserStoryList(user_stories=user_story_objects)

    return state_dict

def delete_from_redis(task_id: str):
    """ Delete from redis or in-memory cache """
    if USE_REDIS and redis_client:
        redis_client.delete(task_id)
    else:
        # Use in-memory storage
        if task_id in _memory_cache:
            del _memory_cache[task_id]
            logger.debug(f"Deleted task_id {task_id} from memory cache")

def flush_redis_cache():
    """ Flushes the whole cache"""
    if USE_REDIS and redis_client:
        # Clear all keys in all databases
        redis_client.flushall()
        logger.info("--- Redis cache cleared ---")
    else:
        # Clear in-memory cache
        _memory_cache.clear()
        logger.info("--- Memory cache cleared ---")
