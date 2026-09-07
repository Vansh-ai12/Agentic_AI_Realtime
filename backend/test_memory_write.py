from memory.long_term import write_memory

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"

print("--- First write ---")
result1 = write_memory(
    user_id=USER_ID,
    user_query="What internships have I received and what's blocking Project Alpha?",
    answer="You have received internship offers for a Junior Manual Tester/QA position at Jarvis Technology & Strategy Consulting in Delhi and a Database Analyst role at TSTEPS PRIVATE LIMITED. The current blocker for Project Alpha is a delay from the third-party API provider."
)
print(result1)

print("\n--- Second write (near-duplicate, should UPDATE not insert) ---")
result2 = write_memory(
    user_id=USER_ID,
    user_query="What's blocking Project Alpha right now?",
    answer="Project Alpha is currently blocked because of a delay from the third-party API provider, affecting the authentication module and payment gateway."
)
print(result2)