import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

from db.supabase_client import supabase

print("=" * 80)
print("ANALYZING GROQ API TOKEN USAGE AND RATE LIMIT IMPACT")
print("=" * 80)

# Fetch recent token logs from evaluation runs
print("\nFetching token logs from recent evaluation runs...")
result = supabase.table("token_logs").select("*").order("created_at", desc=True).limit(100).execute()
token_logs = result.data

print(f"Found {len(token_logs)} recent token log entries")

if not token_logs:
    print("No token logs found. Please run evaluation first.")
    sys.exit(1)

# Analyze by agent role
print("\n" + "=" * 80)
print("TOKEN USAGE BY AGENT ROLE")
print("=" * 80)

agent_stats = {}
for log in token_logs:
    role = log.get("agent_role", "unknown")
    model = log.get("model", "unknown")
    tokens_in = log.get("tokens_in", 0)
    tokens_out = log.get("tokens_out", 0)
    total = tokens_in + tokens_out
    
    if role not in agent_stats:
        agent_stats[role] = {
            "count": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_tokens": 0,
            "models": {}
        }
    
    agent_stats[role]["count"] += 1
    agent_stats[role]["total_tokens_in"] += tokens_in
    agent_stats[role]["total_tokens_out"] += tokens_out
    agent_stats[role]["total_tokens"] += total
    
    if model not in agent_stats[role]["models"]:
        agent_stats[role]["models"][model] = {"count": 0, "tokens": 0}
    agent_stats[role]["models"][model]["count"] += 1
    agent_stats[role]["models"][model]["tokens"] += total

# Print agent breakdown
for role, stats in agent_stats.items():
    print(f"\n{role.upper()}:")
    print(f"  Calls: {stats['count']}")
    print(f"  Input tokens: {stats['total_tokens_in']:,}")
    print(f"  Output tokens: {stats['total_tokens_out']:,}")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    print(f"  Avg tokens/call: {stats['total_tokens'] // stats['count']:,}")
    print(f"  Output/Input ratio: {stats['total_tokens_out'] / stats['total_tokens_in']:.2f}x")
    print(f"  Models used:")
    for model, model_stats in stats["models"].items():
        print(f"    - {model}: {model_stats['count']} calls, {model_stats['tokens']:,} tokens")

# Calculate overall stats
print("\n" + "=" * 80)
print("OVERALL TOKEN USAGE")
print("=" * 80)

total_tokens_in = sum(stats["total_tokens_in"] for stats in agent_stats.values())
total_tokens_out = sum(stats["total_tokens_out"] for stats in agent_stats.values())
total_tokens = total_tokens_in + total_tokens_out
total_calls = sum(stats["count"] for stats in agent_stats.values())

print(f"Total API calls: {total_calls}")
print(f"Total input tokens: {total_tokens_in:,}")
print(f"Total output tokens: {total_tokens_out:,}")
print(f"Total tokens: {total_tokens:,}")
print(f"Average tokens/call: {total_tokens // total_calls:,}")
print(f"Output/Input ratio: {total_tokens_out / total_tokens_in:.2f}x")

# Rate limit analysis
print("\n" + "=" * 80)
print("RATE LIMIT ANALYSIS")
print("=" * 80)

groq_limit = 8000  # TPM limit
print(f"Groq on-demand limit: {groq_limit:,} TPM (tokens per minute)")
print(f"Total tokens used: {total_tokens:,}")
print(f"Capacity used: {(total_tokens / groq_limit * 100):.1f}% of one minute's capacity")

# Identify inefficiencies
print("\n" + "=" * 80)
print("EFFICIENCY ANALYSIS")
print("=" * 80)

inefficiencies = []

# Check for redundant calls
if agent_stats.get("synthesizer", {}).get("count", 0) > 0:
    synthesize_calls = agent_stats["synthesizer"]["count"]
    if synthesize_calls > 10:
        inefficiencies.append(f"High synthesizer call count: {synthesize_calls} (indicates many retries)")

# Check output token inefficiency
if total_tokens_out > total_tokens_in * 2:
    inefficiencies.append(f"High output token ratio: {total_tokens_out / total_tokens_in:.2f}x (LLM may be verbose)")

# Check for unnecessary agent calls
critic_calls = agent_stats.get("critic", {}).get("count", 0)
synthesizer_calls = agent_stats.get("synthesizer", {}).get("count", 0)
if critic_calls >= synthesizer_calls:
    inefficiencies.append(f"Critic calls equal or exceed synthesizer calls (may indicate strict critic)")

if inefficiencies:
    print("Potential inefficiencies found:")
    for ineff in inefficiencies:
        print(f"  - {ineff}")
else:
    print("No obvious inefficiencies detected")

# Model-specific analysis
print("\n" + "=" * 80)
print("MODEL-SPECIFIC USAGE")
print("=" * 80)

model_usage = {}
for log in token_logs:
    model = log.get("model", "unknown")
    tokens_in = log.get("tokens_in", 0)
    tokens_out = log.get("tokens_out", 0)
    
    if model not in model_usage:
        model_usage[model] = {"calls": 0, "tokens_in": 0, "tokens_out": 0}
    
    model_usage[model]["calls"] += 1
    model_usage[model]["tokens_in"] += tokens_in
    model_usage[model]["tokens_out"] += tokens_out

for model, stats in model_usage.items():
    total = stats["tokens_in"] + stats["tokens_out"]
    print(f"\n{model}:")
    print(f"  Calls: {stats['calls']}")
    print(f"  Input: {stats['tokens_in']:,}, Output: {stats['tokens_out']:,}, Total: {total:,}")
    print(f"  Avg/call: {total // stats['calls']:,}")

# Recommendations
print("\n" + "=" * 80)
print("OPTIMIZATION RECOMMENDATIONS")
print("=" * 80)

recommendations = [
    "1. Reduce retry count - each retry doubles the token usage",
    "2. Use smaller models for guardrail checks (llama-3.1-8b instead of 120b)",
    "3. Implement rate limit-aware scheduling with delays",
    "4. Cache guardrail results for repeated patterns",
    "5. Use input token compression for long documents",
    "6. Consider upgrading Groq tier for higher limits",
    "7. Batch evaluation runs with cooldown periods"
]

for rec in recommendations:
    print(f"  {rec}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
