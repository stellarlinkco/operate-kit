"""Compatibility shim.

The SDK has been renamed from `mobile_agent.sdk` to `operatekit` because the
core is now cross-platform RPA-first automation, not mobile-only and not
agent-first.
"""
from operatekit import *  # noqa: F401,F403
