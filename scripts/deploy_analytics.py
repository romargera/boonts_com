#!/usr/bin/env python3
"""Deploy the existing analytics Worker using local credentials, never CLI token arguments."""
import subprocess
from seo_env import ROOT,load_env
load_env()
raise SystemExit(subprocess.call(['npx','--yes','wrangler@4.129.0','deploy'],cwd=ROOT/'cloudflare/analytics-worker'))
