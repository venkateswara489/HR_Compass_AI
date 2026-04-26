"""
Test script to verify Ollama-based answer generation.
This tests that the system is using Ollama (llama3) for natural, human-like responses.
"""
from system_llm import answer_with_ollama

# Sample HR policy context
hr_context = """
Employees are entitled to 21 days of paid annual leave per year. Leave requests should be submitted at least 7 days in advance through the HR portal. Unused annual leave can be carried forward up to a maximum of 10 days into the next calendar year. Encashment of leave is allowed only at the time of separation.

Employees are entitled to 12 days of paid sick leave per year. A medical certificate from a registered physician is required for sick leave exceeding 3 consecutive days. Sick leave cannot be carried forward to the next year. Sick leave is paid at the full rate of basic salary.

The company follows a 5-day work week from Monday to Friday. Standard working hours are 9:00 AM to 6:00 PM with a 1-hour lunch break. Overtime is paid at 1.5 times the normal hourly rate for hours worked beyond standard hours.
"""

# Test questions
test_questions = [
    "What is the sick leave policy?",
    "How many days of annual leave do employees get?",
    "What are the standard working hours?",
    "When is a medical certificate required?",
]

print("=" * 80)
print("OLLAMA-BASED ANSWER GENERATION TEST")
print("=" * 80)
print()

for i, question in enumerate(test_questions, 1):
    print(f"Test {i}:")
    print(f"Question: {question}")
    print()
    
    answer = answer_with_ollama(hr_context, question)
    
    print(f"Answer: {answer}")
    print()
    print(f"Length: {len(answer)} characters")
    print()
    
    # Check if it's an error message
    if answer.startswith("Error:"):
        print("⚠️ Ollama may not be running. Start with: ollama serve")
    else:
        print("✓ Answer generated successfully")
    
    print("-" * 80)
    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
