"""
Supabase client initialization utility.
This module provides a consistent way to initialize and access Supabase clients.
"""
import httpx

# Store original __init__ method
_original_init = httpx.Client.__init__

# Patch httpx.Client.__init__ to ignore proxy argument
def patched_init(self, *args, **kwargs):
    # Remove proxy from kwargs if present
    kwargs.pop('proxy', None)
    return _original_init(self, *args, **kwargs)

# Apply the patch
httpx.Client.__init__ = patched_init

from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = 'https://qkaaoeismqnhjyikgkme.supabase.co'
SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrYWFvZWlzbXFuaGp5aWtna21lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDI1NzQsImV4cCI6MjA2OTg3ODU3NH0.o3K8BNVZucbqFWsPzIZJ_H8_ApR3uu9Cvjm5C9HFKX0'
SUPABASE_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrYWFvZWlzbXFuaGp5aWtna21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDMwMjU3NCwiZXhwIjoyMDY5ODc4NTc0fQ.L1ZCNGBbQqrRjCI9IrmounuEtwux4yBmhvPBR4vU5Uw'

# Supabase configuration is hardcoded for this application

# Log the configuration (without sensitive data)
print(f"[SUPABASE] Initializing with URL: {SUPABASE_URL}")
print(f"[SUPABASE] Anon key: {'Set' if SUPABASE_ANON_KEY else 'Not set'}")
print(f"[SUPABASE] Service role key: {'Set' if SUPABASE_SERVICE_ROLE_KEY else 'Not set'}")

# Initialize Supabase clients with default options
# Regular client for normal operations (uses anon key)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Admin client for auth operations (uses service role key)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_supabase(admin: bool = False, token: str = None) -> Client:
    """
    Get the appropriate Supabase client instance.

    Args:
        admin (bool): If True, returns the admin client with service role.
                     If False, returns the regular client with anon key.
        token (str): Optional JWT token for authenticated requests.
    Returns:
        Client: The appropriate Supabase client instance
    """
    if admin:
        return supabase_admin
    elif token:
        # Create a new client instance with the user's JWT token
        return create_client(SUPABASE_URL, SUPABASE_ANON_KEY, {
            'global': {
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
        })
    else:
        return supabase
