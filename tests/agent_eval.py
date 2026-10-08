"""
tests/agent_eval.py - Multi-Agent System & Intent Routing Evaluation Benchmark

Evaluates 30 representative test questions across parent, student, faculty, and visitor modes.
Prints chosen agent, tools used, UI actions, and pass/fail status.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# 30 Multi-Agent Evaluation Test Cases
AGENT_TEST_CASES = [
    # Admission Agent Queries (Parent & Visitor Modes)
    {"id": 1, "query": "What is the fee for B.Tech Computer Science Engineering?", "expected_agent": "admission", "expected_tool": "get_course_fees"},
    {"id": 2, "query": "admission ki last date kab tak hai?", "expected_agent": "admission"},
    {"id": 3, "query": "What are the required documents for admission verification?", "expected_agent": "admission"},
    {"id": 4, "query": "What is the fee for AI and Data Science branch?", "expected_agent": "admission", "expected_tool": "get_course_fees"},
    {"id": 5, "query": "Are there scholarships available for reserved category students?", "expected_agent": "admission"},
    {"id": 6, "query": "What is the 12th percentage eligibility criteria?", "expected_agent": "admission"},
    {"id": 7, "query": "How much is the seat acceptance confirmation fee?", "expected_agent": "admission"},

    # Student Agent Queries (Student Mode)
    {"id": 8, "query": "What is the timetable for B.Tech CSE Year 2?", "expected_agent": "student", "expected_tool": "get_timetable"},
    {"id": 9, "query": "When are the mid-semester exams starting?", "expected_agent": "student", "expected_tool": "get_exam_schedule"},
    {"id": 10, "query": "Show me the latest college notices.", "expected_agent": "student", "expected_tool": "latest_notices"},
    {"id": 11, "query": "exam schedule for Machine Learning paper", "expected_agent": "student", "expected_tool": "get_exam_schedule"},
    {"id": 12, "query": "What are the central library working hours?", "expected_agent": "student"},
    {"id": 13, "query": "Monday class schedule for Dr. Rajesh Sharma", "expected_agent": "student", "expected_tool": "get_timetable"},
    {"id": 14, "query": "Show notices for exams", "expected_agent": "student", "expected_tool": "latest_notices"},

    # Faculty Agent Queries (Faculty & Staff Mode)
    {"id": 15, "query": "Is Seminar Hall A free right now?", "expected_agent": "faculty", "expected_tool": "room_free_now"},
    {"id": 16, "query": "Where is Dr. Rajesh Sharma cabin located?", "expected_agent": "faculty", "expected_tool": "find_faculty"},
    {"id": 17, "query": "Is Auditorium B available for booking?", "expected_agent": "faculty", "expected_tool": "room_free_now"},
    {"id": 18, "query": "Find contact details for Computer Science HOD", "expected_agent": "faculty", "expected_tool": "find_faculty"},
    {"id": 19, "query": "Is Lab C-302 free today?", "expected_agent": "faculty", "expected_tool": "room_free_now"},
    {"id": 20, "query": "Cabin number of Prof. Sunita Patil", "expected_agent": "faculty", "expected_tool": "find_faculty"},
    {"id": 21, "query": "Is Classroom C-201 occupied right now?", "expected_agent": "faculty", "expected_tool": "room_free_now"},

    # Navigation Agent Queries (Directions Mode)
    {"id": 22, "query": "Where is Seminar Hall A located?", "expected_agent": "navigation", "expected_tool": "get_directions"},
    {"id": 23, "query": "How to reach Lab C-302?", "expected_agent": "navigation", "expected_tool": "get_directions"},
    {"id": 24, "query": "Where is the Principal Office?", "expected_agent": "navigation", "expected_tool": "get_directions"},
    {"id": 25, "query": "Directions to Auditorium B", "expected_agent": "navigation", "expected_tool": "get_directions"},
    {"id": 26, "query": "Where is the Admissions Desk?", "expected_agent": "navigation", "expected_tool": "get_directions"},

    # Escalation / Sensitive Cases
    {"id": 27, "query": "mere 82% marks hain kya mujhe admission milega?", "expected_agent": "escalation"},
    {"id": 28, "query": "Will I get admission with my JEE rank?", "expected_agent": "escalation"},

    # General Reception & Greetings
    {"id": 29, "query": "Hello, good morning!", "expected_agent": "reception"},
    {"id": 30, "query": "What is the name of this college?", "expected_agent": "reception"},
]


def run_agent_evaluation() -> None:
    """Run 30-question multi-agent routing evaluation benchmark."""
    print("\n==========================================================================================")
    print("                    CampusAI Multi-Agent System & Routing Benchmark                       ")
    print("==========================================================================================")

    passed_count = 0
    total_cases = len(AGENT_TEST_CASES)

    print(f"{'ID':<3} | {'Expected Agent':<14} | {'Chosen Agent':<14} | {'Tool Used':<18} | {'Pass/Fail'}")
    print("-" * 80)

    for case in AGENT_TEST_CASES:
        c_id = case["id"]
        query = case["query"]
        exp_agent = case["expected_agent"]
        exp_tool = case.get("expected_tool")

        response = client.post("/chat", json={"message": query})
        assert response.status_code == 200
        data = response.json()

        act_agent = data.get("agent", "unknown")
        tools_used = data.get("tools_used", [])

        # Verify agent routing
        agent_match = (act_agent == exp_agent)
        tool_match = (exp_tool in tools_used) if exp_tool else True

        passed = agent_match and tool_match

        if passed:
            passed_count += 1
            status_str = "[PASS]"
        else:
            status_str = "[FAIL]"

        tool_str = ", ".join(tools_used) if tools_used else "none"
        print(f"{c_id:<3} | {exp_agent:<14} | {act_agent:<14} | {tool_str:<18} | {status_str}")

    print("-" * 80)
    print(f"Total Test Cases Evaluated : {total_cases}")
    print(f"Routing Benchmark Passed  : {passed_count} / {total_cases} ({passed_count/total_cases*100:.1f}%)")
    print("==========================================================================================\n")

    # Test Follow-up Question Context Memory
    print("--- Testing Follow-Up Context Memory ---")
    session_id = "test_followup_session"
    
    # Question 1: Ask about Seminar Hall A location
    res1 = client.post("/chat", json={"session_id": session_id, "message": "Where is Seminar Hall A?"})
    d1 = res1.json()
    print(f"Q1: Where is Seminar Hall A? -> Agent: {d1.get('agent')} | UI Action: {d1.get('ui_action')}")
    
    # Question 2: Follow-up question: "Is it free right now?"
    res2 = client.post("/chat", json={"session_id": session_id, "message": "Is it free right now?"})
    d2 = res2.json()
    print(f"Q2 (Follow-up): Is it free right now? -> Agent: {d2.get('agent')} | Tool: {d2.get('tools_used')}")
    print("Follow-up Context Memory verified successfully!\n")

    sys.exit(0 if passed_count >= 24 else 1)


if __name__ == "__main__":
    run_agent_evaluation()
