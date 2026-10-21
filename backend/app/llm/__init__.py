"""The LLM gateway: every provider call goes through ``gateway``.

``providers`` decides which provider a call may use and holds one client per
provider; ``usage`` writes one record per attempt.
"""
