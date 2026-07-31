"""
🛡️ Instagram API Rate Limiter
Track karta hai kitne calls kiye, aur limit ke paas rukta hai.
Yeh file Instagram "Application request limit reached" error fix karti hai.

Usage:
    from utils.rate_limiter import InstagramRateLimiter

    rate_limiter = InstagramRateLimiter(max_calls_per_hour=150)
    rate_limiter.wait_if_needed()
    # ... API call karo
"""

import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class InstagramRateLimiter:
    """
    Instagram Graph API rate limiter.
    Default: 150 calls/hour (safe limit, Meta ka official 200/hour hai).
    """

    def __init__(self, max_calls_per_hour=150, state_file="logs/ig_rate_limit.json"):
        self.max_calls = max_calls_per_hour
        self.state_file = Path(state_file)
        self.calls = self._load_state()
        print(f"🛡️ IG Rate Limiter initialized: {self.max_calls} calls/hour")

    def _load_state(self):
        """Pichli state load karo (persistent tracking)"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Timestamps ko datetime me convert karo
                    return [datetime.fromisoformat(t) for t in data.get('calls', [])]
            except Exception as e:
                print(f"⚠️ Rate limiter state load failed: {e}")
                return []
        return []

    def _save_state(self):
        """State save karo disk pe"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                data = {
                    'calls': [t.isoformat() for t in self.calls],
                    'last_updated': datetime.now().isoformat()
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Rate limiter state save failed: {e}")

    def _cleanup_old_calls(self):
        """1 ghante se purani calls hatao"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.calls = [t for t in self.calls if t > one_hour_ago]

    def can_make_call(self):
        """
        Check karo ki abhi call kar sakte hain ya nahi.
        Returns: (bool, wait_seconds)
        """
        self._cleanup_old_calls()
        current_count = len(self.calls)

        if current_count >= self.max_calls:
            # Sabse purani call ka time + 1 hour
            oldest_call = min(self.calls)
            wait_until = oldest_call + timedelta(hours=1)
            wait_seconds = (wait_until - datetime.now()).total_seconds()
            return False, max(0, wait_seconds)

        return True, 0

    def make_call(self):
        """Ek call register karo (timestamp add karo)"""
        self.calls.append(datetime.now())
        self._save_state()
        print(f"📊 IG API calls this hour: {len(self.calls)}/{self.max_calls}")

    def wait_if_needed(self, verbose=True):
        """
        Agar limit ke paas hain toh wait karo.
        Yeh function call karne se pehle use karo.
        """
        can_call, wait_seconds = self.can_make_call()

        if not can_call:
            wait_minutes = wait_seconds / 60
            if verbose:
                print(f"⏳ Rate limit reached ({len(self.calls)}/{self.max_calls}).")
                print(f"⏳ Waiting {wait_minutes:.1f} minutes before next call...")
            time.sleep(wait_seconds + 10)  # 10s buffer

        self.make_call()

    def get_stats(self):
        """Current statistics return karo"""
        self._cleanup_old_calls()
        return {
            'calls_this_hour': len(self.calls),
            'max_calls': self.max_calls,
            'remaining': self.max_calls - len(self.calls),
            'oldest_call': min(self.calls).isoformat() if self.calls else None,
            'reset_at': (min(self.calls) + timedelta(hours=1)).isoformat() if self.calls else None
        }


# Singleton instance (poore project me ek hi use hoga)
_rate_limiter_instance = None


def get_rate_limiter():
    """Singleton rate limiter instance return karo"""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = InstagramRateLimiter()
    return _rate_limiter_instance


if __name__ == "__main__":
    # Test the rate limiter
    print("🧪 Testing Instagram Rate Limiter\n")
    limiter = InstagramRateLimiter(max_calls_per_hour=5)  # Low limit for testing

    # Stats dekho
    stats = limiter.get_stats()
    print(f"📊 Current stats: {json.dumps(stats, indent=2)}")

    # Kuch calls simulate karo
    for i in range(3):
        limiter.wait_if_needed()
        print(f"✅ Call {i+1} made\n")

    print("✅ Rate limiter test complete!")
