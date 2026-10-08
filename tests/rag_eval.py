"""
tests/rag_eval.py - RAG Evaluation & Confidence Gating Benchmark Suite

Runs 20 benchmark test queries (14 answerable from KB, 3 ambiguous, 3 outside KB / personal case)
against the CampusAI RAG pipeline. Verifies zero hallucinations on outside-KB questions.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
from typing import List, Dict, Any
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings

client = TestClient(app)

# 20 Benchmark Test Cases
TEST_CASES = [
    # 14 Answerable Knowledge Base Questions
    {"id": 1, "query": "What is the total fee for B.Tech AI & Data Science?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 2, "query": "What are the compulsory subjects for 12th eligibility?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 3, "query": "What is the last date to submit the application form?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 4, "query": "admission kab tak hai sir?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 5, "query": "How much is the annual hostel fee?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 6, "query": "What are the central library working hours?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 7, "query": "Which companies visit for campus placement?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 8, "query": "What is the highest package offered in placements?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 9, "query": "What is the minimum percentage required for SC/ST category?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 10, "query": "Is there a transport bus facility available?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 11, "query": "What is the annual fee for Computer Science Engineering?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 12, "query": "How much is the initial seat acceptance fee?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 13, "query": "What scholarships are available for TFWS students?", "category": "in_kb", "expected_confident": True, "expected_human": False},
    {"id": 14, "query": "Where is the college campus located?", "category": "in_kb", "expected_confident": True, "expected_human": False},

    # 3 Ambiguous Questions
    {"id": 15, "query": "timing kya hai?", "category": "ambiguous", "expected_confident": True, "expected_human": False},
    {"id": 16, "query": "What documents?", "category": "ambiguous", "expected_confident": True, "expected_human": False},
    {"id": 17, "query": "fee kitni hai?", "category": "ambiguous", "expected_confident": True, "expected_human": False},

    # 3 Outside-KB or Personal Case Questions (Must Refuse / Escalate)
    {"id": 18, "query": "Who won the 2024 ICC T20 World Cup?", "category": "outside_kb", "expected_confident": False, "expected_human": True},
    {"id": 19, "query": "mere 82% marks hain kya mujhe CSE branch milegi?", "category": "personal_case", "expected_confident": False, "expected_human": True},
    {"id": 20, "query": "What is the food menu in the college canteen today?", "category": "outside_kb", "expected_confident": False, "expected_human": True},
]


def run_rag_evaluation() -> None:
    """Run full evaluation suite and print markdown/ASCII report table."""
    print("\n==========================================================================================")
    print("                     CampusAI RAG & Confidence Gating Benchmark                           ")
    print("==========================================================================================")
    print(f"Current Configured RAG_MIN_SCORE: {settings.RAG_MIN_SCORE}")
    print(f"Current Configured RAG_TOP_K    : {settings.RAG_TOP_K}\n")

    results = []
    passed_count = 0
    hallucination_count = 0

    print(f"{'ID':<3} | {'Category':<13} | {'Query Snippet':<35} | {'Confident':<9} | {'Human':<5} | {'Pass/Fail'}")
    print("-" * 90)

    for case in TEST_CASES:
        c_id = case["id"]
        query = case["query"]
        cat = case["category"]
        exp_conf = case["expected_confident"]
        exp_human = case["expected_human"]

        response = client.post("/chat", json={"message": query})
        assert response.status_code == 200
        data = response.json()

        act_conf = data.get("confident", False)
        act_human = data.get("needs_human", False)
        reply = data.get("reply", "")
        sources = data.get("sources", [])

        # Check for Hallucination on Outside-KB
        is_outside = cat in ["outside_kb", "personal_case"]
        if is_outside and act_conf and not act_human:
            hallucination_count += 1
            passed = False
        else:
            if is_outside:
                passed = (act_human or not act_conf)
            else:
                passed = (act_conf and len(reply) > 0)

        if passed:
            passed_count += 1
            status_str = "[PASS]"
        else:
            status_str = "[FAIL]"

        snippet = (query[:32] + "...") if len(query) > 35 else query
        print(f"{c_id:<3} | {cat:<13} | {snippet:<35} | {str(act_conf):<9} | {str(act_human):<5} | {status_str}")

        results.append({
            "id": c_id,
            "query": query,
            "category": cat,
            "passed": passed,
            "reply": reply,
            "sources": sources,
            "confident": act_conf,
            "needs_human": act_human
        })

    print("-" * 90)
    print(f"Total Test Cases Evaluated : {len(TEST_CASES)}")
    print(f"Successful Tests Passed   : {passed_count} / {len(TEST_CASES)}")
    print(f"Outside-KB Hallucinations : {hallucination_count} (Target: 0)")
    print("==========================================================================================\n")

    # How to Tune RAG_MIN_SCORE Explanation
    print("==========================================================================================")
    print("                      HOW TO TUNE RAG_MIN_SCORE FOR YOUR COLLEGE                          ")
    print("==========================================================================================")
    print("1. Observe the similarity scores printed during retrieval in backend logs.")
    print("2. If valid in-KB queries are being rejected with 'I don't have verified info':")
    print("   -> Lower RAG_MIN_SCORE in .env (e.g. from 0.50 to 0.40 or 0.35).")
    print("3. If outside-KB queries pass and trigger LLM answers (hallucination risk):")
    print("   -> Increase RAG_MIN_SCORE in .env (e.g. from 0.50 to 0.55 or 0.60).")
    print("4. Optimal setting achieves 100% pass on answerable questions and 0 hallucinations.")
    print("==========================================================================================\n")

    sys.exit(0 if hallucination_count == 0 else 1)


if __name__ == "__main__":
    run_rag_evaluation()
