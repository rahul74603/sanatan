"""
🔧 Publisher Agent - Instagram Fix
Tumhare existing core/publisher_agent.py me yeh changes karo.

Yeh file:
1. Rate limiter integrate karti hai
2. Better retry logic deti hai
3. Token auto-refresh karti hai
4. Detailed error messages deti hai

Use:
    from fix_publisher_ig import publish_image_to_instagram_safely
    result = publish_image_to_instagram_safely(image_url, caption)
"""

import os
import sys
import time
import random
import json
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.rate_limiter import get_rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    print("⚠️ rate_limiter not found, proceeding without rate limiting")
    RATE_LIMITER_AVAILABLE = False


class InstagramPublisher:
    """Instagram Graph API publisher with rate limiting and retry logic"""

    def __init__(self, access_token, ig_user_id, app_id=None, app_secret=None):
        self.access_token = access_token
        self.ig_user_id = ig_user_id
        self.app_id = app_id
        self.app_secret = app_secret
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

        # Rate limiter initialize
        if RATE_LIMITER_AVAILABLE:
            self.rate_limiter = get_rate_limiter()
        else:
            self.rate_limiter = None

        print(f"📱 Instagram Publisher initialized (User: {ig_user_id})")

    def _make_request(self, endpoint, method='POST', params=None, max_retries=3):
        """Rate-limited API request with retry"""
        url = f"{self.base_url}/{endpoint}"

        for attempt in range(1, max_retries + 1):
            # Rate limit check
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            try:
                if method == 'POST':
                    response = requests.post(url, params=params, timeout=30)
                else:
                    response = requests.get(url, params=params, timeout=30)

                data = response.json()

                # Success
                if response.status_code == 200 and 'id' in data:
                    return {'success': True, 'data': data}

                # Rate limit error
                if 'limit reached' in str(data).lower() or response.status_code == 429:
                    wait_time = 60 * attempt + random.randint(10, 30)
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                # Auth error - token refresh try karo
                if response.status_code == 401 and self.app_id and self.app_secret:
                    print("🔄 Token expired. Refreshing...")
                    new_token = self._refresh_long_lived_token()
                    if new_token:
                        self.access_token = new_token
                        params['access_token'] = new_token
                        continue

                # Other API error
                error_msg = data.get('error', {}).get('message', str(data))
                return {'success': False, 'error': error_msg, 'status': response.status_code}

            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout (attempt {attempt}/{max_retries})")
                time.sleep(10)
            except Exception as e:
                print(f"❌ Error: {e}")
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Max retries exceeded'}

    def _refresh_long_lived_token(self):
        """Long-lived token refresh (60 din ka)"""
        if not self.app_id or not self.app_secret:
            return None

        try:
            url = f"{self.base_url}/oauth/access_token"
            params = {
                'grant_type': 'fb_exchange_token',
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'fb_exchange_token': self.access_token
            }
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if 'access_token' in data:
                new_token = data['access_token']
                print(f"✅ Token refreshed! Valid for ~{data.get('expires_in', 5184000)/86400:.0f} days")
                # .env me save karo
                self._save_token_to_env(new_token)
                return new_token
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
        return None

    def _save_token_to_env(self, new_token):
        """.env file me new token save karo"""
        env_path = Path(".env")
        if not env_path.exists():
            return

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # INSTAGRAM_ACCESS_TOKEN line update karo
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('INSTAGRAM_ACCESS_TOKEN='):
                    lines[i] = f'INSTAGRAM_ACCESS_TOKEN={new_token}'
                    break

            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print("💾 Token saved to .env")
        except Exception as e:
            print(f"⚠️ Could not save token: {e}")

    def create_container(self, image_url, caption):
        """Step 1: Media container create karo"""
        print(f"\n📦 Creating IG container...")
        print(f"   Image: {image_url[:60]}...")
        print(f"   Caption: {len(caption)} chars")

        params = {
            'access_token': self.access_token,
            'media_type': 'IMAGE',
            'image_url': image_url,
            'caption': caption
        }

        result = self._make_request(f"{self.ig_user_id}/media", params=params)

        if result['success']:
            container_id = result['data']['id']
            print(f"✅ Container created: {container_id}")
            return container_id
        else:
            print(f"❌ Container creation failed: {result.get('error')}")
            return None

    def check_container_status(self, container_id, max_wait=120):
        """Step 2: Container ready hai ya nahi check karo"""
        print(f"\n⏳ Checking container status: {container_id}")

        start = time.time()
        while time.time() - start < max_wait:
            params = {
                'access_token': self.access_token,
                'fields': 'status_code,status'
            }
            result = self._make_request(
                container_id,
                method='GET',
                params=params
            )

            if result['success']:
                status = result['data'].get('status_code', 'UNKNOWN')
                print(f"   Status: {status}")

                if status == 'FINISHED':
                    return 'FINISHED'
                elif status == 'ERROR':
                    return 'ERROR'
                elif status == 'IN_PROGRESS':
                    print("   Still processing, waiting 10s...")
                    time.sleep(10)
            else:
                print(f"   Error: {result.get('error')}")
                time.sleep(5)

        return 'TIMEOUT'

    def publish_container(self, container_id):
        """Step 3: Container publish karo"""
        print(f"\n📤 Publishing container: {container_id}")

        params = {
            'access_token': self.access_token,
            'creation_id': container_id
        }

        result = self._make_request(f"{self.ig_user_id}/media_publish", params=params)

        if result['success']:
            post_id = result['data']['id']
            print(f"✅ Published! Post ID: {post_id}")
            return post_id
        else:
            print(f"❌ Publish failed: {result.get('error')}")
            return None

    def publish_image(self, image_url, caption, max_total_time=600):
        """
        Complete publish flow with smart retry.

        Args:
            image_url: Public image URL (must be HTTPS)
            caption: Post caption (max 2200 chars)
            max_total_time: Max total seconds to spend

        Returns:
            dict with success status and post_id or error
        """
        start_time = time.time()
        attempt = 0
        max_attempts = 3

        while attempt < max_attempts:
            attempt += 1
            elapsed = time.time() - start_time

            if elapsed > max_total_time:
                print(f"⏱️ Total time limit ({max_total_time}s) reached. Stopping.")
                return {'success': False, 'error': 'Total time limit exceeded'}

            print(f"\n{'='*60}")
            print(f"📱 INSTAGRAM PUBLISH ATTEMPT {attempt}/{max_attempts}")
            print(f"{'='*60}")

            # Step 1: Container
            container_id = self.create_container(image_url, caption)
            if not container_id:
                # Container creation fail - bahut rare
                wait = 30 * attempt
                print(f"⏳ Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            # Step 2: Wait for processing
            wait_time = 15 + (attempt * 5)  # Increasing wait
            print(f"\n⏳ Waiting {wait_time}s for IG to process image...")
            time.sleep(wait_time)

            # Step 3: Check status
            status = self.check_container_status(container_id, max_wait=60)
            if status == 'ERROR':
                print("❌ Container error. Recreating...")
                continue
            elif status == 'TIMEOUT':
                print("⚠️ Status check timeout. Trying to publish anyway...")

            # Step 4: Publish
            post_id = self.publish_container(container_id)
            if post_id:
                return {
                    'success': True,
                    'post_id': post_id,
                    'container_id': container_id,
                    'attempts': attempt
                }

            # Publish failed - rate limit likely
            print(f"⚠️ Publish attempt {attempt} failed.")
            if attempt < max_attempts:
                # Rate limit detected - longer wait
                wait = 90 * attempt + random.randint(20, 60)
                print(f"⏳ Waiting {wait}s ({wait/60:.1f} min) before next attempt...")
                time.sleep(wait)

        return {
            'success': False,
            'error': f'All {max_attempts} attempts failed',
            'attempts': attempt
        }


def publish_image_to_instagram_safely(image_url, caption, ig_user_id=None, access_token=None):
    """
    Helper function - directly call kar sakte ho.

    Usage:
        result = publish_image_to_instagram_safely(
            image_url="https://...",
            caption="Your caption",
        )
    """
    # .env se credentials load karo agar nahi diye
    if not access_token or not ig_user_id:
        from dotenv import load_dotenv
        load_dotenv()
        access_token = access_token or os.getenv('INSTAGRAM_ACCESS_TOKEN')
        ig_user_id = ig_user_id or os.getenv('INSTAGRAM_USER_ID')

    if not access_token or not ig_user_id:
        print("❌ Instagram credentials missing!")
        print("💡 Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in .env")
        return {'success': False, 'error': 'Missing credentials'}

    app_id = os.getenv('META_APP_ID')
    app_secret = os.getenv('META_APP_SECRET')

    publisher = InstagramPublisher(
        access_token=access_token,
        ig_user_id=ig_user_id,
        app_id=app_id,
        app_secret=app_secret
    )

    return publisher.publish_image(image_url, caption)


# Example usage
if __name__ == "__main__":
    print("🧪 Instagram Publisher Test\n")

    # Test image (replace with your own)
    test_image = "https://storage.googleapis.com/your-bucket/test.jpg"
    test_caption = "Test post from Python script! 🙏 #test"

    result = publish_image_to_instagram_safely(test_image, test_caption)

    if result['success']:
        print(f"\n✅ SUCCESS!")
        print(f"📱 Post ID: {result['post_id']}")
        print(f"🔗 URL: https://instagram.com/p/{result['post_id']}")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
